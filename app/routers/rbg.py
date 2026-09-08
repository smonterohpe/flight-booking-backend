from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.rbg import rbg

router = APIRouter(prefix="/rbg", tags=["rbg"])


class RBGStartPayload(BaseModel):
    rate_per_minute: int = Field(default=20, ge=1, le=300)


@router.post("/start")
async def start_rbg(payload: RBGStartPayload = RBGStartPayload()) -> dict:
    """
    Arranca el generador (o actualiza su ritmo si ya estaba corriendo).
    El generador persiste en el servidor aunque el navegador se cierre.
    """
    rbg.start(payload.rate_per_minute)
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
