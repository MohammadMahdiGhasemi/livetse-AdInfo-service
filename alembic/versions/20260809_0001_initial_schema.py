"""Baseline schema matching the pre-Alembic service.

Revision ID: 20260809_0001
Revises: None
Create Date: 2026-08-09

Existing databases that were previously created by SQLAlchemy create_all() can
be audited and stamped to this revision, then upgraded to head to apply the
production hardening migration.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260809_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

announcement_visibility = postgresql.ENUM(
    "PUBLIC", "PRIVATE", name="announcement_visibility", create_type=False
)


def upgrade() -> None:
    announcement_visibility.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "banners",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=False),
        sa.Column("image_name", sa.String(length=255), nullable=True),
        sa.Column("image_folder", sa.String(length=100), nullable=True),
        sa.Column("image_size", sa.Integer(), nullable=True),
        sa.Column("image_type", sa.String(length=100), nullable=True),
        sa.Column("alt_text", sa.String(length=255), nullable=True),
        sa.Column("link_url", sa.Text(), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expire_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_banner_active_time", "banners", ["is_active", "start_at", "expire_at"])

    op.create_table(
        "announcements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("link", sa.Text(), nullable=True),
        sa.Column("button_text", sa.String(length=100), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("sections", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("visibility", announcement_visibility, nullable=False),
        sa.Column("subscription_types", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("target_data_tiers", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("target_live_tread_access", sa.Boolean(), nullable=True),
        sa.Column("target_user_data_groups", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("target_devices", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("display_start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("display_expire_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_announcements_visibility", "announcements", ["visibility"])
    op.create_index("ix_announcements_is_active", "announcements", ["is_active"])
    op.create_index("ix_announcements_display_start_at", "announcements", ["display_start_at"])
    op.create_index("ix_announcements_display_expire_at", "announcements", ["display_expire_at"])
    op.create_index("ix_announcements_created_at", "announcements", ["created_at"])
    op.create_index("ix_announcements_target_live_tread_access", "announcements", ["target_live_tread_access"])
    op.create_index(
        "ix_announcements_active_visibility_start",
        "announcements",
        ["is_active", "visibility", "display_start_at"],
    )
    op.create_index("ix_announcements_sections_gin", "announcements", ["sections"], postgresql_using="gin")
    op.create_index("ix_announcements_subscription_types_gin", "announcements", ["subscription_types"], postgresql_using="gin")
    op.create_index("ix_announcements_target_data_tiers_gin", "announcements", ["target_data_tiers"], postgresql_using="gin")
    op.create_index("ix_announcements_target_user_data_groups_gin", "announcements", ["target_user_data_groups"], postgresql_using="gin")
    op.create_index("ix_announcements_target_devices_gin", "announcements", ["target_devices"], postgresql_using="gin")

    op.create_table(
        "ad_campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_name", sa.String(length=255), nullable=True),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expire_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "ad_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("platform", sa.String(length=50), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("link_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["ad_campaigns.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "ad_stats",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("views_count", sa.Integer(), nullable=True),
        sa.Column("clicks_count", sa.Integer(), nullable=True),
        sa.Column("date", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["asset_id"], ["ad_assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "date", name="uq_asset_date"),
    )


def downgrade() -> None:
    op.drop_table("ad_stats")
    op.drop_table("ad_assets")
    op.drop_table("ad_campaigns")

    op.drop_index("ix_announcements_target_devices_gin", table_name="announcements")
    op.drop_index("ix_announcements_target_user_data_groups_gin", table_name="announcements")
    op.drop_index("ix_announcements_target_data_tiers_gin", table_name="announcements")
    op.drop_index("ix_announcements_subscription_types_gin", table_name="announcements")
    op.drop_index("ix_announcements_sections_gin", table_name="announcements")
    op.drop_index("ix_announcements_active_visibility_start", table_name="announcements")
    op.drop_index("ix_announcements_target_live_tread_access", table_name="announcements")
    op.drop_index("ix_announcements_created_at", table_name="announcements")
    op.drop_index("ix_announcements_display_expire_at", table_name="announcements")
    op.drop_index("ix_announcements_display_start_at", table_name="announcements")
    op.drop_index("ix_announcements_is_active", table_name="announcements")
    op.drop_index("ix_announcements_visibility", table_name="announcements")
    op.drop_table("announcements")
    announcement_visibility.drop(op.get_bind(), checkfirst=True)

    op.drop_index("idx_banner_active_time", table_name="banners")
    op.drop_table("banners")
