
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    __table_args__ = (
        CheckConstraint(
            "status IN ('OPEN', 'ACCEPTED', 'ON_THE_WAY', 'COMPLETED', 'CANCELLED')",
            name="ck_orders_status",
        ),
        CheckConstraint(
            "passenger_count IS NULL OR passenger_count > 0",
            name="ck_orders_passenger_count",
        ),
        CheckConstraint(
            "optional_cost_expectation IS NULL "
            "OR optional_cost_expectation >= 0",
            name="ck_orders_optional_cost_expectation",
        ),
        CheckConstraint(
            "service_request_type IS NULL OR "
            "service_request_type IN ('AMBIL_BARANG', 'BELIKAN_BARANG')",
            name="ck_orders_service_request_type",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    customer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    driver_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    service_type_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("service_types.id"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="OPEN",
        server_default="OPEN",
        index=True,
    )

    pickup_location_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("locations.id"),
        nullable=True,
    )

    destination_location_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("locations.id"),
        nullable=True,
    )

    service_request_type: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    item_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    passenger_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    optional_cost_expectation: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
