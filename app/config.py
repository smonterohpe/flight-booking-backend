from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuración de la aplicación, cargada desde variables de entorno
    o un fichero .env en la raíz del proyecto.
    """
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Ej: postgresql+asyncpg://flight_app:password@10.0.0.3:5432/flight_booking
    database_url: str

    api_title: str = "Flight Booking API"
    api_version: str = "1.0.0"

    # Orígenes permitidos para CORS (frontend de negocio + observability console)
    cors_origins: list[str] = ["*"]

    # Nº de asientos por defecto si un vuelo no especifica total_seats
    default_total_seats: int = 180


@lru_cache
def get_settings() -> Settings:
    return Settings()
