import time

import psutil
from fastapi import APIRouter

from app.config import get_settings
from app.database import check_db_connection
from app.schemas import HealthStatus, PingResponse, SystemMetrics

router = APIRouter(tags=["health"])
settings = get_settings()

_PROCESS_START = time.time()


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


@router.get("/ping", response_model=PingResponse)
async def ping() -> PingResponse:
    """Ping ligero (sin tocar BD) para medir latencia pura del backend."""
    return PingResponse(message="pong")


@router.get("/system", response_model=SystemMetrics)
async def system_metrics() -> SystemMetrics:
    """
    Métricas de sistema (CPU/RAM/Disco/Uptime) del proceso del backend,
    consumidas por la pestaña "Systems" de la Observability Console.
    """
    disk = psutil.disk_usage("/")
    mem = psutil.virtual_memory()
    uptime_seconds = int(time.time() - _PROCESS_START)

    return SystemMetrics(
        cpu_percent=psutil.cpu_percent(interval=0.2),
        ram_used_mb=round((mem.total - mem.available) / (1024 * 1024), 1),
        ram_total_mb=round(mem.total / (1024 * 1024), 1),
        disk_used_gb=round(disk.used / (1024 ** 3), 1),
        disk_total_gb=round(disk.total / (1024 ** 3), 1),
        uptime_seconds=uptime_seconds,
    )
