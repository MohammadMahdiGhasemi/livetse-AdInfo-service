import logging

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.upload_client import upload_client, UploadServiceError

from .model import Announcement
from .repo import AnnouncementRepository
from .schema import (
    AnnouncementCreate,
    AnnouncementUpdate,
    PaginatedAnnouncementResponse,
)

logger = logging.getLogger(__name__)


class AnnouncementService:
    def __init__(self):
        self.repo = AnnouncementRepository()

    # ------------------------------------------------------------------
    # Read paths
    # ------------------------------------------------------------------
    async def get_latest_public(self, db, section, limit: int = 5):
        return await self.repo.get_latest_public(db, section, limit)

    async def get_public_history(self, db, section, page: int, limit: int):
        items, total = await self.repo.get_public_history(db, section, page, limit)
        return self._paginate(items, total, page, limit)

    async def get_private_history(self, db, section, user, page: int, limit: int):
        items, total = await self.repo.get_private_history(db, section, user, page, limit)
        return self._paginate(items, total, page, limit)

    async def get_announcement(self, db, announcement_id: str):
        return await self.repo.get_by_id(db, announcement_id)

    async def get_admin_list(
        self,
        db,
        *,
        type,
        section,
        visibility,
        is_active,
        subscription_type,
        data_tier,
        live_tread_access,
        user_data_group,
        device,
        display_start_at,
        display_expire_at,
        page: int,
        size: int,
    ):
        items, total = await self.repo.search(
            db,
            type=type,
            section=section,
            visibility=visibility,
            is_active=is_active,
            subscription_type=subscription_type,
            data_tier=data_tier,
            live_tread_access=live_tread_access,
            user_data_group=user_data_group,
            device=device,
            display_start_at=display_start_at,
            display_expire_at=display_expire_at,
            page=page,
            size=size,
        )
        return self._paginate(items, total, page, size)

    # ------------------------------------------------------------------
    # Write paths
    # ------------------------------------------------------------------
    async def create_announcement(self, db, data: AnnouncementCreate) -> Announcement:
        obj = Announcement(
            text=data.text,
            type=data.type,
            link=data.link,
            button_text=data.button_text,
            image_url=data.image_url,
            sections=[s.value for s in data.sections],
            visibility=data.visibility,
            subscription_types=data.subscription_types,
            target_data_tiers=data.target_data_tiers,
            target_live_tread_access=data.target_live_tread_access,
            target_user_data_groups=data.target_user_data_groups,
            target_devices=data.target_devices,
            display_start_at=data.display_start_at,
            display_expire_at=data.display_expire_at,
            is_active=data.is_active,
        )
        return await self.repo.create(db, obj)

    async def create_announcement_with_upload(
        self,
        db,
        data: AnnouncementCreate,
        file: UploadFile,
    ) -> Announcement:
        upload_result = await upload_client.upload_file(
            file, default_folder=settings.ANNOUNCEMENTS_UPLOAD_FOLDER
        )
        upload_data = upload_result.get("data", {}) or {}

        obj = Announcement(
            text=data.text,
            type=data.type,
            link=data.link,
            button_text=data.button_text,
            image_url=upload_data.get("url") or data.image_url,
            sections=[s.value for s in data.sections],
            visibility=data.visibility,
            subscription_types=data.subscription_types,
            target_data_tiers=data.target_data_tiers,
            target_live_tread_access=data.target_live_tread_access,
            target_user_data_groups=data.target_user_data_groups,
            target_devices=data.target_devices,
            display_start_at=data.display_start_at,
            display_expire_at=data.display_expire_at,
            is_active=data.is_active,
        )
        try:
            return await self.repo.create(db, obj)
        except Exception:
            new_name = upload_data.get("name")
            new_folder = upload_data.get("folder")
            if new_name and new_folder:
                try:
                    await upload_client.delete_file(new_folder, new_name)
                except UploadServiceError:
                    logger.warning("Failed to clean up announcement upload after DB failure")
            raise

    async def update_announcement(self, db, announcement_id: str, data: AnnouncementUpdate):
        announcement = await self.repo.get_by_id(db, announcement_id)
        if not announcement:
            return None

        update_data = data.model_dump(exclude_unset=True)
        new_start = update_data.get("display_start_at", announcement.display_start_at)
        new_expire = update_data.get("display_expire_at", announcement.display_expire_at)
        if new_start and new_expire and new_expire <= new_start:
            raise ValueError("display_expire_at must be after display_start_at")

        if "sections" in update_data and update_data["sections"] is not None:
            update_data["sections"] = [s.value for s in update_data["sections"]]

        for key, value in update_data.items():
            setattr(announcement, key, value)

        await db.commit()
        await db.refresh(announcement)
        logger.info(
            "Updated announcement: %s fields=%s", announcement_id, list(update_data.keys())
        )
        return announcement

    async def update_announcement_with_upload(
        self,
        db,
        announcement_id: str,
        data: AnnouncementUpdate,
        file: UploadFile,
    ):
        announcement = await self.repo.get_by_id(db, announcement_id)
        if not announcement:
            return None

        try:
            upload_result = await upload_client.upload_file(
                file, default_folder=settings.ANNOUNCEMENTS_UPLOAD_FOLDER
            )
        except UploadServiceError as e:
            logger.error("Upload failed during update: %s", e.detail)
            raise

        upload_data = upload_result.get("data", {}) or {}

        update_data = data.model_dump(exclude_unset=True)
        new_start = update_data.get("display_start_at", announcement.display_start_at)
        new_expire = update_data.get("display_expire_at", announcement.display_expire_at)
        if new_start and new_expire and new_expire <= new_start:
            new_name = upload_data.get("name")
            new_folder = upload_data.get("folder")
            if new_name and new_folder:
                try:
                    await upload_client.delete_file(new_folder, new_name)
                except UploadServiceError:
                    logger.warning("Failed to clean invalid announcement upload")
            raise ValueError("display_expire_at must be after display_start_at")

        if "sections" in update_data and update_data["sections"] is not None:
            update_data["sections"] = [s.value for s in update_data["sections"]]
        update_data["image_url"] = upload_data.get("url") or announcement.image_url

        try:
            for key, value in update_data.items():
                setattr(announcement, key, value)
            await db.commit()
            await db.refresh(announcement)
        except Exception:
            await db.rollback()
            new_name = upload_data.get("name")
            new_folder = upload_data.get("folder")
            if new_name and new_folder:
                try:
                    await upload_client.delete_file(new_folder, new_name)
                except UploadServiceError:
                    logger.warning("Failed to clean up announcement upload after DB failure")
            raise

        logger.info("Updated announcement with new image: %s", announcement_id)
        return announcement

    async def delete_announcement(self, db, announcement_id: str) -> bool:
        announcement = await self.repo.get_by_id(db, announcement_id)
        if not announcement:
            return False
        await self.repo.delete(db, announcement)
        return True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _paginate(items, total: int, page: int, size: int) -> PaginatedAnnouncementResponse:
        pages = (total + size - 1) // size if total else 0
        return PaginatedAnnouncementResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )
