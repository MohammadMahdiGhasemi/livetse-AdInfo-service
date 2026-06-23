from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from .service import BannerService
from .schema import BannerResponse

router = APIRouter(tags=["Banners"])

service = BannerService()


# -------------------------
# Public: Get Active Banners
# -------------------------
@router.get("/", response_model=list[BannerResponse])
async def get_banners(
    platform: str = Query(..., description="landing | extension"),
    db: AsyncSession = Depends(get_session)
):
    return await service.get_active_banners(db, platform)
