"""
RBG — Random Booking Generator (backend edition)
=================================================
Proceso asyncio que genera reservas aleatorias de forma continua
directamente contra la base de datos, sin necesidad de ningún
navegador abierto. Se arranca automáticamente al iniciar el backend
y expone endpoints de control en /api/rbg/*.

La lógica de generación es idéntica a la del RBG del frontend
(mismos nombres ficticios, mismo reparto de clases, mismo cálculo
de precio), trasladada aquí para que sobreviva al cierre de pestañas.
"""
import asyncio
import logging
import random
import string
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# ── Datos de demo para la generación aleatoria ────────────────────────────────
_FIRST_NAMES = [
    "Laura", "Carlos", "Maria", "Javier", "Lucia", "Pablo",
    "Elena", "Diego", "Marta", "Alvaro", "Sofia", "Hugo",
    "Ana", "Miguel", "Carmen", "David", "Isabel", "Jorge",
]
_LAST_NAMES = [
    "Garcia", "Rodriguez", "Fernandez", "Lopez", "Martinez",
    "Sanchez", "Perez", "Gomez", "Diaz", "Ruiz", "Moreno", "Jimenez",
]
_SEAT_WEIGHTS = [("TOURIST", 0.85), ("BUSINESS", 0.15)]


def _pick_class() -> str:
    r = random.random()
    cumulative = 0.0
    for code, weight in _SEAT_WEIGHTS:
        cumulative += weight
        if r <= cumulative:
            return code
    return "TOURIST"


def _random_doc() -> str:
    digits = random.randint(10_000_000, 99_999_999)
    letter = "TRWAGMYFPDXBNJZSQVHLCKE"[digits % 23]
    return f"{digits}{letter}"


def _random_ref() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


# ── Clase principal ───────────────────────────────────────────────────────────
class RBGManager:
    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._running: bool = False
        self._rate_per_minute: int = 20
        self._generated: int = 0
        self._errors: int = 0
        self._started_at: Optional[datetime] = None
        self._last_booking_ref: Optional[str] = None

    # ── Generación de una reserva ─────────────────────────────────────────────
    async def _generate_one(self) -> None:
        from sqlalchemy import select
        from sqlalchemy.exc import IntegrityError

        from app.database import AsyncSessionLocal
        from app.models import (
            Booking, BookingStatus, Customer, Flight, FlightStatus, SeatClass,
        )

        async with AsyncSessionLocal() as db:
            # 1. Vuelo aleatorio entre los programados
            result = await db.execute(
                select(Flight).where(Flight.status == FlightStatus.SCHEDULED)
            )
            flights = list(result.scalars().all())
            if not flights:
                logger.warning("RBG: no hay vuelos SCHEDULED disponibles")
                return
            flight = random.choice(flights)

            # 2. Clase de asiento (con pesos)
            seat_class_code = _pick_class()
            result = await db.execute(
                select(SeatClass).where(SeatClass.code == seat_class_code)
            )
            seat_class = result.scalar_one_or_none()
            if not seat_class:
                return

            # 3. Cliente de demo único
            tag = random.randint(100_000, 9_999_999)
            first = random.choice(_FIRST_NAMES)
            last = random.choice(_LAST_NAMES)
            email = f"{first.lower()}.{last.lower()}{tag}@rbg-auto.test"
            doc = _random_doc()

            from sqlalchemy import or_
            res = await db.execute(
                select(Customer).where(
                    or_(Customer.email == email, Customer.document_id == doc)
                )
            )
            customer = res.scalars().first()
            if not customer:
                customer = Customer(
                    full_name=f"{first} {last}",
                    email=email,
                    document_id=doc,
                )
                db.add(customer)
                try:
                    await db.flush()
                except IntegrityError:
                    await db.rollback()
                    return

            # 4. Reserva
            price = round(float(flight.base_price) * float(seat_class.price_multiplier), 2)
            row = random.randint(1, max(flight.total_seats // 6, 1))
            seat_number = f"{row}{random.choice('ABCDEF')}"
            ref = _random_ref()

            booking = Booking(
                booking_reference=ref,
                customer_id=customer.id,
                flight_id=flight.id,
                seat_class_id=seat_class.id,
                seat_number=seat_number,
                price=price,
                status=BookingStatus.CONFIRMED,
            )
            db.add(booking)
            await db.commit()
            self._last_booking_ref = ref

    # ── Bucle principal ───────────────────────────────────────────────────────
    async def _run(self) -> None:
        while self._running:
            interval = max(60.0 / self._rate_per_minute, 0.5)
            await asyncio.sleep(interval)
            if not self._running:
                break
            try:
                await self._generate_one()
                self._generated += 1
            except Exception as exc:
                self._errors += 1
                logger.error("RBG: error generando reserva: %s", exc)

    # ── API pública ───────────────────────────────────────────────────────────
    def start(self, rate_per_minute: int = 20) -> None:
        self._rate_per_minute = max(1, min(rate_per_minute, 300))
        if not self._running:
            self._running = True
            self._started_at = datetime.now(timezone.utc)
            self._task = asyncio.create_task(self._run())
        # Si ya estaba corriendo, solo actualiza el ritmo (el próximo
        # tick usará el nuevo intervalo automáticamente).

    def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None

    @property
    def status(self) -> dict:
        return {
            "running": self._running,
            "rate_per_minute": self._rate_per_minute,
            "generated": self._generated,
            "errors": self._errors,
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "last_booking_ref": self._last_booking_ref,
        }


# Singleton compartido por toda la aplicación
rbg = RBGManager()
