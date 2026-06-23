from sqlalchemy import Column, String, DateTime, Boolean, Integer, Date, ForeignKey, UniqueConstraint,Text
from sqlalchemy.dialects.postgresql import UUID
from shared.base_model import Base, TimestampMixin, generate_uuid


class AdCampaign(Base, TimestampMixin):
    __tablename__ = "ad_campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)

    client_name = Column(String(255))

    start_at = Column(DateTime(timezone=True))
    expire_at = Column(DateTime(timezone=True))

    is_active = Column(Boolean, default=True)






class AdAsset(Base, TimestampMixin):
    __tablename__ = "ad_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)

    campaign_id = Column(UUID(as_uuid=True), ForeignKey("ad_campaigns.id", ondelete="CASCADE"))

    platform = Column(String(50))

    title = Column(String(255), nullable=True)
    image_url = Column(Text)
    link_url = Column(Text)




class AdStats(Base):
    __tablename__ = "ad_stats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)

    asset_id = Column(UUID(as_uuid=True), ForeignKey("ad_assets.id", ondelete="CASCADE"))

    views_count = Column(Integer, default=0)
    clicks_count = Column(Integer, default=0)

    date = Column(Date)

    __table_args__ = (
        UniqueConstraint("asset_id", "date", name="uq_asset_date"),
    )