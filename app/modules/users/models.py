"""Model SQLAlchemy modul users."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Identity,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import column

from app.db.base import BIGINT_ID, Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    __table_args__ = (
        CheckConstraint(
            "role IN ('CUSTOMER', 'DRIVER', 'ADMIN')",
            name="chk_users_role",
        ),
        CheckConstraint(
            "availability_status IN ('ACTIVE', 'INACTIVE')",
            name="chk_users_availability",
        ),
        Index(
            "uq_users_email_lower",
            func.lower(column("email")),
            unique=True,
        ),
        Index("idx_users_role", "role"),
    )

    id: Mapped[int] = mapped_column(
        BIGINT_ID,
        Identity(always=True),
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="CUSTOMER",
        server_default=text("'CUSTOMER'"),
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    availability_status: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="INACTIVE",
        server_default=text("'INACTIVE'"),
    )
