from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,   # evita conexiones muertas tras cortes de red/BD
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base declarativa para los modelos ORM (mapean tablas ya existentes)."""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependencia FastAPI: entrega una sesión de BD por request."""
    async with AsyncSessionLocal() as session:
        yield session


async def check_db_connection() -> bool:
    """Usado por el endpoint /health para comprobar conectividad real con PostgreSQL."""
    from sqlalchemy import text
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
