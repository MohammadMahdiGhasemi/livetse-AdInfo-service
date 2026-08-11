from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.modules.ads.schema import AdAssetUpdate, AdCampaignCreate
from app.modules.announcements.schema import AnnouncementCreate
from app.modules.banners.schema import BannerCreate
from app.shared.enums import AnnouncementSection, AnnouncementType, AnnouncementVisibility, BannerPlatform


NOW = datetime.now(timezone.utc)


def test_banner_rejects_invalid_time_range():
    with pytest.raises(ValidationError):
        BannerCreate(
            title="banner",
            image_url="https://example.test/banner.png",
            link_url="https://example.test",
            platform=BannerPlatform.landing,
            start_at=NOW,
            expire_at=NOW,
        )


def test_campaign_rejects_invalid_time_range():
    with pytest.raises(ValidationError):
        AdCampaignCreate(
            client_name="client",
            start_at=NOW,
            expire_at=NOW - timedelta(seconds=1),
        )


def test_announcement_normalizes_tiers():
    item = AnnouncementCreate(
        text="hello",
        sections=[AnnouncementSection.LANDING],
        visibility=AnnouncementVisibility.PRIVATE,
        target_data_tiers=[" gold ", "GOLD"],
        display_start_at=NOW,
        display_expire_at=NOW + timedelta(hours=1),
    )
    assert item.target_data_tiers == ["GOLD"]


def test_announcement_type_defaults_to_info_and_accepts_error():
    base = dict(
        text="hello",
        sections=[AnnouncementSection.LANDING],
        visibility=AnnouncementVisibility.PUBLIC,
        display_start_at=NOW,
        display_expire_at=NOW + timedelta(hours=1),
    )
    item = AnnouncementCreate(**base)
    assert item.type == AnnouncementType.info

    error_item = AnnouncementCreate(**base, type="error")
    assert error_item.type == AnnouncementType.error


def test_announcement_rejects_legacy_danger_type():
    with pytest.raises(ValidationError):
        AnnouncementCreate(
            text="hello",
            type="danger",
            sections=[AnnouncementSection.LANDING],
            visibility=AnnouncementVisibility.PUBLIC,
            display_start_at=NOW,
            display_expire_at=NOW + timedelta(hours=1),
        )


def test_ad_position_must_be_positive():
    with pytest.raises(ValidationError):
        AdAssetUpdate(position=0)
