import logging
from typing import List, Optional

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.upload_client import UploadServiceError, upload_client

from .model import AdAsset, AdCampaign, AdStats
from .repo import AdAssetRepository, AdCampaignRepository, AdStatsRepository
from .schema import (
    AdAssetUpdate, AdCampaignCreate, AdCampaignUpdate, AdStatsResponse,
    PaginatedAdAssetResponse, PaginatedAdCampaignResponse,
)

logger = logging.getLogger(__name__)


class AdCampaignService:
    def __init__(self):
        self.repo = AdCampaignRepository()
        self.asset_repo = AdAssetRepository()

    async def create_campaign(self, db: AsyncSession, data: AdCampaignCreate) -> AdCampaign:
        campaign = AdCampaign(
            client_name=data.client_name,
            start_at=data.start_at,
            expire_at=data.expire_at,
            is_active=data.is_active,
        )
        return await self.repo.create(db, campaign)

    async def get_campaign(self, db: AsyncSession, campaign_id: str) -> Optional[AdCampaign]:
        return await self.repo.get_by_id(db, campaign_id)

    async def get_all_campaigns(
        self, db: AsyncSession, *, client_name: Optional[str] = None,
        is_active: Optional[bool] = None, start_at=None, expire_at=None,
        page: int = 1, size: int = 20,
    ):
        items, total = await self.repo.get_all_paginated(
            db, client_name=client_name, is_active=is_active, start_at=start_at,
            expire_at=expire_at, page=page, size=size,
        )
        pages = (total + size - 1) // size if total else 0
        return PaginatedAdCampaignResponse(items=items, total=total, page=page, size=size, pages=pages)

    async def _validate_campaign_positions(
        self, db: AsyncSession, campaign_id: str, start_at, expire_at, is_active: bool,
    ) -> None:
        if not settings.ADS_POSITION_CONFLICT_CHECK_ENABLED or not is_active:
            return
        assets = await self.asset_repo.get_all_by_campaign(db, campaign_id)
        for asset in assets:
            conflict = await self.asset_repo.find_active_position_conflict(
                db,
                platform=asset.platform,
                position=asset.position,
                start_at=start_at,
                expire_at=expire_at,
                exclude_campaign_id=campaign_id,
            )
            if conflict:
                raise ValueError(
                    f"Position conflict: platform={asset.platform}, position={asset.position} "
                    f"is already reserved by campaign {conflict.campaign_id} during the overlapping schedule"
                )

    async def update_campaign(
        self, db: AsyncSession, campaign_id: str, data: AdCampaignUpdate,
    ) -> Optional[AdCampaign]:
        campaign = await self.repo.get_by_id(db, campaign_id)
        if not campaign:
            return None

        update_data = data.model_dump(exclude_unset=True)
        new_start = update_data.get("start_at", campaign.start_at)
        new_expire = update_data.get("expire_at", campaign.expire_at)
        new_active = update_data.get("is_active", campaign.is_active)
        if new_expire <= new_start:
            raise ValueError("expire_at must be after start_at")

        await self._validate_campaign_positions(db, campaign_id, new_start, new_expire, new_active)

        for key, value in update_data.items():
            setattr(campaign, key, value)
        await db.commit()
        await db.refresh(campaign)
        logger.info("Updated ad campaign: %s fields=%s", campaign_id, list(update_data.keys()))
        return campaign

    async def delete_campaign(self, db: AsyncSession, campaign_id: str) -> Optional[AdCampaign]:
        campaign = await self.repo.get_by_id(db, campaign_id)
        if not campaign:
            return None
        await self.repo.delete(db, campaign)
        return campaign


class AdAssetService:
    def __init__(self):
        self.repo = AdAssetRepository()
        self.campaign_repo = AdCampaignRepository()

    def _validate_position(self, position: int) -> None:
        if not settings.ADS_MIN_POSITION <= position <= settings.ADS_MAX_POSITION:
            raise ValueError(
                f"position must be between {settings.ADS_MIN_POSITION} and {settings.ADS_MAX_POSITION}"
            )

    async def _validate_placement(
        self, db: AsyncSession, campaign: AdCampaign, platform: str, position: int,
        exclude_asset_id: str | None = None,
    ) -> None:
        self._validate_position(position)
        duplicate = await self.repo.get_same_campaign_position(
            db, str(campaign.id), platform, position, exclude_asset_id=exclude_asset_id
        )
        if duplicate:
            raise ValueError(
                f"Campaign already has an asset at platform={platform}, position={position}"
            )

        if settings.ADS_POSITION_CONFLICT_CHECK_ENABLED and campaign.is_active:
            conflict = await self.repo.find_active_position_conflict(
                db,
                platform=platform,
                position=position,
                start_at=campaign.start_at,
                expire_at=campaign.expire_at,
                exclude_campaign_id=str(campaign.id),
            )
            if conflict:
                raise ValueError(
                    f"Position conflict: platform={platform}, position={position} is already "
                    f"reserved by campaign {conflict.campaign_id} during the overlapping schedule"
                )

    async def get_asset(self, db: AsyncSession, asset_id: str) -> Optional[AdAsset]:
        return await self.repo.get_by_id(db, asset_id)

    async def get_assets_by_campaign(
        self, db: AsyncSession, campaign_id: str, page: int = 1, size: int = 20,
    ):
        items, total = await self.repo.get_by_campaign(db, campaign_id, page, size)
        pages = (total + size - 1) // size if total else 0
        return PaginatedAdAssetResponse(items=items, total=total, page=page, size=size, pages=pages)

    async def create_asset(self, db: AsyncSession, campaign_id: str, data: dict) -> AdAsset:
        campaign = await self.campaign_repo.get_by_id(db, campaign_id)
        if not campaign:
            raise ValueError("Campaign not found")
        await self._validate_placement(db, campaign, data["platform"], data["position"])
        asset = AdAsset(
            campaign_id=campaign_id,
            platform=data["platform"],
            position=data["position"],
            title=data.get("title"),
            image_url=data.get("image_url", ""),
            link_url=data.get("link_url", ""),
        )
        return await self.repo.create(db, asset)

    async def create_asset_with_upload(
        self, db: AsyncSession, campaign_id: str, data: dict, file: UploadFile,
    ) -> AdAsset:
        campaign = await self.campaign_repo.get_by_id(db, campaign_id)
        if not campaign:
            raise ValueError("Campaign not found")
        await self._validate_placement(db, campaign, data["platform"], data["position"])

        upload_result = await upload_client.upload_file(file, default_folder=settings.ADS_UPLOAD_FOLDER)
        upload_data = upload_result.get("data", {}) or {}
        asset = AdAsset(
            campaign_id=campaign_id,
            platform=data["platform"],
            position=data["position"],
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

    async def update_asset(
        self, db: AsyncSession, asset_id: str, data: AdAssetUpdate,
    ) -> Optional[AdAsset]:
        asset = await self.repo.get_by_id(db, asset_id)
        if not asset:
            return None
        campaign = await self.campaign_repo.get_by_id(db, asset.campaign_id)
        if not campaign:
            raise ValueError("Campaign not found")

        update_data = data.model_dump(exclude_unset=True)
        new_platform = update_data.get("platform", asset.platform)
        if hasattr(new_platform, "value"):
            new_platform = new_platform.value
        new_position = update_data.get("position", asset.position)
        await self._validate_placement(
            db, campaign, new_platform, new_position, exclude_asset_id=str(asset.id)
        )

        if "platform" in update_data and hasattr(update_data["platform"], "value"):
            update_data["platform"] = update_data["platform"].value
        for key, value in update_data.items():
            setattr(asset, key, value)
        await db.commit()
        await db.refresh(asset)
        logger.info("Updated ad asset: %s fields=%s", asset_id, list(update_data.keys()))
        return asset

    async def delete_asset(self, db: AsyncSession, asset_id: str) -> Optional[AdAsset]:
        asset = await self.repo.get_by_id(db, asset_id)
        if not asset:
            return None
        await self.repo.delete(db, asset)
        return asset

    async def get_active_assets(self, db: AsyncSession, platform: str) -> List[AdAsset]:
        return await self.repo.get_active_by_platform(db, platform)


class AdStatsService:
    def __init__(self):
        self.repo = AdStatsRepository()

    async def upsert_bulk(self, db: AsyncSession, items: list[dict]) -> List[AdStats]:
        return await self.repo.upsert_bulk(db, items)

    async def get_stats_by_asset(self, db: AsyncSession, asset_id: str, page: int = 1, size: int = 20):
        items, total = await self.repo.get_by_asset(db, asset_id, page, size)
        pages = (total + size - 1) // size if total else 0
        return AdStatsResponse(items=items, total=total, page=page, size=size, pages=pages)

    async def get_stats_by_campaign(self, db: AsyncSession, campaign_id: str, page: int = 1, size: int = 20):
        items, total = await self.repo.get_by_campaign(db, campaign_id, page, size)
        pages = (total + size - 1) // size if total else 0
        return AdStatsResponse(items=items, total=total, page=page, size=size, pages=pages)
