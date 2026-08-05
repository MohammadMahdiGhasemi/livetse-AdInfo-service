import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from .model import AdCampaign, AdAsset, AdStats

logger = logging.getLogger(__name__)


class AdCampaignRepository:

    async def create(self, db: AsyncSession, campaign: AdCampaign) -> AdCampaign:
        db.add(campaign)
        await db.commit()
        await db.refresh(campaign)
        logger.info("Created ad campaign: %s", campaign.id)
        return campaign

    async def get_by_id(
        self, db: AsyncSession, campaign_id: str
    ) -> Optional[AdCampaign]:
        result = await db.execute(
            select(AdCampaign).filter(AdCampaign.id == campaign_id)
        )
        return result.scalar_one_or_none()

    async def get_all_paginated(
        self,
        db: AsyncSession,
        *,
        client_name: Optional[str] = None,
        is_active: Optional[bool] = None,
        start_at: Optional[datetime] = None,
        expire_at: Optional[datetime] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[AdCampaign], int]:
        clauses = []
        if client_name is not None:
            clauses.append(AdCampaign.client_name.ilike(f"%{client_name}%"))
        if is_active is not None:
            clauses.append(AdCampaign.is_active.is_(is_active))
        if start_at is not None:
            clauses.append(AdCampaign.start_at >= start_at)
        if expire_at is not None:
            clauses.append(AdCampaign.expire_at <= expire_at)

        where = and_(*clauses) if clauses else True
        offset = (page - 1) * size

        count_q = await db.execute(
            select(func.count(AdCampaign.id)).filter(where)
        )
        total = count_q.scalar() or 0

        result = await db.execute(
            select(AdCampaign)
            .filter(where)
            .order_by(AdCampaign.created_at.desc())
            .offset(offset)
            .limit(size)
        )
        items = list(result.scalars().all())
        return items, total

    async def delete(self, db: AsyncSession, campaign: AdCampaign) -> None:
        campaign_id = campaign.id
        await db.delete(campaign)
        await db.commit()
        logger.info("Deleted ad campaign: %s", campaign_id)


class AdAssetRepository:

    async def create(self, db: AsyncSession, asset: AdAsset) -> AdAsset:
        db.add(asset)
        await db.commit()
        await db.refresh(asset)
        logger.info("Created ad asset: %s", asset.id)
        return asset

    async def get_by_id(
        self, db: AsyncSession, asset_id: str
    ) -> Optional[AdAsset]:
        result = await db.execute(
            select(AdAsset).filter(AdAsset.id == asset_id)
        )
        return result.scalar_one_or_none()

    async def get_by_campaign(
        self,
        db: AsyncSession,
        campaign_id: str,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[AdAsset], int]:
        offset = (page - 1) * size

        count_q = await db.execute(
            select(func.count(AdAsset.id)).filter(
                AdAsset.campaign_id == campaign_id
            )
        )
        total = count_q.scalar() or 0

        result = await db.execute(
            select(AdAsset)
            .filter(AdAsset.campaign_id == campaign_id)
            .order_by(AdAsset.created_at.desc())
            .offset(offset)
            .limit(size)
        )
        items = list(result.scalars().all())
        return items, total

    async def get_active_by_platform(
        self, db: AsyncSession, platform: str
    ) -> List[AdAsset]:
        now = datetime.now(timezone.utc)

        result = await db.execute(
            select(AdAsset)
            .join(AdAsset.campaign)
            .filter(
                AdAsset.platform == platform,
                AdCampaign.is_active.is_(True),
                AdCampaign.start_at <= now,
                AdCampaign.expire_at >= now,
            )
            .order_by(AdAsset.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete(self, db: AsyncSession, asset: AdAsset) -> None:
        asset_id = asset.id
        await db.delete(asset)
        await db.commit()
        logger.info("Deleted ad asset: %s", asset_id)


class AdStatsRepository:

    async def upsert_bulk(
        self, db: AsyncSession, items: list[dict]
    ) -> List[AdStats]:
        if not items:
            return []

        seen: dict[tuple, dict] = {}
        for item in items:
            key = (item["asset_id"], str(item["date"]))
            seen[key] = item
        deduped = list(seen.values())

        stmt = insert(AdStats).values(deduped)
        stmt = stmt.on_conflict_do_update(
            index_elements=["asset_id", "date"],
            set_={
                "views_count": stmt.excluded.views_count,
                "clicks_count": stmt.excluded.clicks_count,
            },
        )
        await db.execute(stmt)
        await db.commit()

        asset_ids = list({item["asset_id"] for item in deduped})
        stat_dates = list({item["date"] for item in deduped})
        result = await db.execute(
            select(AdStats).filter(
                AdStats.asset_id.in_(asset_ids),
                AdStats.date.in_(stat_dates),
            )
        )
        return list(result.scalars().all())

    async def get_by_asset(
        self,
        db: AsyncSession,
        asset_id: str,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[AdStats], int]:
        offset = (page - 1) * size

        count_q = await db.execute(
            select(func.count(AdStats.id)).filter(AdStats.asset_id == asset_id)
        )
        total = count_q.scalar() or 0

        result = await db.execute(
            select(AdStats)
            .filter(AdStats.asset_id == asset_id)
            .order_by(AdStats.date.desc())
            .offset(offset)
            .limit(size)
        )
        items = list(result.scalars().all())
        return items, total

    async def get_by_campaign(
        self,
        db: AsyncSession,
        campaign_id: str,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[AdStats], int]:
        offset = (page - 1) * size

        count_q = await db.execute(
            select(func.count(AdStats.id))
            .join(AdAsset, AdAsset.id == AdStats.asset_id)
            .filter(AdAsset.campaign_id == campaign_id)
        )
        total = count_q.scalar() or 0

        result = await db.execute(
            select(AdStats)
            .join(AdAsset, AdAsset.id == AdStats.asset_id)
            .filter(AdAsset.campaign_id == campaign_id)
            .order_by(AdStats.date.desc())
            .offset(offset)
            .limit(size)
        )
        items = list(result.scalars().all())
        return items, total
