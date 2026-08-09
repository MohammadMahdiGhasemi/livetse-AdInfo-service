"""Central model registry.

Importing every concrete model guarantees ``Base.metadata`` contains the full
schema for Alembic autogeneration/comparison and optional local development
schema creation.
"""
from app.modules.announcements.model import Announcement  # noqa: F401
from app.modules.banners.model import Banner  # noqa: F401
from app.modules.ads.model import AdCampaign, AdAsset, AdStats  # noqa: F401

__all__ = [
    "Announcement",
    "Banner",
    "AdCampaign",
    "AdAsset",
    "AdStats",
]
