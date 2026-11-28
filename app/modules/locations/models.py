"""Model SQLAlchemy modul locations."""

from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Identity,
    Index,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BIGINT_ID, Base, TimestampMixin


class Location(Base, TimestampMixin):
    __tablename__ = "locations"

    __table_args__ = (
        CheckConstraint(
            "latitude IS NULL OR latitude BETWEEN -90 AND 90",
            name="chk_locations_lat",
        ),
        CheckConstraint(
            "longitude IS NULL OR longitude BETWEEN -180 AND 180",
            name="chk_locations_lng",
        ),
        CheckConstraint(
            "(latitude IS NULL) = (longitude IS NULL)",
            name="chk_locations_pair",
        ),
        Index("idx_locations_category_active", "category", "is_active"),
    )

    id: Mapped[int] = mapped_column(
        BIGINT_ID,
        Identity(always=True),
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    latitude: Mapped[Decimal | None] = mapped_column(
        Numeric(9, 6),
        nullable=True,
    )

    longitude: Mapped[Decimal | None] = mapped_column(
        Numeric(9, 6),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
