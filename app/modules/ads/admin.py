import logging
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from fastapi import (
    APIRouter, Depends, File, Form, HTTPException,
    Query, UploadFile,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import require_admin
from app.shared.enums import AdPlatform
from app.services.upload_client import UploadServiceError

from .schema import (
    AdCampaignCreate,
    AdCampaignUpdate,
    AdCampaignResponse,
    AdAssetResponse,
    AdStatsBulkRequest,
    AdStatsRecord,
    PaginatedAdCampaignResponse,
    PaginatedAdAssetResponse,
    AdStatsResponse,
)
from .service import AdCampaignService, AdAssetService, AdStatsService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Ads-Admin"])

campaign_service = AdCampaignService()
asset_service = AdAssetService()
stats_service = AdStatsService()


# ---------------------------------------------------------------------------
# Admin authorization
# ---------------------------------------------------------------------------


# ===========================================================================
# Campaign endpoints
# ===========================================================================

# ---------------------------------------------------------------------------
# GET /ads/admin — list campaigns with filters
# ---------------------------------------------------------------------------
@router.get(
    "/admin",
    response_model=PaginatedAdCampaignResponse,
)
async def list_campaigns(
    client_name: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    start_at: Optional[datetime] = Query(default=None),
    expire_at: Optional[datetime] = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
    _ = Depends(require_admin),
):
    return await campaign_service.get_all_campaigns(
        db,
        client_name=client_name,
        is_active=is_active,
        start_at=start_at,
        expire_at=expire_at,
        page=page,
        size=size,
    )


# ---------------------------------------------------------------------------
# GET /ads/admin/{campaign_id}
# ---------------------------------------------------------------------------
@router.get(
    "/admin/{campaign_id}",
    response_model=AdCampaignResponse,
)
async def get_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_session),
    _ = Depends(require_admin),
):
    campaign = await campaign_service.get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


# ---------------------------------------------------------------------------
# POST /ads/admin — create campaign
# ---------------------------------------------------------------------------
@router.post(
    "/admin",
    response_model=AdCampaignResponse,
    status_code=201,
)
async def create_campaign(
    data: AdCampaignCreate,
    db: AsyncSession = Depends(get_session),
    _ = Depends(require_admin),
):
    return await campaign_service.create_campaign(db, data)


# ---------------------------------------------------------------------------
# PUT /ads/admin/{campaign_id}
# ---------------------------------------------------------------------------
@router.put(
    "/admin/{campaign_id}",
    response_model=AdCampaignResponse,
)
async def update_campaign(
    campaign_id: UUID,
    data: AdCampaignUpdate,
    db: AsyncSession = Depends(get_session),
    _ = Depends(require_admin),
):
    try:
        campaign = await campaign_service.update_campaign(db, campaign_id, data)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


# ---------------------------------------------------------------------------
# DELETE /ads/admin/{campaign_id}
# ---------------------------------------------------------------------------
@router.delete("/admin/{campaign_id}")
async def delete_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_session),
    _ = Depends(require_admin),
):
    campaign = await campaign_service.delete_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {"message": "Campaign deleted", "id": campaign_id}


# ===========================================================================
# Asset endpoints
# ===========================================================================

# ---------------------------------------------------------------------------
# GET /ads/admin/{campaign_id}/assets — list assets for a campaign
# ---------------------------------------------------------------------------
@router.get(
    "/admin/{campaign_id}/assets",
    response_model=PaginatedAdAssetResponse,
)
async def list_assets(
    campaign_id: UUID,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
    _ = Depends(require_admin),
):
    campaign = await campaign_service.get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return await asset_service.get_assets_by_campaign(db, campaign_id, page, size)


# ---------------------------------------------------------------------------
# GET /ads/admin/assets/{asset_id}
# ---------------------------------------------------------------------------
@router.get(
    "/admin/assets/{asset_id}",
    response_model=AdAssetResponse,
)
async def get_asset(
    asset_id: UUID,
    db: AsyncSession = Depends(get_session),
    _ = Depends(require_admin),
):
    asset = await asset_service.get_asset(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


# ---------------------------------------------------------------------------
# POST /ads/admin/{campaign_id}/assets — create asset (JSON)
# ---------------------------------------------------------------------------
@router.post(
    "/admin/{campaign_id}/assets",
    response_model=AdAssetResponse,
    status_code=201,
)
async def create_asset(
    campaign_id: UUID,
    platform: str = Form(...),
    title: Optional[str] = Form(default=None),
    image_url: str = Form(default=""),
    link_url: str = Form(default=""),
    db: AsyncSession = Depends(get_session),
    _ = Depends(require_admin),
):
    campaign = await campaign_service.get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    try:
        platform_enum = AdPlatform(platform)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid platform '{platform}'. Allowed: "
                   f"{[p.value for p in AdPlatform]}",
        )

    data = {
        "platform": platform_enum.value,
        "title": title,
        "image_url": image_url,
        "link_url": link_url,
    }
    return await asset_service.create_asset(db, campaign_id, data)


# ---------------------------------------------------------------------------
# POST /ads/admin/{campaign_id}/assets/upload — create asset with file
# ---------------------------------------------------------------------------
@router.post(
    "/admin/{campaign_id}/assets/upload",
    response_model=AdAssetResponse,
    status_code=201,
)
async def create_asset_with_upload(
    campaign_id: UUID,
    file: UploadFile = File(...),
    platform: str = Form(...),
    title: Optional[str] = Form(default=None),
    link_url: str = Form(default=""),
    db: AsyncSession = Depends(get_session),
    _ = Depends(require_admin),
):
    campaign = await campaign_service.get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    try:
        platform_enum = AdPlatform(platform)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid platform '{platform}'. Allowed: "
                   f"{[p.value for p in AdPlatform]}",
        )

    data = {
        "platform": platform_enum.value,
        "title": title,
        "link_url": link_url,
    }
    try:
        return await asset_service.create_asset_with_upload(db, campaign_id, data, file)
    except UploadServiceError as e:
        logger.error("Upload service failed: %s", e.detail)
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e


# ---------------------------------------------------------------------------
# DELETE /ads/admin/assets/{asset_id}
# ---------------------------------------------------------------------------
@router.delete("/admin/assets/{asset_id}")
async def delete_asset(
    asset_id: UUID,
    db: AsyncSession = Depends(get_session),
    _ = Depends(require_admin),
):
    asset = await asset_service.delete_asset(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"message": "Asset deleted", "id": asset_id}


# ===========================================================================
# Stats endpoints
# ===========================================================================

# ---------------------------------------------------------------------------
# POST /ads/admin/stats — bulk upsert stats
# ---------------------------------------------------------------------------
@router.post(
    "/admin/stats",
    response_model=list[AdStatsRecord],
    status_code=201,
)
async def upsert_stats(
    data: AdStatsBulkRequest,
    db: AsyncSession = Depends(get_session),
    _ = Depends(require_admin),
):
    for item in data.stats:
        asset = await asset_service.get_asset(db, item.asset_id)
        if not asset:
            raise HTTPException(
                status_code=404,
                detail=f"Asset not found: {item.asset_id}",
            )

    stats_dicts = [
        {
            "asset_id": item.asset_id,
            "date": item.date,
            "views_count": item.views_count,
            "clicks_count": item.clicks_count,
        }
        for item in data.stats
    ]
    return await stats_service.upsert_bulk(db, stats_dicts)


# ---------------------------------------------------------------------------
# GET /ads/admin/assets/{asset_id}/stats — stats for an asset
# ---------------------------------------------------------------------------
@router.get(
    "/admin/assets/{asset_id}/stats",
    response_model=AdStatsResponse,
)
async def get_asset_stats(
    asset_id: UUID,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
    _ = Depends(require_admin),
):
    asset = await asset_service.get_asset(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return await stats_service.get_stats_by_asset(db, asset_id, page, size)


# ---------------------------------------------------------------------------
# GET /ads/admin/{campaign_id}/stats — stats for a campaign
# ---------------------------------------------------------------------------
@router.get(
    "/admin/{campaign_id}/stats",
    response_model=AdStatsResponse,
)
async def get_campaign_stats(
    campaign_id: UUID,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
    _ = Depends(require_admin),
):
    campaign = await campaign_service.get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return await stats_service.get_stats_by_campaign(db, campaign_id, page, size)
