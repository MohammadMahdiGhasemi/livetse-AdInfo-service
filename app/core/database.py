import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.shared.base_model import Base

# Register all models on Base.metadata before optional dev schema creation.
import app.models_registry  # noqa: F401,E402

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO or settings.LOG_SQL_ENABLED,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_pre_ping=True,
    pool_recycle=settings.DB_POOL_RECYCLE,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def check_db() -> None:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))


async def init_db() -> None:
    """Fail fast on DB connectivity; schema creation is dev-only opt-in."""
    await check_db()
    if settings.AUTO_CREATE_SCHEMA:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.warning("AUTO_CREATE_SCHEMA is enabled; do not use this in production")
    logger.info("Database connectivity verified")


async def close_db() -> None:
    await engine.dispose()
