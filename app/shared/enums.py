import enum


class BannerPlatform(str, enum.Enum):
    landing = "landing"
    extension = "extension"


class AnnouncementType(str, enum.Enum):
    info = "info"
    warning = "warning"
    danger = "danger"
    success = "success"


class ScopeType(str, enum.Enum):
    public = "public"
    targeted = "targeted"


class AdPlatform(str, enum.Enum):
    extension = "extension"
    app = "app"
    landing = "landing"