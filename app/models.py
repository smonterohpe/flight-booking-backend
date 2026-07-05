import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BookingStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class FlightStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    DELAYED = "DELAYED"
    CANCELLED = "CANCELLED"
    DEPARTED = "DEPARTED"
    LANDED = "LANDED"


booking_status_enum = PGEnum(BookingStatus, name="booking_status", create_type=False)
flight_status_enum = PGEnum(FlightStatus, name="flight_status", create_type=False)


class Airport(Base):
    __tablename__ = "airports"

    id: Mapped[int] = mapped_column(primary_key=True)
    iata_code: Mapped[str] = mapped_column(String(3), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, default="UTC")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class SeatClass(Base):
    __tablename__ = "seat_classes"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    price_multiplier: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False, default=1.00)


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    document_id: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    bookings: Mapped[list["Booking"]] = relationship(back_populates="customer")


class Flight(Base):
    __tablename__ = "flights"
    __table_args__ = (
        CheckConstraint("origin_airport_id <> destination_airport_id", name="chk_diff_airports"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    flight_number: Mapped[str] = mapped_column(String(10), nullable=False)
    airline_code: Mapped[str] = mapped_column(String(3), nullable=False)
    airline_name: Mapped[str] = mapped_column(String(100), nullable=False)
    origin_airport_id: Mapped[int] = mapped_column(ForeignKey("airports.id"), nullable=False)
    destination_airport_id: Mapped[int] = mapped_column(ForeignKey("airports.id"), nullable=False)
    departure_time: Mapped[datetime] = mapped_column(nullable=False)
    arrival_time: Mapped[datetime] = mapped_column(nullable=False)
    aircraft_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    base_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    total_seats: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[FlightStatus] = mapped_column(flight_status_enum, default=FlightStatus.SCHEDULED)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    origin: Mapped["Airport"] = relationship(foreign_keys=[origin_airport_id])
    destination: Mapped["Airport"] = relationship(foreign_keys=[destination_airport_id])
    bookings: Mapped[list["Booking"]] = relationship(back_populates="flight")


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_reference: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    flight_id: Mapped[int] = mapped_column(ForeignKey("flights.id"), nullable=False)
    seat_class_id: Mapped[int] = mapped_column(ForeignKey("seat_classes.id"), nullable=False)
    seat_number: Mapped[str | None] = mapped_column(String(5), nullable=True)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[BookingStatus] = mapped_column(booking_status_enum, default=BookingStatus.CONFIRMED)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now())

    customer: Mapped["Customer"] = relationship(back_populates="bookings")
    flight: Mapped["Flight"] = relationship(back_populates="bookings")
    seat_class: Mapped["SeatClass"] = relationship()
