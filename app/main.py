from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import bookings, catalog, flights, health, kpis

settings = get_settings()

app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=(
        "API REST del simulador de reservas de vuelos. "
        "Sirve tanto al frontend de negocio (con su generador aleatorio "
        "de reservas) como a la Observability Console para KPIs y "
        "estado de salud."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(catalog.router, prefix="/api")
app.include_router(flights.router, prefix="/api")
app.include_router(bookings.router, prefix="/api")
app.include_router(kpis.router, prefix="/api")


@app.get("/", tags=["root"])
async def root() -> dict:
    return {"service": settings.api_title, "version": settings.api_version, "docs": "/docs"}
