from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Identity,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    desc,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BIGINT_ID, Base, TimestampMixin


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    __table_args__ = (
        CheckConstraint(
            "status IN ('OPEN', 'ACCEPTED', 'ON_THE_WAY', 'COMPLETED', 'CANCELLED')",
            name="chk_orders_status",
        ),
        CheckConstraint(
            "service_request_type IS NULL OR "
            "service_request_type IN ('AMBIL_BARANG', 'BELIKAN_BARANG')",
            name="chk_orders_request_type",
        ),
        CheckConstraint(
            "passenger_count IS NULL OR passenger_count > 0",
            name="chk_orders_passenger",
        ),
        CheckConstraint(
            "optional_cost_expectation IS NULL "
            "OR optional_cost_expectation >= 0",
            name="chk_orders_cost",
        ),
        CheckConstraint(
            "(status IN ('OPEN', 'CANCELLED') AND driver_id IS NULL) OR "
            "(status IN ('ACCEPTED', 'ON_THE_WAY', 'COMPLETED') "
            "AND driver_id IS NOT NULL)",
            name="chk_orders_driver_by_status",
        ),
        Index("idx_orders_customer", "customer_id", desc("created_at")),
        Index(
            "idx_orders_driver",
            "driver_id",
            desc("created_at"),
            postgresql_where=text("driver_id IS NOT NULL"),
            sqlite_where=text("driver_id IS NOT NULL"),
        ),
        Index("idx_orders_status", "status"),
        Index("idx_orders_service_type", "service_type_id"),
        Index(
            "idx_orders_open_created",
            desc("created_at"),
            postgresql_where=text("status = 'OPEN'"),
            sqlite_where=text("status = 'OPEN'"),
        ),
        Index(
            "idx_orders_pickup_loc",
            "pickup_location_id",
            postgresql_where=text("pickup_location_id IS NOT NULL"),
            sqlite_where=text("pickup_location_id IS NOT NULL"),
        ),
        Index(
            "idx_orders_dest_loc",
            "destination_location_id",
            postgresql_where=text("destination_location_id IS NOT NULL"),
            sqlite_where=text("destination_location_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(
        BIGINT_ID,
        Identity(always=True),
        primary_key=True,
    )

    customer_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    driver_id: Mapped[int | None] = mapped_column(
        BIGINT_ID,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )

    service_type_id: Mapped[int] = mapped_column(
        BIGINT_ID,
        ForeignKey("service_types.id", ondelete="RESTRICT"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="OPEN",
        server_default=text("'OPEN'"),
    )

    pickup_location_id: Mapped[int | None] = mapped_column(
        BIGINT_ID,
        ForeignKey("locations.id", ondelete="RESTRICT"),
        nullable=True,
    )

    destination_location_id: Mapped[int | None] = mapped_column(
        BIGINT_ID,
        ForeignKey("locations.id", ondelete="RESTRICT"),
        nullable=True,
    )

    service_request_type: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    item_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    passenger_count: Mapped[int | None] = mapped_column(
        SmallInteger,
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
