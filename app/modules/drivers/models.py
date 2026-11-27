"""Model SQLAlchemy modul drivers."""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BIGINT_ID, Base, TimestampMixin


class DriverApplication(Base, TimestampMixin):
    __tablename__ = "driver_applications"

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'APPROVED', 'REJECTED')",
            name="chk_driver_app_status",
        ),
        CheckConstraint(
            "status = 'PENDING' OR "
            "(reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)",
            name="chk_driver_app_review",
        ),
        CheckConstraint(
            "status = 'PENDING' OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)",
            name="ck_driver_applications_review",
        ),
    )

    id: Mapped[int] = mapped_column(
        BIGINT_ID,
        Identity(always=True),
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="PENDING",
        server_default=text("'PENDING'"),
    )

    application_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    reviewed_by: Mapped[int | None] = mapped_column(
        BIGINT_ID,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
