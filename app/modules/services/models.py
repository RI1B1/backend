"""Model SQLAlchemy modul services. Didaftarkan di app/db/registry.py."""
from app.db.base import Base, TimestampMixin  # noqa: F401
"""Model SQLAlchemy modul services. Didaftarkan di app/db/registry.py."""
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ServiceType(Base, TimestampMixin):
    __tablename__ = "service_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)