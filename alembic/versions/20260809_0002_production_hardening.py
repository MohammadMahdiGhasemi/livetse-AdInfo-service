"""Add production data-integrity constraints and query indexes.

Revision ID: 20260809_0002
Revises: 20260809_0001
Create Date: 2026-08-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260809_0002"
down_revision: Union[str, None] = "20260809_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # These constraints intentionally validate existing data. If an existing
    # database contains NULL/invalid legacy rows, fix those rows explicitly
    # before re-running this migration rather than silently guessing values.
    op.create_check_constraint(
        "ck_banner_time_range", "banners", "expire_at > start_at"
    )
    op.create_check_constraint(
        "ck_banner_sort_order_nonnegative", "banners", "sort_order >= 0"
    )
    op.create_check_constraint(
        "ck_announcement_time_range",
        "announcements",
        "display_expire_at > display_start_at",
    )

    op.alter_column("ad_campaigns", "client_name", existing_type=sa.String(255), nullable=False)
    op.alter_column("ad_campaigns", "start_at", existing_type=sa.DateTime(timezone=True), nullable=False)
    op.alter_column("ad_campaigns", "expire_at", existing_type=sa.DateTime(timezone=True), nullable=False)
    op.alter_column("ad_campaigns", "is_active", existing_type=sa.Boolean(), nullable=False)
    op.create_check_constraint(
        "ck_ad_campaign_time_range", "ad_campaigns", "expire_at > start_at"
    )
    op.create_index(
        "ix_ad_campaign_active_time",
        "ad_campaigns",
        ["is_active", "start_at", "expire_at"],
    )

    op.alter_column("ad_assets", "campaign_id", existing_type=sa.Uuid(), nullable=False)
    op.alter_column("ad_assets", "platform", existing_type=sa.String(50), nullable=False)
    op.alter_column("ad_assets", "image_url", existing_type=sa.Text(), nullable=False)
    op.alter_column("ad_assets", "link_url", existing_type=sa.Text(), nullable=False)
    op.create_index("ix_ad_assets_campaign_id", "ad_assets", ["campaign_id"])
    op.create_index("ix_ad_assets_platform", "ad_assets", ["platform"])

    op.alter_column("ad_stats", "asset_id", existing_type=sa.Uuid(), nullable=False)
    op.alter_column("ad_stats", "views_count", existing_type=sa.Integer(), nullable=False)
    op.alter_column("ad_stats", "clicks_count", existing_type=sa.Integer(), nullable=False)
    op.alter_column("ad_stats", "date", existing_type=sa.Date(), nullable=False)
    op.create_check_constraint(
        "ck_ad_stats_views_nonnegative", "ad_stats", "views_count >= 0"
    )
    op.create_check_constraint(
        "ck_ad_stats_clicks_nonnegative", "ad_stats", "clicks_count >= 0"
    )
    op.create_index("ix_ad_stats_asset_id", "ad_stats", ["asset_id"])
    op.create_index("ix_ad_stats_date", "ad_stats", ["date"])


def downgrade() -> None:
    op.drop_index("ix_ad_stats_date", table_name="ad_stats")
    op.drop_index("ix_ad_stats_asset_id", table_name="ad_stats")
    op.drop_constraint("ck_ad_stats_clicks_nonnegative", "ad_stats", type_="check")
    op.drop_constraint("ck_ad_stats_views_nonnegative", "ad_stats", type_="check")
    op.alter_column("ad_stats", "date", existing_type=sa.Date(), nullable=True)
    op.alter_column("ad_stats", "clicks_count", existing_type=sa.Integer(), nullable=True)
    op.alter_column("ad_stats", "views_count", existing_type=sa.Integer(), nullable=True)
    op.alter_column("ad_stats", "asset_id", existing_type=sa.Uuid(), nullable=True)

    op.drop_index("ix_ad_assets_platform", table_name="ad_assets")
    op.drop_index("ix_ad_assets_campaign_id", table_name="ad_assets")
    op.alter_column("ad_assets", "link_url", existing_type=sa.Text(), nullable=True)
    op.alter_column("ad_assets", "image_url", existing_type=sa.Text(), nullable=True)
    op.alter_column("ad_assets", "platform", existing_type=sa.String(50), nullable=True)
    op.alter_column("ad_assets", "campaign_id", existing_type=sa.Uuid(), nullable=True)

    op.drop_index("ix_ad_campaign_active_time", table_name="ad_campaigns")
    op.drop_constraint("ck_ad_campaign_time_range", "ad_campaigns", type_="check")
    op.alter_column("ad_campaigns", "is_active", existing_type=sa.Boolean(), nullable=True)
    op.alter_column("ad_campaigns", "expire_at", existing_type=sa.DateTime(timezone=True), nullable=True)
    op.alter_column("ad_campaigns", "start_at", existing_type=sa.DateTime(timezone=True), nullable=True)
    op.alter_column("ad_campaigns", "client_name", existing_type=sa.String(255), nullable=True)

    op.drop_constraint("ck_announcement_time_range", "announcements", type_="check")
    op.drop_constraint("ck_banner_sort_order_nonnegative", "banners", type_="check")
    op.drop_constraint("ck_banner_time_range", "banners", type_="check")
