"""Endpoint Locations sesuai Master API Reference v1.3 bagian 6.

Respons "polos" (tanpa pembungkus {success, data}), sama seperti modul auth dan orders.
Endpoint Admin lokasi (bagian 11.5-11.8) belum dibuat: menunggu keputusan tim.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.modules.locations import service
from app.modules.locations.schemas import LocationListResponse, LocationOut

router = APIRouter(prefix="/locations", tags=["Locations"])


@router.get("", response_model=LocationListResponse)
def list_locations(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Daftar lokasi preset aktif. Akses: semua pengguna login."""
    return service.list_active_locations(db)


@router.get("/{location_id}", response_model=LocationOut)
def get_location(
    location_id: int,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Detail lokasi. Akses: semua pengguna login."""
    return service.get_location(db, location_id)
