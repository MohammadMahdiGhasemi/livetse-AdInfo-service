import logging
from datetime import datetime
from typing import Optional

from fastapi import (
    APIRouter, Depends, File, Form, Header, HTTPException,
    Query, UploadFile,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session

from .service import AnnouncementService
from .schema import (
    AnnouncementCreate,
    AnnouncementUpdate,
    AdminAnnouncementResponse,
    PaginatedAnnouncementResponse,
    _normalize_tier_list,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Announcements-Admin"])
service = AnnouncementService()


# ---------------------------------------------------------------------------
# Bearer-token admin authorization (mirrors banners/admin.py)
# ---------------------------------------------------------------------------
async def verify_admin_authorization(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    token = authorization.replace("Bearer ", "")
    if token != settings.ADMIN_PASSWORD:
        logger.warning("Invalid admin authorization attempt on announcements route")
        raise HTTPException(status_code=403, detail="Invalid authorization")
    return token


# ---------------------------------------------------------------------------
# GET /announcements/admin — admin list with filters (no role)
# ---------------------------------------------------------------------------
@router.get(
    "/admin",
    response_model=PaginatedAnnouncementResponse,
)
async def list_announcements(
    section: Optional[str] = Query(default=None),
    visibility: Optional[str] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    subscription_type: Optional[str] = Query(default=None),
    data_tier: Optional[str] = Query(default=None),
    live_tread_access: Optional[bool] = Query(default=None),
    user_data_group: Optional[str] = Query(default=None),
    device: Optional[str] = Query(default=None),
    display_start_at: Optional[datetime] = Query(default=None),
    display_expire_at: Optional[datetime] = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
    _: str = Depends(verify_admin_authorization),
):
    return await service.get_admin_list(
        db,
        section=section,
        visibility=visibility,
        is_active=is_active,
        subscription_type=subscription_type,
        data_tier=data_tier,
        live_tread_access=live_tread_access,
        user_data_group=user_data_group,
        device=device,
        display_start_at=display_start_at,
        display_expire_at=display_expire_at,
        page=page,
        size=size,
    )


# ---------------------------------------------------------------------------
# GET /announcements/admin/{id}
# ---------------------------------------------------------------------------
@router.get(
    "/admin/{announcement_id}",
    response_model=AdminAnnouncementResponse,
)
async def get_announcement(
    announcement_id: str,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(verify_admin_authorization),
):
    announcement = await service.get_announcement(db, announcement_id)
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return announcement


# ---------------------------------------------------------------------------
# POST /announcements/admin — JSON create
# ---------------------------------------------------------------------------
@router.post(
    "/admin",
    response_model=AdminAnnouncementResponse,
    status_code=201,
)
async def create_announcement(
    data: AnnouncementCreate,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(verify_admin_authorization),
):
    return await service.create_announcement(db, data)


# ---------------------------------------------------------------------------
# POST /announcements/admin/upload — multipart create with image upload
# ---------------------------------------------------------------------------
def _split_csv(raw: Optional[str]) -> list[str]:
    return [s.strip() for s in (raw or "").split(",") if s.strip()]


def _coerce_lta(value: Optional[str]) -> Optional[bool]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        s = value.strip().lower()
        if s in {"true", "1", "yes"}:
            return True
        if s in {"false", "0", "no"}:
            return False
    return None


@router.post(
    "/admin/upload",
    response_model=AdminAnnouncementResponse,
    status_code=201,
)
async def create_announcement_with_upload(
    file: UploadFile = File(...),
    text: str = Form(..., min_length=1),
    sections: str = Form(..., description="Comma-separated, e.g. LANDING,DASHBOARD"),
    visibility: str = Form(...),
    display_start_at: str = Form(...),
    display_expire_at: str = Form(...),
    link: Optional[str] = Form(None),
    button_text: Optional[str] = Form(None),
    image_url: Optional[str] = Form(None),
    subscription_types: Optional[str] = Form(default=""),
    target_data_tiers: Optional[str] = Form(default=""),
    target_live_tread_access: Optional[str] = Form(default=None),
    target_user_data_groups: Optional[str] = Form(default=""),
    target_devices: Optional[str] = Form(default=""),
    is_active: bool = Form(default=True),
    db: AsyncSession = Depends(get_session),
    _: str = Depends(verify_admin_authorization),
):
    from app.shared.enums import AnnouncementSection, AnnouncementVisibility
    from pydantic import ValidationError

    try:
        sections_list = [
            AnnouncementSection(s.strip())
            for s in sections.split(",") if s.strip()
        ]
        visibility_enum = AnnouncementVisibility(visibility)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Invalid parameter value: {e}")

    if not sections_list:
        raise HTTPException(
            status_code=422,
            detail="sections is required and must be non-empty",
        )

    try:
        start_dt = datetime.fromisoformat(display_start_at)
        expire_dt = datetime.fromisoformat(display_expire_at)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid date format. Use ISO 8601.")

    try:
        normalized_tiers = _normalize_tier_list(_split_csv(target_data_tiers))
        data = AnnouncementCreate(
            text=text,
            link=link,
            button_text=button_text,
            image_url=image_url,
            sections=sections_list,
            visibility=visibility_enum,
            subscription_types=_split_csv(subscription_types),
            target_data_tiers=normalized_tiers,
            target_live_tread_access=_coerce_lta(target_live_tread_access),
            target_user_data_groups=_split_csv(target_user_data_groups),
            target_devices=_split_csv(target_devices),
            display_start_at=start_dt,
            display_expire_at=expire_dt,
            is_active=is_active,
        )
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

    return await service.create_announcement_with_upload(db, data, file)


# ---------------------------------------------------------------------------
# PUT /announcements/admin/{id} — JSON update
# ---------------------------------------------------------------------------
@router.put(
    "/admin/{announcement_id}",
    response_model=AdminAnnouncementResponse,
)
async def update_announcement(
    announcement_id: str,
    data: AnnouncementUpdate,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(verify_admin_authorization),
):
    announcement = await service.update_announcement(db, announcement_id, data)
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return announcement


# ---------------------------------------------------------------------------
# PUT /announcements/admin/{id}/upload — multipart update with file
# ---------------------------------------------------------------------------
@router.put(
    "/admin/{announcement_id}/upload",
    response_model=AdminAnnouncementResponse,
)
async def update_announcement_with_upload(
    announcement_id: str,
    file: UploadFile = File(...),
    text: Optional[str] = Form(default=None),
    sections: Optional[str] = Form(default=None),
    visibility: Optional[str] = Form(default=None),
    display_start_at: Optional[str] = Form(default=None),
    display_expire_at: Optional[str] = Form(default=None),
    link: Optional[str] = Form(default=None),
    button_text: Optional[str] = Form(default=None),
    image_url: Optional[str] = Form(default=None),
    subscription_types: Optional[str] = Form(default=None),
    target_data_tiers: Optional[str] = Form(default=None),
    target_live_tread_access: Optional[str] = Form(default=None),
    target_user_data_groups: Optional[str] = Form(default=None),
    target_devices: Optional[str] = Form(default=None),
    is_active: Optional[bool] = Form(default=None),
    db: AsyncSession = Depends(get_session),
    _: str = Depends(verify_admin_authorization),
):
    from app.shared.enums import AnnouncementSection, AnnouncementVisibility
    from pydantic import ValidationError

    payload: dict = {}

    if text is not None:
        payload["text"] = text
    if link is not None:
        payload["link"] = link
    if button_text is not None:
        payload["button_text"] = button_text
    if image_url is not None:
        payload["image_url"] = image_url
    if is_active is not None:
        payload["is_active"] = is_active
    if sections is not None:
        try:
            payload["sections"] = [
                AnnouncementSection(s.strip())
                for s in sections.split(",") if s.strip()
            ]
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
    if visibility is not None:
        try:
            payload["visibility"] = AnnouncementVisibility(visibility)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

    if subscription_types is not None:
        payload["subscription_types"] = _split_csv(subscription_types)
    if target_data_tiers is not None:
        payload["target_data_tiers"] = _normalize_tier_list(_split_csv(target_data_tiers))
    if target_user_data_groups is not None:
        payload["target_user_data_groups"] = _split_csv(target_user_data_groups)
    if target_devices is not None:
        payload["target_devices"] = _split_csv(target_devices)
    if target_live_tread_access is not None:
        payload["target_live_tread_access"] = _coerce_lta(target_live_tread_access)

    if display_start_at is not None:
        try:
            payload["display_start_at"] = datetime.fromisoformat(display_start_at)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid display_start_at date format.")
    if display_expire_at is not None:
        try:
            payload["display_expire_at"] = datetime.fromisoformat(display_expire_at)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid display_expire_at date format.")

    try:
        data = AnnouncementUpdate(**payload)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

    announcement = await service.update_announcement_with_upload(
        db, announcement_id, data, file
    )
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return announcement


# ---------------------------------------------------------------------------
# DELETE /announcements/admin/{id}
# ---------------------------------------------------------------------------
@router.delete("/admin/{announcement_id}")
async def delete_announcement(
    announcement_id: str,
    db: AsyncSession = Depends(get_session),
    _: str = Depends(verify_admin_authorization),
):
    ok = await service.delete_announcement(db, announcement_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return {"message": "Announcement deleted", "id": announcement_id}
