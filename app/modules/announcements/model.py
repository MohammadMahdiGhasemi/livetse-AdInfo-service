from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Index, String, Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID

from app.shared.base_model import Base, TimestampMixin, generate_uuid
from app.shared.enums import AnnouncementVisibility


class Announcement(Base, TimestampMixin):
    __tablename__ = "announcements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)

    text = Column(Text, nullable=False)
    link = Column(Text, nullable=True)
    button_text = Column(String(100), nullable=True)
    image_url = Column(Text, nullable=True)

    # Which UI sections this announcement is shown in.
    sections = Column(ARRAY(String), nullable=False, default=list)

    visibility = Column(
        Enum(AnnouncementVisibility, name="announcement_visibility"),
        nullable=False,
    )

    # Subscription types this announcement applies to; empty == all.
    subscription_types = Column(ARRAY(String), nullable=False, default=list)

    # Targeting fields — only consulted when visibility = PRIVATE.
    # Empty ARRAY == unrestricted on that dimension (per spec).
    target_data_tiers = Column(ARRAY(String), nullable=False, default=list)
    # Triple-state NULL = no restriction on live-trading access.
    target_live_tread_access = Column(Boolean, nullable=True, default=None)
    target_user_data_groups = Column(ARRAY(String), nullable=False, default=list)
    target_devices = Column(ARRAY(String), nullable=False, default=list)

    display_start_at = Column(DateTime(timezone=True), nullable=False)
    display_expire_at = Column(DateTime(timezone=True), nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)

    __table_args__ = (
        # B-tree indexes for the scalar filter columns used in admin / public
        Index("ix_announcements_visibility", "visibility"),
        Index("ix_announcements_is_active", "is_active"),
        Index("ix_announcements_display_start_at", "display_start_at"),
        Index("ix_announcements_display_expire_at", "display_expire_at"),
        Index("ix_announcements_created_at", "created_at"),
        Index(
            "ix_announcements_target_live_tread_access",
            "target_live_tread_access",
        ),
        # Composite for the latest-public query path
        Index(
            "ix_announcements_active_visibility_start",
            "is_active", "visibility", "display_start_at",
        ),
        # GIN indexes for ARRAY containment lookups
        Index("ix_announcements_sections_gin", "sections", postgresql_using="gin"),
        Index(
            "ix_announcements_subscription_types_gin",
            "subscription_types", postgresql_using="gin",
        ),
        Index(
            "ix_announcements_target_data_tiers_gin",
            "target_data_tiers", postgresql_using="gin",
        ),
        Index(
            "ix_announcements_target_user_data_groups_gin",
            "target_user_data_groups", postgresql_using="gin",
        ),
        Index(
            "ix_announcements_target_devices_gin",
            "target_devices", postgresql_using="gin",
        ),
    )
