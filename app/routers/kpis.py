from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Booking, BookingStatus
from app.schemas import KPISummary, KPITimeseriesPoint

router = APIRouter(prefix="/kpis", tags=["kpis"])


@router.get("/summary", response_model=KPISummary)
async def get_summary(
    from_time: datetime | None = Query(default=None, alias="from"),
    to_time: datetime | None = Query(default=None, alias="to"),
    db: AsyncSession = Depends(get_db),
) -> KPISummary:
    """
    KPIs filtrados por el rango temporal seleccionado en el dashboard.
    Sin parámetros devuelve los totales históricos completos.
    Con ?from=ISO&to=ISO devuelve los KPIs del intervalo indicado.
    """
    q = select(
        func.count().label("total_bookings"),
        func.coalesce(func.sum(Booking.price), 0).label("total_revenue"),
        func.max(Booking.created_at).label("last_booking_at"),
        func.count(
            func.distinct(func.date_trunc('day', Booking.created_at))
        ).label("days_count"),
    ).where(Booking.status == BookingStatus.CONFIRMED)

    if from_time:
        q = q.where(Booking.created_at >= from_time.replace(tzinfo=None))
    if to_time:
        q = q.where(Booking.created_at <= to_time.replace(tzinfo=None))

    result = await db.execute(q)
    row = result.mappings().one()

    total_bookings = row["total_bookings"] or 0
    total_revenue = float(row["total_revenue"] or 0)
    last_booking_at = row["last_booking_at"]
    days_count = max(row["days_count"] or 1, 1)

    minutes_since = None
    if last_booking_at is not None:
        now = datetime.now(timezone.utc)
        minutes_since = round((now - last_booking_at).total_seconds() / 60, 1)

    return KPISummary(
        total_bookings=total_bookings,
        total_revenue=total_revenue,
        avg_bookings_per_day=total_bookings / days_count,
        avg_revenue_per_day=total_revenue / days_count,
        last_booking_at=last_booking_at,
        minutes_since_last_booking=minutes_since,
    )


@router.get("/timeseries", response_model=list[KPITimeseriesPoint])
async def get_timeseries(
    from_time: datetime | None = Query(default=None, alias="from"),
    to_time: datetime | None = Query(default=None, alias="to"),
    db: AsyncSession = Depends(get_db),
) -> list[KPITimeseriesPoint]:
    """
    Serie temporal de reservas/minuto e ingresos/minuto, para la gráfica
    "Reservas por minuto (timeline)" de la Observability Console.
    Si no se especifica rango, devuelve la última hora.
    """
    query = "SELECT * FROM v_bookings_per_minute WHERE 1=1"
    params: dict = {}

    if from_time:
        query += " AND minute >= :from_time"
        params["from_time"] = from_time.replace(tzinfo=None)
    else:
        query += " AND minute >= now() - interval '1 hour'"

    if to_time:
        query += " AND minute <= :to_time"
        params["to_time"] = to_time.replace(tzinfo=None)

    query += " ORDER BY minute"

    result = await db.execute(text(query), params)
    rows = result.mappings().all()

    return [
        KPITimeseriesPoint(
            minute=row["minute"],
            bookings_count=row["bookings_count"],
            revenue=float(row["revenue"]),
        )
        for row in rows
    ]
