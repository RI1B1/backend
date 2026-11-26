from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BIGINT_ID, Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    __table_args__ = (
        CheckConstraint(
            "length(message) BETWEEN 1 AND 2000",
            name="chk_chat_message_length",
        ),
        Index("idx_chat_order_time", "order_id", "created_at"),
        Index("idx_chat_sender", "sender_id"),
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

    sender_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
