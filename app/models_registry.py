"""Centralized model registry.

Importing every concrete model here guarantees ``Base.metadata`` knows
about every table before ``init_db()`` runs ``create_all``. Without this
file, models are only registered when their owning router is imported,
which means the lifespan event (which runs first) sees an empty
metadata and creates no tables at all.
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
