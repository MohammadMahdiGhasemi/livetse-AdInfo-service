from app.shared.base_model import Base
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession
)
from app.core.config import settings
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

# Importing the registry registers every model on Base.metadata before
# init_db() runs ``create_all``. Without this, models only register when
# their owning router is imported — and the lifespan event runs before
# the routers are wired up.
import app.models_registry  # noqa: F401

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=20,
    pool_timeout=30,
    pool_pre_ping=True,
    pool_recycle=1800,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """Initialize the database schema.

    Issues:
      1. Verifies DB connectivity (raises if unreachable).
      2. Runs ``Base.metadata.create_all`` for ALL model tables. This is
         idempotent and safe to invoke on every startup — tables that
         already exist are left alone.

    NOTE: For a real production deploy you should still run schema
    migrations (Alembic) before this service starts; ``create_all`` is
    here so dev / fresh-DB onboarding doesn't require a separate step.
    """
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema verified / created")
