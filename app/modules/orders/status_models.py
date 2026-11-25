
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OrderStatusLog(Base):
    __tablename__ = "order_status_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"),
        nullable=False,
        index=True,
    )

    old_status: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    new_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    changed_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "old_status IS NULL OR old_status IN "
            "('OPEN', 'ACCEPTED', 'ON_THE_WAY', 'COMPLETED', 'CANCELLED')",
            name="ck_order_status_logs_old_status",
        ),
        CheckConstraint(
            "new_status IN "
            "('OPEN', 'ACCEPTED', 'ON_THE_WAY', 'COMPLETED', 'CANCELLED')",
            name="ck_order_status_logs_new_status",
        ),
    )
