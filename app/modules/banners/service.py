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

        upload_data = upload_result.get("data", {}) or {}
        banner_data = data.model_dump()
        banner_data.update(
            image_url=upload_data.get("url") or data.image_url,
            image_name=upload_data.get("name"),
            image_folder=upload_data.get("folder"),
            image_size=upload_data.get("size"),
            image_type=upload_data.get("type"),
        )
        banner = Banner(**banner_data)
        try:
            return await self.repo.create(db, banner)
        except Exception:
            new_name = upload_data.get("name")
            new_folder = upload_data.get("folder")
            if new_name and new_folder:
                try:
                    await upload_client.delete_file(new_folder, new_name)
                except UploadServiceError:
                    logger.warning("Failed to clean up banner upload after DB failure")
            raise

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
        new_start = update_data.get("start_at", banner.start_at)
        new_expire = update_data.get("expire_at", banner.expire_at)
        if new_start and new_expire and new_expire <= new_start:
            raise ValueError("expire_at must be after start_at")

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

        old_image_name = banner.image_name
        old_image_folder = banner.image_folder

        # Upload first. Never delete the currently referenced image before the
        # replacement is known to exist.
        upload_result = await upload_client.upload_file(file)
        upload_data = upload_result.get("data", {}) or {}

        update_data = data.model_dump(exclude_unset=True)
        new_start = update_data.get("start_at", banner.start_at)
        new_expire = update_data.get("expire_at", banner.expire_at)
        if new_start and new_expire and new_expire <= new_start:
            raise ValueError("expire_at must be after start_at")

        update_data["image_url"] = upload_data.get("url", banner.image_url)
        update_data["image_name"] = upload_data.get("name")
        update_data["image_folder"] = upload_data.get("folder")
        update_data["image_size"] = upload_data.get("size")
        update_data["image_type"] = upload_data.get("type")

        try:
            for key, value in update_data.items():
                setattr(banner, key, value)
            await db.commit()
            await db.refresh(banner)
        except Exception:
            await db.rollback()
            # Best-effort cleanup of the newly uploaded object if DB commit fails.
            new_name = upload_data.get("name")
            new_folder = upload_data.get("folder")
            if new_name and new_folder:
                try:
                    await upload_client.delete_file(new_folder, new_name)
                except UploadServiceError:
                    logger.warning("Failed to clean up newly uploaded image after DB failure")
            raise

        # Database now points to the replacement, so old-file cleanup can be
        # best-effort without breaking the live record.
        if old_image_name and old_image_folder:
            try:
                await upload_client.delete_file(old_image_folder, old_image_name)
            except UploadServiceError as e:
                logger.warning("Failed to delete old image: %s", e.detail)

        logger.info("Updated banner with new image: %s", banner_id)
        return banner

    async def delete_banner(self, db: AsyncSession, banner_id: str):
        banner = await self.repo.get_by_id(db, banner_id)
        if not banner:
            return None

        image_name = banner.image_name
        image_folder = banner.image_folder
        await self.repo.delete(db, banner)

        if image_name and image_folder:
            try:
                await upload_client.delete_file(image_folder, image_name)
            except UploadServiceError as e:
                # An orphaned upload is safer than a DB record that references
                # a file we already deleted.
                logger.warning("Failed to delete image after banner deletion: %s", e.detail)

        return banner
