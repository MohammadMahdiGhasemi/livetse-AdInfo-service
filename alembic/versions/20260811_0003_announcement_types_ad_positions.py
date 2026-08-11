"""Add announcement types and ordered ad positions.

Revision ID: 20260811_0003
Revises: 20260809_0002
Create Date: 2026-08-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260811_0003"
down_revision: Union[str, None] = "20260809_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

announcement_type = postgresql.ENUM(
    "info", "warning", "error", "success",
    name="announcement_type",
    create_type=False,
)


def upgrade() -> None:
    announcement_type.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "announcements",
        sa.Column(
            "type",
            announcement_type,
            nullable=False,
            server_default=sa.text("'info'::announcement_type"),
        ),
    )
    op.create_index("ix_announcements_type", "announcements", ["type"])

    # Existing assets are given deterministic positions per platform so an
    # upgrade never invents duplicate live positions from legacy data.
    op.add_column("ad_assets", sa.Column("position", sa.Integer(), nullable=True))
    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY platform
                       ORDER BY created_at ASC NULLS LAST, id ASC
                   ) AS new_position
            FROM ad_assets
        )
        UPDATE ad_assets AS a
        SET position = ranked.new_position
        FROM ranked
        WHERE a.id = ranked.id
        """
    )
    op.alter_column("ad_assets", "position", existing_type=sa.Integer(), nullable=False)
    op.create_check_constraint(
        "ck_ad_asset_position_positive", "ad_assets", "position >= 1"
    )
    op.create_unique_constraint(
        "uq_ad_asset_campaign_platform_position",
        "ad_assets",
        ["campaign_id", "platform", "position"],
    )
    op.create_index(
        "ix_ad_assets_platform_position", "ad_assets", ["platform", "position"]
    )


def downgrade() -> None:
    op.drop_index("ix_ad_assets_platform_position", table_name="ad_assets")
    op.drop_constraint(
        "uq_ad_asset_campaign_platform_position", "ad_assets", type_="unique"
    )
    op.drop_constraint("ck_ad_asset_position_positive", "ad_assets", type_="check")
    op.drop_column("ad_assets", "position")

    op.drop_index("ix_announcements_type", table_name="announcements")
    op.drop_column("announcements", "type")
    announcement_type.drop(op.get_bind(), checkfirst=True)
