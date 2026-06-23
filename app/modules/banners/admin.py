import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_session
from app.core.config import settings
from .service import BannerService
from .schema import BannerCreate, BannerResponse, BannerUpdate, PaginatedBannerResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Banners-Admin"])

service = BannerService()


async def verify_admin_authorization(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    token = authorization.replace("Bearer ", "")
    if token != settings.ADMIN_PASSWORD:
        logger.warning(f"Invalid admin authorization attempt")
        raise HTTPException(status_code=403, detail="Invalid authorization")

    return token


# -------------------------
# Admin: List All Banners
# -------------------------
@router.get("/admin", response_model=PaginatedBannerResponse)
async def list_banners(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
    _: str = Depends(verify_admin_authorization)
):
    return await service.get_all_banners(db, page, size)


# -------------------------
# Admin: Get Banner by ID
# -------------------------
@router.get("/admin/{banner_id}", response_model=BannerResponse)
async def get_banner(
    banner_id: str,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(verify_admin_authorization)
):
    banner = await service.get_banner(db, banner_id)
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    return banner


# -------------------------
# Admin: Create Banner
# -------------------------
@router.post("/admin", response_model=BannerResponse, status_code=201)
async def create_banner(
    data: BannerCreate,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(verify_admin_authorization)
):
    return await service.create_banner(db, data)


# -------------------------
# Admin: Update Banner
# -------------------------
@router.put("/admin/{banner_id}", response_model=BannerResponse)
async def update_banner(
    banner_id: str,
    data: BannerUpdate,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(verify_admin_authorization)
):
    banner = await service.update_banner(db, banner_id, data)
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    return banner


# -------------------------
# Admin: Delete Banner
# -------------------------
@router.delete("/admin/{banner_id}")
async def delete_banner(
    banner_id: str,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(verify_admin_authorization)
):
    banner = await service.delete_banner(db, banner_id)
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    return {"message": "Banner deleted", "id": banner_id}
