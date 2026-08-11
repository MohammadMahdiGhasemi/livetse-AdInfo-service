import logging
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import require_admin
from app.shared.enums import AdPlatform
from app.services.upload_client import UploadServiceError

from .schema import (
    AdAssetResponse, AdAssetUpdate, AdCampaignCreate, AdCampaignResponse,
    AdCampaignUpdate, AdStatsBulkRequest, AdStatsRecord, AdStatsResponse,
    PaginatedAdAssetResponse, PaginatedAdCampaignResponse,
)
from .service import AdAssetService, AdCampaignService, AdStatsService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Ads-Admin"])
campaign_service = AdCampaignService()
asset_service = AdAssetService()
stats_service = AdStatsService()


@router.get("/admin", response_model=PaginatedAdCampaignResponse)
async def list_campaigns(
    client_name: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    start_at: Optional[datetime] = Query(default=None),
    expire_at: Optional[datetime] = Query(default=None),
    page: int = Query(default=1, ge=1), size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_session), _=Depends(require_admin),
):
    return await campaign_service.get_all_campaigns(
        db, client_name=client_name, is_active=is_active, start_at=start_at,
        expire_at=expire_at, page=page, size=size,
    )


@router.get("/admin/{campaign_id}", response_model=AdCampaignResponse)
async def get_campaign(campaign_id: UUID, db: AsyncSession = Depends(get_session), _=Depends(require_admin)):
    campaign = await campaign_service.get_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.post("/admin", response_model=AdCampaignResponse, status_code=201)
async def create_campaign(data: AdCampaignCreate, db: AsyncSession = Depends(get_session), _=Depends(require_admin)):
    return await campaign_service.create_campaign(db, data)


@router.put("/admin/{campaign_id}", response_model=AdCampaignResponse)
async def update_campaign(
    campaign_id: UUID, data: AdCampaignUpdate,
    db: AsyncSession = Depends(get_session), _=Depends(require_admin),
):
    try:
        campaign = await campaign_service.update_campaign(db, campaign_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.delete("/admin/{campaign_id}")
async def delete_campaign(campaign_id: UUID, db: AsyncSession = Depends(get_session), _=Depends(require_admin)):
    campaign = await campaign_service.delete_campaign(db, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {"message": "Campaign deleted", "id": campaign_id}


@router.get("/admin/{campaign_id}/assets", response_model=PaginatedAdAssetResponse)
async def list_assets(
    campaign_id: UUID, page: int = Query(default=1, ge=1), size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_session), _=Depends(require_admin),
):
    if not await campaign_service.get_campaign(db, campaign_id):
        raise HTTPException(status_code=404, detail="Campaign not found")
    return await asset_service.get_assets_by_campaign(db, campaign_id, page, size)


@router.get("/admin/assets/{asset_id}", response_model=AdAssetResponse)
async def get_asset(asset_id: UUID, db: AsyncSession = Depends(get_session), _=Depends(require_admin)):
    asset = await asset_service.get_asset(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.post("/admin/{campaign_id}/assets", response_model=AdAssetResponse, status_code=201)
async def create_asset(
    campaign_id: UUID,
    platform: AdPlatform = Form(...),
    position: int = Form(..., ge=1),
    title: Optional[str] = Form(default=None),
    image_url: str = Form(default=""),
    link_url: str = Form(default=""),
    db: AsyncSession = Depends(get_session), _=Depends(require_admin),
):
    if not await campaign_service.get_campaign(db, campaign_id):
        raise HTTPException(status_code=404, detail="Campaign not found")
    try:
        return await asset_service.create_asset(db, campaign_id, {
            "platform": platform.value, "position": position, "title": title,
            "image_url": image_url, "link_url": link_url,
        })
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/admin/{campaign_id}/assets/upload", response_model=AdAssetResponse, status_code=201)
async def create_asset_with_upload(
    campaign_id: UUID,
    file: UploadFile = File(...),
    platform: AdPlatform = Form(...),
    position: int = Form(..., ge=1),
    title: Optional[str] = Form(default=None),
    link_url: str = Form(default=""),
    db: AsyncSession = Depends(get_session), _=Depends(require_admin),
):
    if not await campaign_service.get_campaign(db, campaign_id):
        raise HTTPException(status_code=404, detail="Campaign not found")
    try:
        return await asset_service.create_asset_with_upload(db, campaign_id, {
            "platform": platform.value, "position": position, "title": title, "link_url": link_url,
        }, file)
    except UploadServiceError as exc:
        logger.error("Upload service failed: %s", exc.detail)
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.put("/admin/assets/{asset_id}", response_model=AdAssetResponse)
async def update_asset(
    asset_id: UUID, data: AdAssetUpdate,
    db: AsyncSession = Depends(get_session), _=Depends(require_admin),
):
    try:
        asset = await asset_service.update_asset(db, asset_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.delete("/admin/assets/{asset_id}")
async def delete_asset(asset_id: UUID, db: AsyncSession = Depends(get_session), _=Depends(require_admin)):
    asset = await asset_service.delete_asset(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"message": "Asset deleted", "id": asset_id}


@router.post("/admin/stats", response_model=list[AdStatsRecord], status_code=201)
async def upsert_stats(data: AdStatsBulkRequest, db: AsyncSession = Depends(get_session), _=Depends(require_admin)):
    for item in data.stats:
        if not await asset_service.get_asset(db, item.asset_id):
            raise HTTPException(status_code=404, detail=f"Asset not found: {item.asset_id}")
    return await stats_service.upsert_bulk(db, [
        {"asset_id": item.asset_id, "date": item.date, "views_count": item.views_count, "clicks_count": item.clicks_count}
        for item in data.stats
    ])


@router.get("/admin/assets/{asset_id}/stats", response_model=AdStatsResponse)
async def get_asset_stats(
    asset_id: UUID, page: int = Query(default=1, ge=1), size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_session), _=Depends(require_admin),
):
    if not await asset_service.get_asset(db, asset_id):
        raise HTTPException(status_code=404, detail="Asset not found")
    return await stats_service.get_stats_by_asset(db, asset_id, page, size)


@router.get("/admin/{campaign_id}/stats", response_model=AdStatsResponse)
async def get_campaign_stats(
    campaign_id: UUID, page: int = Query(default=1, ge=1), size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_session), _=Depends(require_admin),
):
    if not await campaign_service.get_campaign(db, campaign_id):
        raise HTTPException(status_code=404, detail="Campaign not found")
    return await stats_service.get_stats_by_campaign(db, campaign_id, page, size)
