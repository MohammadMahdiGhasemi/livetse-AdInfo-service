from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from app.shared.base_model import Base, TimestampMixin, generate_uuid
from app.shared.enums import BannerPlatform


class Banner(Base, TimestampMixin):
    __tablename__ = "banners"
    __table_args__ = (
        Index("idx_banner_active_time", "is_active", "start_at", "expire_at"),
        CheckConstraint("expire_at > start_at", name="ck_banner_time_range"),
        CheckConstraint("sort_order >= 0", name="ck_banner_sort_order_nonnegative"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)

    title = Column(String(255), nullable=False)
    image_url = Column(Text, nullable=False)
    image_name = Column(String(255), nullable=True)
    image_folder = Column(String(100), nullable=True)
    image_size = Column(Integer, nullable=True)
    image_type = Column(String(100), nullable=True)
    alt_text = Column(String(255), nullable=True)
    link_url = Column(Text, nullable=False)

    platform = Column(String(50), nullable=False)
    start_at = Column(DateTime(timezone=True), nullable=False)
    expire_at = Column(DateTime(timezone=True), nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
