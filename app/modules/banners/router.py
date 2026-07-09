from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.shared.enums import BannerPlatform
from .service import BannerService
from .schema import BannerResponse

router = APIRouter(tags=["Banners"])

service = BannerService()


# -------------------------
# Public: Get Active Banners
# -------------------------
@router.get("/", response_model=list[BannerResponse])
async def get_banners(
    # Validate against the same enum used by the admin/POST/upload paths
    # so callers get a 422 for bad values instead of a silent empty list.
    platform: BannerPlatform = Query(...),
    db: AsyncSession = Depends(get_session)
):
    return await service.get_active_banners(db, platform.value)
