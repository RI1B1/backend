
"""add service request type constraint

Revision ID: 5d158c3a338b
Revises: cbf3f86c6c86
Create Date: 2026-11-25 03:13:34.160749
"""

from typing import Sequence, Union

from alembic import op


revision: str = "5d158c3a338b"
down_revision: Union[str, None] = "cbf3f86c6c86"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_orders_service_request_type",
        "orders",
        "service_request_type IS NULL OR "
        "service_request_type IN ('AMBIL_BARANG', 'BELIKAN_BARANG')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_orders_service_request_type",
        "orders",
        type_="check",
    )
