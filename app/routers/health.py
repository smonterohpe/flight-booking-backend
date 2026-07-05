from fastapi import APIRouter

from app.config import get_settings
from app.database import check_db_connection
from app.schemas import HealthStatus

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health", response_model=HealthStatus)
async def health_check() -> HealthStatus:
    """
    Endpoint de salud. La Observability Console lo consulta periódicamente
    para pintar el estado del BackEnd (equivalente a "BackEnd - API" en el
    diagrama de arquitectura).
    """
    db_ok = await check_db_connection()
    return HealthStatus(
        status="ok" if db_ok else "degraded",
        database="connected" if db_ok else "unreachable",
        version=settings.api_version,
    )
