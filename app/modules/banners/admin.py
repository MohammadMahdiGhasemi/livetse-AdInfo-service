import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Header, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_session
from app.core.config import settings
from .service import BannerService
from .schema import (
    BannerCreate,
    BannerResponse,
    BannerUpdate,
    BannerUploadResponse,
    PaginatedBannerResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Banners-Admin"])

service = BannerService()


async def verify_admin_authorization(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    token = authorization.replace("Bearer ", "")
    if token != settings.ADMIN_PASSWORD:
        logger.warning("Invalid admin authorization attempt")
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
    _: str = Depends(verify_admin_authorization),
):
    return await service.get_all_banners(db, page, size)


# -------------------------
# Admin: Get Banner by ID
# -------------------------
@router.get("/admin/{banner_id}", response_model=BannerResponse)
async def get_banner(
    banner_id: str,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(verify_admin_authorization),
):
    banner = await service.get_banner(db, banner_id)
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    return banner


# -------------------------
# Admin: Create Banner (JSON)
# -------------------------
@router.post("/admin", response_model=BannerResponse, status_code=201)
async def create_banner(
    data: BannerCreate,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(verify_admin_authorization),
):
    return await service.create_banner(db, data)


# -------------------------
# Admin: Create Banner (with file upload)
# -------------------------
@router.post("/admin/upload", response_model=BannerUploadResponse, status_code=201)
async def create_banner_with_upload(
    file: UploadFile = File(...),
    title: str = Form(...),
    alt_text: Optional[str] = Form(None),
    link_url: str = Form(...),
    platform: str = Form(...),
    start_at: str = Form(...),
    expire_at: str = Form(...),
    sort_order: int = Form(default=0),
    is_active: bool = Form(default=True),
    db: AsyncSession = Depends(get_session),
    _: str = Depends(verify_admin_authorization),
):
    from datetime import datetime

    try:
        start_dt = datetime.fromisoformat(start_at)
        expire_dt = datetime.fromisoformat(expire_at)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid date format. Use ISO 8601.")

    data = BannerCreate(
        title=title,
        image_url="",
        alt_text=alt_text,
        link_url=link_url,
        platform=platform,
        start_at=start_dt,
        expire_at=expire_dt,
        sort_order=sort_order,
        is_active=is_active,
    )
    return await service.create_banner_with_upload(db, data, file)


# -------------------------
# Admin: Update Banner (JSON)
# -------------------------
@router.put("/admin/{banner_id}", response_model=BannerResponse)
async def update_banner(
    banner_id: str,
    data: BannerUpdate,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(verify_admin_authorization),
):
    banner = await service.update_banner(db, banner_id, data)
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    return banner


# -------------------------
# Admin: Update Banner (with file upload)
# -------------------------
@router.put("/admin/{banner_id}/upload", response_model=BannerUploadResponse)
async def update_banner_with_upload(
    banner_id: str,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    alt_text: Optional[str] = Form(None),
    link_url: Optional[str] = Form(None),
    platform: Optional[str] = Form(None),
    start_at: Optional[str] = Form(None),
    expire_at: Optional[str] = Form(None),
    sort_order: Optional[int] = Form(None),
    is_active: Optional[bool] = Form(None),
    db: AsyncSession = Depends(get_session),
    _: str = Depends(verify_admin_authorization),
):
    from datetime import datetime

    update_fields = {}
    if title is not None:
        update_fields["title"] = title
    if alt_text is not None:
        update_fields["alt_text"] = alt_text
    if link_url is not None:
        update_fields["link_url"] = link_url
    if platform is not None:
        update_fields["platform"] = platform
    if start_at is not None:
        try:
            update_fields["start_at"] = datetime.fromisoformat(start_at)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid start_at date format.")
    if expire_at is not None:
        try:
            update_fields["expire_at"] = datetime.fromisoformat(expire_at)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid expire_at date format.")
    if sort_order is not None:
        update_fields["sort_order"] = sort_order
    if is_active is not None:
        update_fields["is_active"] = is_active

    data = BannerUpdate(**update_fields)
    banner = await service.update_banner_with_upload(db, banner_id, data, file)
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
    _: str = Depends(verify_admin_authorization),
):
    banner = await service.delete_banner(db, banner_id)
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    return {"message": "Banner deleted", "id": banner_id}
