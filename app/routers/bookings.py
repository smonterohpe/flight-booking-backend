import random
import string
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Booking, BookingStatus, Customer, Flight, SeatClass
from app.schemas import BookingCreate, BookingOut, BookingStatusUpdate

router = APIRouter(tags=["bookings"])

_BOOKING_OPTIONS = selectinload(Booking.customer), selectinload(Booking.seat_class), \
    selectinload(Booking.flight).selectinload(Flight.origin), \
    selectinload(Booking.flight).selectinload(Flight.destination)


def _generate_booking_reference() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


def _generate_seat_number(total_seats: int) -> str:
    row = random.randint(1, max(total_seats // 6, 1))
    letter = random.choice("ABCDEF")
    return f"{row}{letter}"


@router.post("/bookings", response_model=BookingOut, status_code=201)
async def create_booking(payload: BookingCreate, db: AsyncSession = Depends(get_db)) -> Booking:
    """
    Crea una reserva. Es el endpoint principal invocado por el generador
    aleatorio de reservas (RBG) del frontend, y también por el flujo de
    reserva manual de un usuario real.
    """
    # 1. Vuelo
    flight = await db.get(Flight, payload.flight_id)
    if flight is None:
        raise HTTPException(status_code=404, detail="Vuelo no encontrado")

    # 2. Clase de asiento
    seat_class_result = await db.execute(
        select(SeatClass).where(SeatClass.code == payload.seat_class_code.upper())
    )
    seat_class = seat_class_result.scalar_one_or_none()
    if seat_class is None:
        raise HTTPException(status_code=400, detail="Clase de asiento no válida")

    # 3. Cliente: obtener por email o crear
    customer_result = await db.execute(
        select(Customer).where(Customer.email == payload.customer.email)
    )
    customer = customer_result.scalar_one_or_none()
    if customer is None:
        customer = Customer(**payload.customer.model_dump())
        db.add(customer)
        await db.flush()  # asigna customer.id sin cerrar la transacción

    # 4. Cálculo de precio y asiento
    price = round(float(flight.base_price) * float(seat_class.price_multiplier), 2)
    seat_number = _generate_seat_number(flight.total_seats)

    booking = Booking(
        booking_reference=_generate_booking_reference(),
        customer_id=customer.id,
        flight_id=flight.id,
        seat_class_id=seat_class.id,
        seat_number=seat_number,
        price=price,
        status=BookingStatus.CONFIRMED,
    )
    db.add(booking)
    await db.commit()

    # Recargar con relaciones para la respuesta
    result = await db.execute(
        select(Booking).options(*_BOOKING_OPTIONS).where(Booking.id == booking.id)
    )
    return result.scalar_one()


@router.get("/bookings", response_model=list[BookingOut])
async def list_bookings(
    status: BookingStatus | None = None,
    created_after: datetime | None = None,
    limit: int = Query(default=100, le=1000),
    db: AsyncSession = Depends(get_db),
) -> list[Booking]:
    query = select(Booking).options(*_BOOKING_OPTIONS)
    if status:
        query = query.where(Booking.status == status)
    if created_after:
        query = query.where(Booking.created_at >= created_after)
    query = query.order_by(Booking.created_at.desc()).limit(limit)

    result = await db.execute(query)
    return list(result.scalars().unique().all())


@router.get("/bookings/{booking_id}", response_model=BookingOut)
async def get_booking(booking_id: int, db: AsyncSession = Depends(get_db)) -> Booking:
    query = select(Booking).options(*_BOOKING_OPTIONS).where(Booking.id == booking_id)
    result = await db.execute(query)
    booking = result.scalar_one_or_none()
    if booking is None:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return booking


@router.patch("/bookings/{booking_id}/status", response_model=BookingOut)
async def update_booking_status(
    booking_id: int, payload: BookingStatusUpdate, db: AsyncSession = Depends(get_db)
) -> Booking:
    booking = await db.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")

    booking.status = payload.status
    await db.commit()

    result = await db.execute(
        select(Booking).options(*_BOOKING_OPTIONS).where(Booking.id == booking_id)
    )
    return result.scalar_one()
