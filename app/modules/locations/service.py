"""Logika bisnis modul locations. Router hanya memanggil fungsi di sini."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, ErrorCode, NotFoundError
from app.modules.locations.models import Location
from app.modules.locations.schemas import LocationUpdateIn


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


# ---------------------------------------------------------------- Admin (11.5 - 11.8)


def list_all_locations(db: Session) -> dict:
    """Daftar semua lokasi untuk Admin (aktif dan nonaktif).

    Asumsi: kontrak 11.5 tidak menyebut filter, jadi lokasi nonaktif ikut ditampilkan
    agar Admin bisa melihat yang sudah dinonaktifkan. Menunggu konfirmasi tim.
    """
    rows = db.scalars(select(Location).order_by(Location.id)).all()
    return {"locations": list(rows)}


def update_location(db: Session, location_id: int, data: LocationUpdateIn) -> dict:
    """Perbarui name dan/atau description (11.7). 404 jika lokasi tidak ada.

    Belum ada pengecekan nama duplikat: aturannya belum ditetapkan di kontrak
    (11.7 tidak mencantumkan 409). Tambahkan setelah tim memutuskan.
    """
    location = get_location(db, location_id)
    if "name" in data.model_fields_set:
        location.name = data.name
    if "description" in data.model_fields_set:
        location.description = data.description
    db.commit()
    db.refresh(location)
    return {"message": "Lokasi berhasil diperbarui", "location": location}


def deactivate_location(db: Session, location_id: int) -> dict:
    """Nonaktifkan lokasi (11.8). Soft delete: baris tidak dihapus.

    404 jika tidak ada, 409 jika sudah nonaktif.
    """
    location = get_location(db, location_id)
    if not location.is_active:
        raise ConflictError(ErrorCode.CONFLICT, "Lokasi sudah nonaktif.")
    location.is_active = False
    db.commit()
    db.refresh(location)
    return {"message": "Lokasi berhasil dinonaktifkan", "location": location}
