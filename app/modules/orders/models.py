"""Model SQLAlchemy modul orders. Didaftarkan di app/db/registry.py."""
from app.db.base import Base, TimestampMixin  # noqa: F401
"""Model SQLAlchemy modul orders. Didaftarkan di app/db/registry.py."""
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    customer_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    driver_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    service_type: Mapped[str] = mapped_column(String(50), nullable=False)
    pickup_location_id: Mapped[int] = mapped_column(Integer, nullable=False)
    destination_location_id: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    expected_cost: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN", index=True)


class OrderStatusLog(Base, TimestampMixin):
    __tablename__ = "order_status_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    changed_by: Mapped[str] = mapped_column(String(64), nullable=False)