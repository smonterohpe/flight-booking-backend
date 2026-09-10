from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.rbg import rbg

router = APIRouter(prefix="/rbg", tags=["rbg"])


class RBGStartPayload(BaseModel):
    rate_per_minute: int = Field(default=20, ge=1, le=300)
    start_hour: int = Field(default=8, ge=0, le=23, description="Hora UTC inicio horario de negocio")
    end_hour: int = Field(default=22, ge=1, le=24, description="Hora UTC fin horario de negocio")


@router.post("/start")
async def start_rbg(payload: RBGStartPayload = RBGStartPayload()) -> dict:
    """
    Arranca el generador (o actualiza su configuración si ya estaba corriendo).
    Soporta horario de negocio: fuera de start_hour-end_hour (UTC) no genera reservas.
    """
    rbg.start(payload.rate_per_minute, payload.start_hour, payload.end_hour)
    return rbg.status


@router.post("/stop")
async def stop_rbg() -> dict:
    """Detiene el generador."""
    rbg.stop()
    return rbg.status


@router.get("/status")
async def get_rbg_status() -> dict:
    """Estado actual del generador — consumido por el frontend cada pocos segundos."""
    return rbg.status
