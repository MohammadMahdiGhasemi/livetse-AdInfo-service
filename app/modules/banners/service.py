import logging
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile

from .repo import BannerRepository
from .model import Banner
from .schema import BannerCreate, BannerUpdate, PaginatedBannerResponse
from app.services.upload_client import upload_client, UploadServiceError

logger = logging.getLogger(__name__)


class BannerService:

    def __init__(self):
        self.repo = BannerRepository()

    async def create_banner(self, db: AsyncSession, data: BannerCreate):
        banner = Banner(**data.model_dump())
        return await self.repo.create(db, banner)

    async def create_banner_with_upload(
        self,
        db: AsyncSession,
        data: BannerCreate,
        file: UploadFile,
    ):
        try:
            upload_result = await upload_client.upload_file(file)
        except UploadServiceError as e:
            logger.error(f"Upload failed: {e.detail}")
            raise

        upload_data = upload_result.get("data", {})
        banner = Banner(
            **data.model_dump(),
            image_url=upload_data.get("url", data.image_url),
            image_name=upload_data.get("name"),
            image_folder=upload_data.get("folder"),
            image_size=upload_data.get("size"),
            image_type=upload_data.get("type"),
        )
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

    async def update_banner_with_upload(
        self,
        db: AsyncSession,
        banner_id: str,
        data: BannerUpdate,
        file: UploadFile,
    ):
        banner = await self.repo.get_by_id(db, banner_id)
        if not banner:
            return None

        if banner.image_name and banner.image_folder:
            try:
                await upload_client.delete_file(banner.image_folder, banner.image_name)
            except UploadServiceError as e:
                logger.warning(f"Failed to delete old image: {e.detail}")

        try:
            upload_result = await upload_client.upload_file(file)
        except UploadServiceError as e:
            logger.error(f"Upload failed: {e.detail}")
            raise

        upload_data = upload_result.get("data", {})
        update_data = data.model_dump(exclude_unset=True)

        update_data["image_url"] = upload_data.get("url", banner.image_url)
        update_data["image_name"] = upload_data.get("name")
        update_data["image_folder"] = upload_data.get("folder")
        update_data["image_size"] = upload_data.get("size")
        update_data["image_type"] = upload_data.get("type")

        for key, value in update_data.items():
            setattr(banner, key, value)

        await db.commit()
        await db.refresh(banner)
        logger.info(f"Updated banner with new image: {banner_id}")
        return banner

    async def delete_banner(self, db: AsyncSession, banner_id: str):
        banner = await self.repo.get_by_id(db, banner_id)
        if not banner:
            return None

        if banner.image_name and banner.image_folder:
            try:
                await upload_client.delete_file(banner.image_folder, banner.image_name)
            except UploadServiceError as e:
                logger.warning(f"Failed to delete image: {e.detail}")

        await self.repo.delete(db, banner)
        return banner
