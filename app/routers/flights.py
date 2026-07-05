from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Flight, FlightStatus
from app.schemas import FlightOut

router = APIRouter(tags=["flights"])


@router.get("/flights", response_model=list[FlightOut])
async def list_flights(
    origin: str | None = None,
    destination: str | None = None,
    departure_after: datetime | None = None,
    status: FlightStatus | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> list[Flight]:
    """
    Lista vuelos disponibles. Es el endpoint principal que consulta el
    generador aleatorio de reservas (RBG) del frontend para elegir un
    vuelo al azar sobre el que crear una reserva.
    """
    query = select(Flight).options(
        selectinload(Flight.origin), selectinload(Flight.destination)
    )

    if origin:
        query = query.join(Flight.origin).where(Flight.origin.has(iata_code=origin.upper()))
    if destination:
        query = query.join(Flight.destination).where(Flight.destination.has(iata_code=destination.upper()))
    if departure_after:
        query = query.where(Flight.departure_time >= departure_after)
    if status:
        query = query.where(Flight.status == status)

    query = query.order_by(Flight.departure_time).limit(limit)

    result = await db.execute(query)
    return list(result.scalars().unique().all())


@router.get("/flights/{flight_id}", response_model=FlightOut)
async def get_flight(flight_id: int, db: AsyncSession = Depends(get_db)) -> Flight:
    query = (
        select(Flight)
        .options(selectinload(Flight.origin), selectinload(Flight.destination))
        .where(Flight.id == flight_id)
    )
    result = await db.execute(query)
    flight = result.scalar_one_or_none()
    if flight is None:
        raise HTTPException(status_code=404, detail="Vuelo no encontrado")
    return flight
