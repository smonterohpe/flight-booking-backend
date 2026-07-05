from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import KPISummary, KPITimeseriesPoint

router = APIRouter(prefix="/kpis", tags=["kpis"])


@router.get("/summary", response_model=KPISummary)
async def get_summary(db: AsyncSession = Depends(get_db)) -> KPISummary:
    """
    Tarjetas KPI globales (equivalente a "Total Pedidos", "Ingresos
    Totales", "Media/día", "Último pedido hace..." del dashboard de
    referencia), calculadas sobre la vista v_bookings_summary.
    """
    result = await db.execute(text("SELECT * FROM v_bookings_summary"))
    row = result.mappings().one()

    last_booking_at = row["last_booking_at"]
    minutes_since = None
    if last_booking_at is not None:
        now = datetime.now(timezone.utc)
        minutes_since = round((now - last_booking_at).total_seconds() / 60, 1)

    return KPISummary(
        total_bookings=row["total_bookings"],
        total_revenue=float(row["total_revenue"]),
        avg_bookings_per_day=float(row["avg_bookings_per_day"]),
        avg_revenue_per_day=float(row["avg_revenue_per_day"]),
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
        params["from_time"] = from_time
    else:
        query += " AND minute >= now() - interval '1 hour'"

    if to_time:
        query += " AND minute <= :to_time"
        params["to_time"] = to_time

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
