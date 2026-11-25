
"""add default open status to orders

Revision ID: cbf3f86c6c86
Revises: 742ff9b8b8b8
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "cbf3f86c6c86"
down_revision: Union[str, None] = "742ff9b8b8b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "orders",
        "status",
        existing_type=sa.String(length=20),
        server_default="OPEN",
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "orders",
        "status",
        existing_type=sa.String(length=20),
        server_default=None,
        existing_nullable=False,
    )
