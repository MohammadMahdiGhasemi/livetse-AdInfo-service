import enum


class BannerPlatform(str, enum.Enum):
    landing = "landing"
    extension = "extension"


class AnnouncementType(str, enum.Enum):
    info = "info"
    warning = "warning"
    error = "error"
    success = "success"


class ScopeType(str, enum.Enum):
    public = "public"
    targeted = "targeted"


class AdPlatform(str, enum.Enum):
    extension = "extension"
    app = "app"
    landing = "landing"


class AnnouncementSection(str, enum.Enum):
    LANDING = "LANDING"
    DASHBOARD = "DASHBOARD"
    EXTENSION = "EXTENSION"
    MOBILE = "MOBILE"


class AnnouncementVisibility(str, enum.Enum):
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"


class DataTier(str, enum.Enum):
    STANDARD = "STANDARD"
    SILVER = "SILVER"
    GOLD = "GOLD"


# Accepted canonical tier values (uppercase).
ALLOWED_DATA_TIERS: tuple[str, ...] = ("STANDARD", "SILVER", "GOLD")


def normalize_data_tier(value: str | None) -> str | None:
    """Uppercase + strip incoming tier values. Returns None when the
    input is empty/None so callers cannot accidentally persist blanks."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    upper = s.upper()
    if upper not in ALLOWED_DATA_TIERS:
        # Fall back to whatever the caller sent verbatim — validation in
        # the Pydantic schema is what actually rejects bogus values.
        return upper
    return upper
