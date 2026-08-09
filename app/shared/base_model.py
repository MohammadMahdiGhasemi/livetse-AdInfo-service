from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, DateTime
from datetime import datetime, timezone
import uuid
from sqlalchemy.dialects.postgresql import UUID


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """created_at / updated_at columns stored as TIMESTAMP WITH TIME ZONE.

    Defaults use ``datetime.now(timezone.utc)`` so the values are timezone-
    aware at write time, matching the column type. ``datetime.utcnow()`` is
    deprecated in Python 3.12+ and returns a naive datetime which can
    confuse comparisons against tz-aware values read back from the DB.
    """

    def _utcnow(ctx):
        # SQLAlchemy always passes an ExecutionContext-like object here;
        # the parameter just has to be named so the wrapper can call us.
        return datetime.now(timezone.utc)

    created_at = Column(
        DateTime(timezone=True),
        default=_utcnow,
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        nullable=False,
    )


def generate_uuid():
    """Return a native UUID4 object for PostgreSQL UUID(as_uuid=True) columns."""
    return uuid.uuid4()
