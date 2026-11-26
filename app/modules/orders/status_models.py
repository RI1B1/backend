from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BIGINT_ID, Base


class OrderStatusLog(Base):
    __tablename__ = "order_status_logs"

    __table_args__ = (
        CheckConstraint(
            "new_status IN "
            "('OPEN', 'ACCEPTED', 'ON_THE_WAY', 'COMPLETED', 'CANCELLED')",
            name="chk_status_log_new",
        ),
        CheckConstraint(
            "old_status IS NULL OR old_status IN "
            "('OPEN', 'ACCEPTED', 'ON_THE_WAY', 'COMPLETED', 'CANCELLED')",
            name="chk_status_log_old",
        ),
        Index("idx_status_logs_order", "order_id", "created_at"),
        Index("idx_status_logs_user", "changed_by"),
    )

    id: Mapped[int] = mapped_column(
        BIGINT_ID,
        Identity(always=True),
        primary_key=True,
    )

    order_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
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
        BIGINT_ID,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
