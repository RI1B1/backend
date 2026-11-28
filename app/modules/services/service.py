"""Logika bisnis modul services. Router hanya memanggil fungsi di sini."""
"""Logika bisnis modul services. Router hanya memanggil fungsi di sini."""
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.modules.services.models import ServiceType

DEFAULT_SERVICES = [
    {"id": 1, "name": "ANTAR_JEMPUT", "description": "Layanan antar jemput"},
    {"id": 2, "name": "JASA_TITIP", "description": "Layanan jasa titip"},
]


def get_all_services(db: Session) -> list[dict]:
    """Mengambil daftar layanan dari database dengan fallback data MVP."""
    try:
        rows = db.query(ServiceType).order_by(ServiceType.id.asc()).all()
        if rows:
            return [
                {"id": row.id, "name": row.name, "description": row.description}
                for row in rows
            ]
    except SQLAlchemyError:
        # Jika migration tabel belum dijalankan di lokal, tetap kembalikan daftar layanan MVP
        db.rollback()

    return DEFAULT_SERVICES