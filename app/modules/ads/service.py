import logging
from typing import List, Optional

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.upload_client import upload_client, UploadServiceError

from .model import AdCampaign, AdAsset, AdStats
from .repo import AdCampaignRepository, AdAssetRepository, AdStatsRepository
from .schema import (
    AdCampaignCreate,
    AdCampaignUpdate,
    PaginatedAdCampaignResponse,
    PaginatedAdAssetResponse,
    AdStatsResponse,
)

logger = logging.getLogger(__name__)


class AdCampaignService:

    def __init__(self):
        self.repo = AdCampaignRepository()

    async def create_campaign(
        self, db: AsyncSession, data: AdCampaignCreate
    ) -> AdCampaign:
        campaign = AdCampaign(
            client_name=data.client_name,
            start_at=data.start_at,
            expire_at=data.expire_at,
            is_active=data.is_active,
        )
        return await self.repo.create(db, campaign)

    async def get_campaign(
        self, db: AsyncSession, campaign_id: str
    ) -> Optional[AdCampaign]:
        return await self.repo.get_by_id(db, campaign_id)

    async def get_all_campaigns(
        self,
        db: AsyncSession,
        *,
        client_name: Optional[str] = None,
        is_active: Optional[bool] = None,
        start_at=None,
        expire_at=None,
        page: int = 1,
        size: int = 20,
    ):
        items, total = await self.repo.get_all_paginated(
            db,
            client_name=client_name,
            is_active=is_active,
            start_at=start_at,
            expire_at=expire_at,
            page=page,
            size=size,
        )
        pages = (total + size - 1) // size if total else 0
        return PaginatedAdCampaignResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )

    async def update_campaign(
        self, db: AsyncSession, campaign_id: str, data: AdCampaignUpdate
    ) -> Optional[AdCampaign]:
        campaign = await self.repo.get_by_id(db, campaign_id)
        if not campaign:
            return None

        update_data = data.model_dump(exclude_unset=True)

        new_start = update_data.get("start_at", campaign.start_at)
        new_expire = update_data.get("expire_at", campaign.expire_at)
        if new_start and new_expire and new_expire <= new_start:
            raise ValueError("expire_at must be after start_at")

        for key, value in update_data.items():
            setattr(campaign, key, value)

        await db.commit()
        await db.refresh(campaign)
        logger.info(
            "Updated ad campaign: %s fields=%s", campaign_id, list(update_data.keys())
        )
        return campaign

    async def delete_campaign(
        self, db: AsyncSession, campaign_id: str
    ) -> Optional[AdCampaign]:
        campaign = await self.repo.get_by_id(db, campaign_id)
        if not campaign:
            return None
        await self.repo.delete(db, campaign)
        return campaign


class AdAssetService:

    def __init__(self):
        self.repo = AdAssetRepository()

    async def get_asset(
        self, db: AsyncSession, asset_id: str
    ) -> Optional[AdAsset]:
        return await self.repo.get_by_id(db, asset_id)

    async def get_assets_by_campaign(
        self, db: AsyncSession, campaign_id: str, page: int = 1, size: int = 20
    ):
        items, total = await self.repo.get_by_campaign(db, campaign_id, page, size)
        pages = (total + size - 1) // size if total else 0
        return PaginatedAdAssetResponse(
            items=items, total=total, page=page, size=size, pages=pages,
        )

    async def create_asset(
        self, db: AsyncSession, campaign_id: str, data: dict
    ) -> Optional[AdAsset]:
        asset = AdAsset(
            campaign_id=campaign_id,
            platform=data["platform"],
            title=data.get("title"),
            image_url=data.get("image_url", ""),
            link_url=data.get("link_url", ""),
        )
        return await self.repo.create(db, asset)

    async def create_asset_with_upload(
        self,
        db: AsyncSession,
        campaign_id: str,
        data: dict,
        file: UploadFile,
    ) -> Optional[AdAsset]:
        try:
            upload_result = await upload_client.upload_file(
                file, default_folder=settings.ADS_UPLOAD_FOLDER
            )
        except UploadServiceError as e:
            logger.error("Upload failed: %s", e.detail)
            raise

        upload_data = upload_result.get("data", {}) or {}
        asset = AdAsset(
            campaign_id=campaign_id,
            platform=data["platform"],
            title=data.get("title"),
            image_url=upload_data.get("url") or data.get("image_url", ""),
            link_url=data.get("link_url", ""),
        )
        try:
            return await self.repo.create(db, asset)
        except Exception:
            new_name = upload_data.get("name")
            new_folder = upload_data.get("folder")
            if new_name and new_folder:
                try:
                    await upload_client.delete_file(new_folder, new_name)
                except UploadServiceError:
                    logger.warning("Failed to clean up ad upload after DB failure")
            raise

    async def delete_asset(
        self, db: AsyncSession, asset_id: str
    ) -> Optional[AdAsset]:
        asset = await self.repo.get_by_id(db, asset_id)
        if not asset:
            return None
        await self.repo.delete(db, asset)
        return asset

    async def get_active_assets(
        self, db: AsyncSession, platform: str
    ) -> List[AdAsset]:
        return await self.repo.get_active_by_platform(db, platform)


class AdStatsService:

    def __init__(self):
        self.repo = AdStatsRepository()

    async def upsert_bulk(
        self, db: AsyncSession, items: list[dict]
    ) -> List[AdStats]:
        results = await self.repo.upsert_bulk(db, items)
        return results

    async def get_stats_by_asset(
        self, db: AsyncSession, asset_id: str, page: int = 1, size: int = 20
    ):
        items, total = await self.repo.get_by_asset(db, asset_id, page, size)
        pages = (total + size - 1) // size if total else 0
        return AdStatsResponse(
            items=items, total=total, page=page, size=size, pages=pages,
        )

    async def get_stats_by_campaign(
        self, db: AsyncSession, campaign_id: str, page: int = 1, size: int = 20
    ):
        items, total = await self.repo.get_by_campaign(db, campaign_id, page, size)
        pages = (total + size - 1) // size if total else 0
        return AdStatsResponse(
            items=items, total=total, page=page, size=size, pages=pages,
        )
