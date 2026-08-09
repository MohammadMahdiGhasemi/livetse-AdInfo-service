from datetime import date, datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.shared.enums import AdPlatform


# ---------------------------------------------------------------------------
# Campaign schemas
# ---------------------------------------------------------------------------
class AdCampaignBase(BaseModel):
    client_name: str = Field(..., min_length=1, max_length=255)
    start_at: datetime
    expire_at: datetime
    is_active: bool = True

    @model_validator(mode="after")
    def _validate_dates(self) -> "AdCampaignBase":
        if self.expire_at <= self.start_at:
            raise ValueError("expire_at must be after start_at")
        return self


class AdCampaignCreate(AdCampaignBase):
    pass


class AdCampaignUpdate(BaseModel):
    client_name: Optional[str] = Field(None, min_length=1, max_length=255)
    start_at: Optional[datetime] = None
    expire_at: Optional[datetime] = None
    is_active: Optional[bool] = None


class AdCampaignResponse(AdCampaignBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PaginatedAdCampaignResponse(BaseModel):
    items: List[AdCampaignResponse]
    total: int
    page: int
    size: int
    pages: int


# ---------------------------------------------------------------------------
# Asset schemas
# ---------------------------------------------------------------------------
class AdAssetResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    platform: str
    title: Optional[str] = None
    image_url: str
    link_url: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PaginatedAdAssetResponse(BaseModel):
    items: List[AdAssetResponse]
    total: int
    page: int
    size: int
    pages: int


# ---------------------------------------------------------------------------
# Stats schemas
# ---------------------------------------------------------------------------
class AdStatsRecord(BaseModel):
    id: UUID
    asset_id: UUID
    views_count: int
    clicks_count: int
    date: date

    model_config = {"from_attributes": True}


class AdStatsBulkItem(BaseModel):
    asset_id: UUID
    date: date
    views_count: int = Field(default=0, ge=0)
    clicks_count: int = Field(default=0, ge=0)


class AdStatsBulkRequest(BaseModel):
    stats: List[AdStatsBulkItem]


class AdStatsResponse(BaseModel):
    items: List[AdStatsRecord]
    total: int
    page: int
    size: int
    pages: int
