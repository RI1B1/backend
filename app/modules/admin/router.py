"""Router endpoint Admin — Master API Reference v1.3 (Bagian 11)."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.response import ok
from app.core.security import CurrentUser, Role, require_role
from app.db.session import get_db
from app.modules.admin import service
from app.modules.admin.schemas import (
    AdminDriverApplicationListResponse,
    AdminLocationCreateRequest,
    AdminLocationDeactivateResponse,
    AdminLocationListResponse,
    AdminLocationMutationResponse,
    AdminLocationUpdateRequest,
    AdminOrderListResponse,
    AdminSummaryResponse,
    DriverApplicationReviewRequest,
    DriverApplicationReviewResponse,
)

router = APIRouter(prefix="/admin", tags=["Admin"])
admin_only = require_role(Role.ADMIN)


# Dipertahankan sementara agar tests/test_role_guard.py bawaan repo tetap hijau
@router.get("/ping", summary="Cek role guard Admin")
def admin_ping(user: CurrentUser = Depends(admin_only)):
    return ok({"message": "pong", "user_id": user.id})


@router.get("/orders", response_model=AdminOrderListResponse)
def get_admin_orders(
    status_filter: str | None = Query(default=None, alias="status"),
    _: CurrentUser = Depends(admin_only),
    db: Session = Depends(get_db),
):
    return AdminOrderListResponse(
        orders=service.list_orders(db=db, status=status_filter)
    )


@router.get("/summary", response_model=AdminSummaryResponse)
def get_admin_summary(
    _: CurrentUser = Depends(admin_only),
    db: Session = Depends(get_db),
):
    return AdminSummaryResponse(summary=service.get_summary(db=db))


@router.get(
    "/driver-applications",
    response_model=AdminDriverApplicationListResponse,
)
def get_driver_applications(
    status_filter: str | None = Query(default=None, alias="status"),
    _: CurrentUser = Depends(admin_only),
    db: Session = Depends(get_db),
):
    return AdminDriverApplicationListResponse(
        applications=service.list_driver_applications(db=db, status=status_filter)
    )


@router.patch(
    "/driver-applications/{application_id}",
    response_model=DriverApplicationReviewResponse,
)
def patch_driver_application(
    application_id: int,
    payload: DriverApplicationReviewRequest,
    current_admin: CurrentUser = Depends(admin_only),
    db: Session = Depends(get_db),
):
    reviewed = service.review_driver_application(
        db=db,
        application_id=application_id,
        new_status=payload.status,
        admin_id=current_admin.id,
    )
    return DriverApplicationReviewResponse(
        message="Status pengajuan berhasil diperbarui",
        application=reviewed,
    )


@router.get("/locations", response_model=AdminLocationListResponse)
def get_admin_locations(
    _: CurrentUser = Depends(admin_only),
    db: Session = Depends(get_db),
):
    return AdminLocationListResponse(locations=service.list_locations(db=db))


@router.post(
    "/locations",
    response_model=AdminLocationMutationResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_admin_location(
    payload: AdminLocationCreateRequest,
    _: CurrentUser = Depends(admin_only),
    db: Session = Depends(get_db),
):
    location = service.create_location(db=db, payload=payload)
    return AdminLocationMutationResponse(
        message="Lokasi berhasil ditambahkan",
        location=location,
    )


@router.patch(
    "/locations/{location_id}",
    response_model=AdminLocationMutationResponse,
)
def patch_admin_location(
    location_id: int,
    payload: AdminLocationUpdateRequest,
    _: CurrentUser = Depends(admin_only),
    db: Session = Depends(get_db),
):
    location = service.update_location(
        db=db, location_id=location_id, payload=payload
    )
    return AdminLocationMutationResponse(
        message="Lokasi berhasil diperbarui",
        location=location,
    )


@router.patch(
    "/locations/{location_id}/deactivate",
    response_model=AdminLocationDeactivateResponse,
)
def deactivate_admin_location(
    location_id: int,
    _: CurrentUser = Depends(admin_only),
    db: Session = Depends(get_db),
):
    location = service.deactivate_location(db=db, location_id=location_id)
    return AdminLocationDeactivateResponse(
        message="Lokasi berhasil dinonaktifkan",
        location=location,
    )
