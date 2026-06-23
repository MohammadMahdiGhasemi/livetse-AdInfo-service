import logging
from sqlalchemy.ext.asyncio import AsyncSession

from .repo import BannerRepository
from .model import Banner
from .schema import BannerCreate, BannerUpdate, PaginatedBannerResponse

logger = logging.getLogger(__name__)


class BannerService:

    def __init__(self):
        self.repo = BannerRepository()

    async def create_banner(self, db: AsyncSession, data: BannerCreate):
        banner = Banner(**data.model_dump())
        return await self.repo.create(db, banner)

    async def get_banner(self, db: AsyncSession, banner_id: str):
        return await self.repo.get_by_id(db, banner_id)

    async def get_all_banners(self, db: AsyncSession, page: int = 1, size: int = 20):
        items, total = await self.repo.get_all(db, page, size)
        pages = (total + size - 1) // size if total else 0

        return PaginatedBannerResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages
        )

    async def get_active_banners(self, db: AsyncSession, platform: str):
        return await self.repo.get_active_banners(db, platform)

    async def update_banner(self, db: AsyncSession, banner_id: str, data: BannerUpdate):
        banner = await self.repo.get_by_id(db, banner_id)
        if not banner:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(banner, key, value)

        await db.commit()
        await db.refresh(banner)
        logger.info(f"Updated banner: {banner_id}, fields: {list(update_data.keys())}")
        return banner

    async def delete_banner(self, db: AsyncSession, banner_id: str):
        banner = await self.repo.get_by_id(db, banner_id)
        if not banner:
            return None
        await self.repo.delete(db, banner)
        return banner
