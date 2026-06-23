import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone

from .model import Banner

logger = logging.getLogger(__name__)


class BannerRepository:

    async def create(self, db: AsyncSession, banner: Banner):
        db.add(banner)
        await db.commit()
        await db.refresh(banner)
        logger.info(f"Created banner: {banner.id}")
        return banner

    async def get_by_id(self, db: AsyncSession, banner_id: str):
        result = await db.execute(select(Banner).filter(Banner.id == banner_id))
        return result.scalar_one_or_none()

    async def get_all(self, db: AsyncSession, page: int = 1, size: int = 20):
        offset = (page - 1) * size

        count_result = await db.execute(select(func.count(Banner.id)))
        total = count_result.scalar()

        result = await db.execute(
            select(Banner)
            .order_by(Banner.sort_order.asc())
            .offset(offset)
            .limit(size)
        )
        items = result.scalars().all()

        return items, total

    async def get_active_banners(self, db: AsyncSession, platform: str):
        now = datetime.now(timezone.utc)

        result = await db.execute(
            select(Banner)
            .filter(
                Banner.is_active == True,
                Banner.platform == platform,
                Banner.start_at <= now,
                Banner.expire_at >= now
            )
            .order_by(Banner.sort_order.asc())
        )
        return result.scalars().all()

    async def delete(self, db: AsyncSession, banner: Banner):
        banner_id = banner.id
        await db.delete(banner)
        await db.commit()
        logger.info(f"Deleted banner: {banner_id}")
