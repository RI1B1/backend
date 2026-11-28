"""Endpoint Admin untuk lokasi sesuai Master API Reference v1.3 bagian 11.5-11.8.

Dipisah dari router.py karena prefix-nya berbeda (/admin/locations).
POST /admin/locations (11.6) belum dibuat: menunggu keputusan tim soal kolom category.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, Role, require_role
from app.db.session import get_db
from app.modules.locations import service
from app.modules.locations.schemas import (
    LocationDeactivateResponse,
    LocationListResponse,
    LocationUpdateIn,
    LocationUpdateResponse,
)

router = APIRouter(prefix="/admin/locations", tags=["Admin Locations"])


@router.get("", response_model=LocationListResponse)
def admin_list_locations(
    admin: CurrentUser = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    """11.5 Daftar lokasi untuk Admin. Akses: ADMIN."""
    return service.list_all_locations(db)


@router.patch("/{location_id}", response_model=LocationUpdateResponse)
def admin_update_location(
    location_id: int,
    body: LocationUpdateIn,
    admin: CurrentUser = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    """11.7 Perbarui lokasi preset. Akses: ADMIN."""
    return service.update_location(db, location_id, body)


@router.patch("/{location_id}/deactivate", response_model=LocationDeactivateResponse)
def admin_deactivate_location(
    location_id: int,
    admin: CurrentUser = Depends(require_role(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    """11.8 Nonaktifkan lokasi preset (bukan hapus permanen). Akses: ADMIN."""
    return service.deactivate_location(db, location_id)
