from sqlalchemy import Column, String, DateTime, Boolean, Integer, Date, ForeignKey, UniqueConstraint, Text, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.shared.base_model import Base, TimestampMixin, generate_uuid


class AdCampaign(Base, TimestampMixin):
    __tablename__ = "ad_campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)

    client_name = Column(String(255), nullable=False)

    start_at = Column(DateTime(timezone=True), nullable=False)
    expire_at = Column(DateTime(timezone=True), nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)

    assets = relationship("AdAsset", back_populates="campaign", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("expire_at > start_at", name="ck_ad_campaign_time_range"),
        Index("ix_ad_campaign_active_time", "is_active", "start_at", "expire_at"),
    )






class AdAsset(Base, TimestampMixin):
    __tablename__ = "ad_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)

    campaign_id = Column(UUID(as_uuid=True), ForeignKey("ad_campaigns.id", ondelete="CASCADE"), nullable=False, index=True)

    platform = Column(String(50), nullable=False, index=True)

    title = Column(String(255), nullable=True)
    image_url = Column(Text, nullable=False)
    link_url = Column(Text, nullable=False)

    campaign = relationship("AdCampaign", back_populates="assets")




class AdStats(Base):
    __tablename__ = "ad_stats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)

    asset_id = Column(UUID(as_uuid=True), ForeignKey("ad_assets.id", ondelete="CASCADE"), nullable=False, index=True)

    views_count = Column(Integer, default=0, nullable=False)
    clicks_count = Column(Integer, default=0, nullable=False)

    date = Column(Date, nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("asset_id", "date", name="uq_asset_date"),
        CheckConstraint("views_count >= 0", name="ck_ad_stats_views_nonnegative"),
        CheckConstraint("clicks_count >= 0", name="ck_ad_stats_clicks_nonnegative"),
    )