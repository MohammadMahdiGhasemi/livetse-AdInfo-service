from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.shared.enums import (
    ALLOWED_DATA_TIERS,
    AnnouncementSection,
    AnnouncementVisibility,
    normalize_data_tier,
)


def _normalize_tier_list(values: Optional[List[str]]) -> List[str]:
    """Normalize each tier in a list. Whitespace is stripped, casing is
    uppercased; duplicates are deduplicated (preserving order)."""
    if not values:
        return []
    seen: list[str] = []
    for raw in values:
        norm = normalize_data_tier(raw)
        if norm and norm not in seen:
            seen.append(norm)
    return seen


def _validate_tier_list(values: List[str]) -> List[str]:
    """Normalize AND reject any tier outside the three allowed enums
    (STANDARD / SILVER / GOLD)."""
    normalized = _normalize_tier_list(values)
    bad = [v for v in values if (v is not None and str(v).strip().upper() not in ALLOWED_DATA_TIERS)]
    if bad:
        raise ValueError(
            f"target_data_tiers contains invalid value(s): {bad}. "
            f"Allowed: {list(ALLOWED_DATA_TIERS)}."
        )
    return normalized


# ---------------------------------------------------------------------------
# Base / Create / Update
# ---------------------------------------------------------------------------
class AnnouncementBase(BaseModel):
    text: str = Field(..., min_length=1)
    link: Optional[str] = None
    button_text: Optional[str] = Field(None, max_length=100)
    image_url: Optional[str] = None

    sections: List[AnnouncementSection] = Field(..., min_length=1)
    visibility: AnnouncementVisibility
    subscription_types: List[str] = Field(default_factory=list)

    target_data_tiers: List[str] = Field(default_factory=list)
    target_live_tread_access: Optional[bool] = None
    target_user_data_groups: List[str] = Field(default_factory=list)
    target_devices: List[str] = Field(default_factory=list)

    display_start_at: datetime
    display_expire_at: datetime
    is_active: bool = True

    @field_validator("target_data_tiers")
    @classmethod
    def _check_tiers(cls, v: List[str]) -> List[str]:
        return _validate_tier_list(v)

    @field_validator("target_live_tread_access", mode="before")
    @classmethod
    def _coerce_lta(cls, v):
        """Defensive coercion if a legacy client sends 'True'/'False' as a string."""
        if v is None or isinstance(v, bool):
            return v
        if isinstance(v, str):
            s = v.strip().lower()
            if s in {"true", "1", "yes"}:
                return True
            if s in {"false", "0", "no"}:
                return False
        raise ValueError("target_live_tread_access must be true, false, or null")

    @model_validator(mode="after")
    def _validate_dates(self) -> "AnnouncementBase":
        if self.display_expire_at <= self.display_start_at:
            raise ValueError("display_expire_at must be after display_start_at")
        return self


class AnnouncementCreate(AnnouncementBase):
    """Body schema for POST /announcements/admin and POST /announcements/admin/upload."""


class AnnouncementUpdate(BaseModel):
    """Body schema for PUT /announcements/admin and PUT /announcements/admin/{id}/upload.
    Every field is optional — only provided fields are updated."""

    text: Optional[str] = Field(None, min_length=1)
    link: Optional[str] = None
    button_text: Optional[str] = Field(None, max_length=100)
    image_url: Optional[str] = None

    sections: Optional[List[AnnouncementSection]] = None
    visibility: Optional[AnnouncementVisibility] = None
    subscription_types: Optional[List[str]] = None

    target_data_tiers: Optional[List[str]] = None
    target_live_tread_access: Optional[bool] = None
    target_user_data_groups: Optional[List[str]] = None
    target_devices: Optional[List[str]] = None

    display_start_at: Optional[datetime] = None
    display_expire_at: Optional[datetime] = None
    is_active: Optional[bool] = None

    @field_validator("target_data_tiers")
    @classmethod
    def _check_tiers(cls, v):
        if v is None:
            return v
        return _validate_tier_list(v)

    @field_validator("target_live_tread_access", mode="before")
    @classmethod
    def _coerce_lta(cls, v):
        if v is None or isinstance(v, bool):
            return v
        if isinstance(v, str):
            s = v.strip().lower()
            if s in {"true", "1", "yes"}:
                return True
            if s in {"false", "0", "no"}:
                return False
        raise ValueError("target_live_tread_access must be true, false, or null")


# ---------------------------------------------------------------------------
# Query schemas
# ---------------------------------------------------------------------------
class AnnouncementLatestQuery(BaseModel):
    section: AnnouncementSection
    limit: int = Field(default=5, ge=1, le=50)


class AnnouncementHistoryQuery(BaseModel):
    section: AnnouncementSection
    visibility: Optional[AnnouncementVisibility] = None
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)


class AdminAnnouncementListQuery(BaseModel):
    section: Optional[AnnouncementSection] = None
    visibility: Optional[AnnouncementVisibility] = None
    is_active: Optional[bool] = None
    subscription_type: Optional[str] = None
    data_tier: Optional[str] = None
    live_tread_access: Optional[bool] = None
    user_data_group: Optional[str] = None
    device: Optional[str] = None
    display_start_at: Optional[datetime] = None
    display_expire_at: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)

    @field_validator("data_tier", mode="before")
    @classmethod
    def _norm_tier(cls, v):
        return normalize_data_tier(v) if v is not None else v


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------
class AnnouncementResponse(BaseModel):
    """Public-facing response — never leaks targeting rules or is_active."""

    id: UUID
    text: str
    link: Optional[str] = None
    button_text: Optional[str] = None
    image_url: Optional[str] = None

    sections: List[AnnouncementSection]
    visibility: AnnouncementVisibility
    subscription_types: List[str]

    display_start_at: datetime
    display_expire_at: datetime

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AdminAnnouncementResponse(AnnouncementResponse):
    """Admin-facing response — includes targeting arrays and is_active."""

    target_data_tiers: List[str] = Field(default_factory=list)
    target_live_tread_access: Optional[bool] = None
    target_user_data_groups: List[str] = Field(default_factory=list)
    target_devices: List[str] = Field(default_factory=list)

    is_active: bool = True


class PaginatedAnnouncementResponse(BaseModel):
    items: List[AnnouncementResponse]
    total: int
    page: int
    size: int
    pages: int
