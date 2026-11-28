"""Logika bisnis modul locations. Router hanya memanggil fungsi di sini."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ErrorCode, NotFoundError
from app.modules.locations.models import Location


def list_active_locations(db: Session) -> dict:
    """Daftar lokasi preset yang aktif (untuk dropdown pemesanan)."""
    rows = db.scalars(
        select(Location).where(Location.is_active.is_(True)).order_by(Location.id)
    ).all()
    return {"locations": list(rows)}


def get_location(db: Session, location_id: int) -> Location:
    """Detail satu lokasi. 404 LOCATION_NOT_FOUND jika tidak ada.

    Catatan: kontrak v1.3 belum menyebut apakah lokasi nonaktif boleh diambil lewat
    endpoint detail. Saat ini lokasi nonaktif tetap dikembalikan (is_active=false) agar
    riwayat order yang merujuk lokasi itu tetap bisa ditampilkan. Menunggu konfirmasi tim.
    """
    location = db.get(Location, location_id)
    if location is None:
        raise NotFoundError(ErrorCode.LOCATION_NOT_FOUND, "Lokasi tidak ditemukan.")
    return location
