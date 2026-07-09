from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID

from app.shared.enums import BannerPlatform


class BannerBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    # The upload flow fills image_url from upload service output AFTER the
    # file is posted; allow empty on create so the upload endpoint can pass
    # through model validation before it knows the final URL.
    image_url: str = Field(default="", min_length=0)
    alt_text: Optional[str] = Field(None, max_length=255)
    link_url: str = Field(..., min_length=1)

    platform: BannerPlatform
    start_at: datetime
    expire_at: datetime

    sort_order: int = Field(default=0, ge=0)
    is_active: bool = True


class BannerCreate(BannerBase):
    pass


class BannerUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    # Empty strings may arrive on update when the client only wants to
    # change other fields and not touch the image — the upload flow will
    # overwrite image_url afterwards if a new file is present.
    image_url: Optional[str] = Field(None, min_length=0)
    alt_text: Optional[str] = Field(None, max_length=255)
    link_url: Optional[str] = Field(None, min_length=1)

    platform: Optional[BannerPlatform] = None
    start_at: Optional[datetime] = None
    expire_at: Optional[datetime] = None

    sort_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class BannerResponse(BannerBase):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class BannerUploadResponse(BaseModel):
    id: UUID
    title: str
    image_url: str
    image_name: Optional[str] = None
    image_folder: Optional[str] = None
    image_size: Optional[int] = None
    image_type: Optional[str] = None
    link_url: str
    platform: BannerPlatform
    start_at: datetime
    expire_at: datetime
    sort_order: int
    is_active: bool
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


class PaginatedBannerResponse(BaseModel):
    items: list[BannerResponse]
    total: int
    page: int
    size: int
    pages: int
