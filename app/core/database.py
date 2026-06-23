from app.shared.base_model import Base
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession
)
from app.core.config import settings
from sqlalchemy import text

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

async def init_db():
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
