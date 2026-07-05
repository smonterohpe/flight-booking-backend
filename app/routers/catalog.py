from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Airport, SeatClass
from app.schemas import AirportOut, SeatClassOut

router = APIRouter(tags=["catalog"])


@router.get("/airports", response_model=list[AirportOut])
async def list_airports(db: AsyncSession = Depends(get_db)) -> list[Airport]:
    result = await db.execute(select(Airport).order_by(Airport.iata_code))
    return list(result.scalars().all())


@router.get("/seat-classes", response_model=list[SeatClassOut])
async def list_seat_classes(db: AsyncSession = Depends(get_db)) -> list[SeatClass]:
    result = await db.execute(select(SeatClass).order_by(SeatClass.id))
    return list(result.scalars().all())
