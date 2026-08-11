import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import and_, func, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.auth import CurrentUser
from app.shared.enums import AnnouncementSection, AnnouncementType, AnnouncementVisibility

from .model import Announcement

logger = logging.getLogger(__name__)


def _arr_unrestricted_or_contains(column, value) -> or_:
    """DB-side helper for ARRAY(String) columns.

    semantics:
      - column is empty (cardinality == 0) → unrestricted, match
      - column contains value → match
      - otherwise → no match
    """
    return or_(
        func.coalesce(func.cardinality(column), 0) == 0,
        # any(None) is always NULL; OK to keep this defensive wrapper.
        # When the value is genuinely None we still rely on cardinality == 0
        # (since anyone with an empty target list must pass this dimension).
        column.any(value),
    )


class AnnouncementRepository:
    # ------------------------------------------------------------------
    # Generic CRUD
    # ------------------------------------------------------------------
    async def create(self, db: AsyncSession, announcement: Announcement) -> Announcement:
        db.add(announcement)
        await db.commit()
        await db.refresh(announcement)
        logger.info("Created announcement: %s", announcement.id)
        return announcement

    async def get_by_id(
        self,
        db: AsyncSession,
        announcement_id: str,
    ) -> Optional[Announcement]:
        result = await db.execute(
            select(Announcement).filter(Announcement.id == announcement_id)
        )
        return result.scalar_one_or_none()

    async def get_all_paginated(
        self,
        db: AsyncSession,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[Announcement], int]:
        offset = (page - 1) * size

        count_q = await db.execute(select(func.count(Announcement.id)))
        total = count_q.scalar() or 0

        result = await db.execute(
            select(Announcement)
            .order_by(
                Announcement.display_start_at.desc(),
                Announcement.created_at.desc(),
            )
            .offset(offset)
            .limit(size)
        )
        items = result.scalars().all()
        return list(items), total

    async def delete(self, db: AsyncSession, announcement: Announcement) -> None:
        announcement_id = announcement.id
        await db.delete(announcement)
        await db.commit()
        logger.info("Deleted announcement: %s", announcement_id)

    # ------------------------------------------------------------------
    # User-facing queries
    # ------------------------------------------------------------------
    async def get_latest_public(
        self,
        db: AsyncSession,
        section: AnnouncementSection,
        limit: int = 5,
    ) -> List[Announcement]:
        now = datetime.now(timezone.utc)

        result = await db.execute(
            select(Announcement)
            .filter(
                Announcement.is_active.is_(True),
                Announcement.visibility == AnnouncementVisibility.PUBLIC,
                Announcement.sections.any(section.value),
                Announcement.display_start_at <= now,
                Announcement.display_expire_at >= now,
            )
            .order_by(
                Announcement.display_start_at.desc(),
                Announcement.created_at.desc(),
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_public_history(
        self,
        db: AsyncSession,
        section: AnnouncementSection,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[Announcement], int]:
        now = datetime.now(timezone.utc)
        base_filter = and_(
            Announcement.is_active.is_(True),
            Announcement.visibility == AnnouncementVisibility.PUBLIC,
            Announcement.sections.any(section.value),
            # History intentionally allows expired items, but not future ones.
            Announcement.display_start_at <= now,
        )
        return await self._paginate(db, base_filter, page, limit)

    async def get_private_history(
        self,
        db: AsyncSession,
        section: AnnouncementSection,
        user: CurrentUser,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[Announcement], int]:
        now = datetime.now(timezone.utc)
        base_filter = and_(
            Announcement.is_active.is_(True),
            Announcement.visibility == AnnouncementVisibility.PRIVATE,
            Announcement.sections.any(section.value),
            Announcement.display_start_at <= now,
            self._targeting_clause(user),
        )
        return await self._paginate(db, base_filter, page, limit)

    # ------------------------------------------------------------------
    # Admin search — filter chain built from the AdminAnnouncementListQuery
    # ------------------------------------------------------------------
    async def search(
        self,
        db: AsyncSession,
        *,
        type: Optional[AnnouncementType] = None,
        section: Optional[AnnouncementSection] = None,
        visibility: Optional[AnnouncementVisibility] = None,
        is_active: Optional[bool] = None,
        subscription_type: Optional[str] = None,
        data_tier: Optional[str] = None,
        live_tread_access: Optional[bool] = None,
        user_data_group: Optional[str] = None,
        device: Optional[str] = None,
        display_start_at: Optional[datetime] = None,
        display_expire_at: Optional[datetime] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[Announcement], int]:
        clauses = []

        if type is not None:
            clauses.append(Announcement.type == type)
        if section is not None:
            clauses.append(Announcement.sections.any(section.value))
        if visibility is not None:
            clauses.append(Announcement.visibility == visibility)
        if is_active is not None:
            clauses.append(Announcement.is_active.is_(is_active))
        if subscription_type:
            clauses.append(Announcement.subscription_types.any(subscription_type))
        if data_tier:
            clauses.append(Announcement.target_data_tiers.any(data_tier))
        if live_tread_access is not None:
            clauses.append(Announcement.target_live_tread_access.is_(live_tread_access))
        if user_data_group:
            clauses.append(Announcement.target_user_data_groups.any(user_data_group))
        if device:
            clauses.append(Announcement.target_devices.any(device))
        if display_start_at is not None:
            clauses.append(Announcement.display_start_at >= display_start_at)
        if display_expire_at is not None:
            clauses.append(Announcement.display_expire_at <= display_expire_at)

        where = and_(*clauses) if clauses else true()
        return await self._paginate(db, where, page, size)

    # ------------------------------------------------------------------
    # Targeting helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _targeting_clause(user: CurrentUser):
        """Private-history predicate. Every dimension AND'd. The four
        dimensions:
          - target_data_tiers (array, empty == unrestricted)
          - target_live_tread_access (boolean, NULL == unrestricted)
          - target_user_data_groups (array, empty == unrestricted)
          - target_devices (array, empty == unrestricted)
        """
        return and_(
            _arr_unrestricted_or_contains(
                Announcement.target_data_tiers, user.dataTier,
            ),
            # Triple-state boolean column: NULL = unrestricted.
            or_(
                Announcement.target_live_tread_access.is_(None),
                Announcement.target_live_tread_access.is_(user.liveTreadAccess),
            ),
            _arr_unrestricted_or_contains(
                Announcement.target_user_data_groups, user.userDataGroup,
            ),
            _arr_unrestricted_or_contains(
                Announcement.target_devices, user.device,
            ),
        )

    # ------------------------------------------------------------------
    # Pagination helper shared by /history and /admin
    # ------------------------------------------------------------------
    @staticmethod
    async def _paginate(
        db: AsyncSession,
        where_clause,
        page: int,
        limit: int,
    ) -> Tuple[List[Announcement], int]:
        offset = (page - 1) * limit

        count_q = await db.execute(
            select(func.count(Announcement.id)).filter(where_clause)
        )
        total = count_q.scalar() or 0

        result = await db.execute(
            select(Announcement)
            .filter(where_clause)
            .order_by(
                Announcement.display_start_at.desc(),
                Announcement.created_at.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        items = list(result.scalars().all())
        return items, total
