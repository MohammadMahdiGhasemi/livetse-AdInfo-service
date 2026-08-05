import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.shared.enums import AdPlatform

from .schema import AdAssetResponse
from .service import AdAssetService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Ads"])

asset_service = AdAssetService()


# ---------------------------------------------------------------------------
# GET /ads/ — active assets by platform
# ---------------------------------------------------------------------------
@router.get("/", response_model=list[AdAssetResponse])
async def get_ads(
    platform: AdPlatform = Query(...),
    db: AsyncSession = Depends(get_session),
):
    return await asset_service.get_active_assets(db, platform.value)
