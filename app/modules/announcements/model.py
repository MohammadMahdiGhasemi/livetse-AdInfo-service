from sqlalchemy import Column, String, Text, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from app.shared.base_model import Base, TimestampMixin, generate_uuid
from app.shared.enums import AnnouncementType, ScopeType


class Announcement(Base, TimestampMixin):
    __tablename__ = "announcements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)

    title = Column(String(255))
    content = Column(Text)

    button_text = Column(String(100), nullable=True)
    button_link = Column(Text, nullable=True)

    type = Column(Enum(AnnouncementType))
    target_platforms = Column(ARRAY(String))  # ['app', 'landing']

    scope = Column(Enum(ScopeType))

    start_at = Column(DateTime(timezone=True))
    expire_at = Column(DateTime(timezone=True))



class AnnouncementTarget(Base):
    __tablename__ = "announcement_targets"

    announcement_id = Column(
        UUID(as_uuid=True),
        ForeignKey("announcements.id", ondelete="CASCADE"),
        primary_key=True
    )

    group_id = Column(String(100), primary_key=True)