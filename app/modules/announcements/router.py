import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.shared.auth import get_current_user, CurrentUser
from app.shared.enums import AnnouncementSection, AnnouncementVisibility

from .service import AnnouncementService
from .schema import (
    AnnouncementResponse,
    PaginatedAnnouncementResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Announcements"])
service = AnnouncementService()


# ---------------------------------------------------------------------------
# GET /announcements/latest
#   Public — no auth required.
#   Active + PUBLIC + section matches + within time window, newest first.
# ---------------------------------------------------------------------------
@router.get(
    "/latest",
    response_model=list[AnnouncementResponse],
)
async def get_latest_announcements(
    section: AnnouncementSection = Query(...),
    limit: int = Query(default=5, ge=1, le=50),
    db: AsyncSession = Depends(get_session),
):
    return await service.get_latest_public(db, section, limit)


# ---------------------------------------------------------------------------
# GET /announcements/history
#   Public visibility: optional auth, returns PUBLIC announcements.
#   Private visibility: requires Authorization header (JWT).
# ---------------------------------------------------------------------------
@router.get(
    "/history",
    response_model=PaginatedAnnouncementResponse,
)
async def get_announcement_history(
    section: AnnouncementSection = Query(...),
    visibility: Optional[AnnouncementVisibility] = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
    current_user: Optional[CurrentUser] = Depends(get_current_user),
):
    # Default visibility filter = PUBLIC; users must opt-in to PRIVATE.
    effective_visibility = visibility or AnnouncementVisibility.PUBLIC

    if effective_visibility == AnnouncementVisibility.PRIVATE:
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization required for private announcements",
            )
        return await service.get_private_history(
            db, section, current_user, page, limit
        )

    return await service.get_public_history(db, section, page, limit)
