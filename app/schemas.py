from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import BookingStatus, FlightStatus


# ---------------------------------------------------------------------
# Airports
# ---------------------------------------------------------------------
class AirportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    iata_code: str
    name: str
    city: str
    country: str
    timezone: str


# ---------------------------------------------------------------------
# Seat classes
# ---------------------------------------------------------------------
class SeatClassOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    price_multiplier: float


# ---------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------
class CustomerCreate(BaseModel):
    full_name: str = Field(..., max_length=150)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    document_id: str = Field(..., max_length=30)


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    phone: str | None
    document_id: str
    created_at: datetime


# ---------------------------------------------------------------------
# Flights
# ---------------------------------------------------------------------
class FlightOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    flight_number: str
    airline_code: str
    airline_name: str
    origin: AirportOut
    destination: AirportOut
    departure_time: datetime
    arrival_time: datetime
    aircraft_type: str | None
    base_price: float
    total_seats: int
    status: FlightStatus


# ---------------------------------------------------------------------
# Bookings
# ---------------------------------------------------------------------
class BookingCreate(BaseModel):
    flight_id: int
    seat_class_code: str = Field(..., examples=["TOURIST", "BUSINESS"])

    # Si el cliente ya existe (por email) se reutiliza; si no, se crea.
    customer: CustomerCreate


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    booking_reference: str
    customer: CustomerOut
    flight: FlightOut
    seat_class: SeatClassOut
    seat_number: str | None
    price: float
    status: BookingStatus
    created_at: datetime
    updated_at: datetime


class BookingStatusUpdate(BaseModel):
    status: BookingStatus


# ---------------------------------------------------------------------
# KPIs (consumidos por la Observability Console)
# ---------------------------------------------------------------------
class KPISummary(BaseModel):
    total_bookings: int
    total_revenue: float
    avg_bookings_per_day: float
    avg_revenue_per_day: float
    last_booking_at: datetime | None
    minutes_since_last_booking: float | None


class KPITimeseriesPoint(BaseModel):
    minute: datetime
    bookings_count: int
    revenue: float


class HealthStatus(BaseModel):
    status: str
    database: str
    version: str


class PingResponse(BaseModel):
    message: str


class SystemMetrics(BaseModel):
    cpu_percent: float
    ram_used_mb: float
    ram_total_mb: float
    disk_used_gb: float
    disk_total_gb: float
    uptime_seconds: int
