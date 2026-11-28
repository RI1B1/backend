from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# PostgreSQL uses BIGINT; SQLite tests need INTEGER for autoincrement primary keys.
BIGINT_ID = BigInteger().with_variant(Integer, "sqlite")


class TimestampMixin:
    """Semua waktu disimpan UTC."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
