"""Logika bisnis modul admin — Master API Reference v1.3 (Bagian 11)."""

from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.constants import DriverApplicationStatus, OrderStatus
from app.core.errors import BadRequestError, ConflictError, ErrorCode, NotFoundError
from app.core.security import Role
from app.modules.admin.schemas import (
    AdminDriverApplicationItem,
    AdminLocationCreateRequest,
    AdminLocationDeactivateItem,
    AdminLocationItem,
    AdminLocationUpdateRequest,
    AdminOrderItem,
    AdminSummaryDetail,
    DriverApplicationReviewItem,
)
from app.modules.drivers.models import DriverApplication
from app.modules.locations.models import Location
from app.modules.orders.models import Order
from app.modules.services.models import ServiceType
from app.modules.users.models import User


def list_orders(db: Session, status: str | None = None) -> list[AdminOrderItem]:
    stmt = (
        select(Order, ServiceType.code)
        .outerjoin(ServiceType, Order.service_type_id == ServiceType.id)
        .order_by(Order.id.desc())
    )
    if status:
        stmt = stmt.where(Order.status == status.upper())

    rows = db.execute(stmt).all()
    return [
        AdminOrderItem(
            id=order.id,
            customer_id=order.customer_id,
            driver_id=order.driver_id,
            service_type=service_code or "ANTAR_JEMPUT",
            status=order.status,
        )
        for order, service_code in rows
    ]


def get_summary(db: Session) -> AdminSummaryDetail:
    counts = dict(
        db.execute(select(Order.status, func.count(Order.id)).group_by(Order.status)).all()
    )

    open_orders = counts.get(OrderStatus.OPEN.value, 0)
    accepted_orders = counts.get(OrderStatus.ACCEPTED.value, 0)
    on_the_way_orders = counts.get(OrderStatus.ON_THE_WAY.value, 0)
    completed_orders = counts.get(OrderStatus.COMPLETED.value, 0)
    cancelled_orders = counts.get(OrderStatus.CANCELLED.value, 0)

    # Sesuai Bagian 9.1 v1.3: Role DRIVER, Application APPROVED, Availability ACTIVE
    active_drivers = (
        db.scalar(
            select(func.count(func.distinct(User.id)))
            .join(DriverApplication, DriverApplication.user_id == User.id)
            .where(
                User.is_active.is_(True),
                User.role == Role.DRIVER.value,
                User.availability_status == "ACTIVE",
                DriverApplication.status == DriverApplicationStatus.APPROVED.value,
            )
        )
        or 0
    )

    pending_driver_applications = (
        db.scalar(
            select(func.count(DriverApplication.id)).where(
                DriverApplication.status == DriverApplicationStatus.PENDING.value
            )
        )
        or 0
    )

    return AdminSummaryDetail(
        total_orders=(
            open_orders
            + accepted_orders
            + on_the_way_orders
            + completed_orders
            + cancelled_orders
        ),
        open_orders=open_orders,
        accepted_orders=accepted_orders,
        on_the_way_orders=on_the_way_orders,
        completed_orders=completed_orders,
        cancelled_orders=cancelled_orders,
        active_drivers=active_drivers,
        pending_driver_applications=pending_driver_applications,
    )


def list_driver_applications(
    db: Session,
    status: str | None = None,
) -> list[AdminDriverApplicationItem]:
    stmt = select(DriverApplication).order_by(DriverApplication.id.desc())
    if status:
        stmt = stmt.where(DriverApplication.status == status.upper())

    apps = db.scalars(stmt).all()
    return [
        AdminDriverApplicationItem(
            id=app.id,
            user_id=app.user_id,
            vehicle_type="MOTOR",
            vehicle_description=app.application_note,
            status=app.status,
        )
        for app in apps
    ]


def review_driver_application(
    db: Session,
    application_id: int,
    new_status: str,
    admin_id: int,
) -> DriverApplicationReviewItem:
    application = db.get(DriverApplication, application_id)
    if application is None:
        raise NotFoundError(
            ErrorCode.DRIVER_APPLICATION_NOT_FOUND,
            "Pengajuan tidak ditemukan",
        )

    if application.status != DriverApplicationStatus.PENDING.value:
        raise ConflictError(ErrorCode.CONFLICT, "Pengajuan tidak dapat diproses")

    application.status = new_status
    application.reviewed_by = admin_id
    application.reviewed_at = datetime.now(timezone.utc)

    if new_status == DriverApplicationStatus.APPROVED.value:
        user = db.get(User, application.user_id)
        if user is not None:
            user.role = Role.DRIVER.value

    db.commit()
    db.refresh(application)

    return DriverApplicationReviewItem(id=application.id, status=application.status)


def list_locations(db: Session) -> list[AdminLocationItem]:
    locations = db.scalars(select(Location).order_by(Location.id.asc())).all()
    return [
        AdminLocationItem(
            id=loc.id,
            name=loc.name,
            description=loc.description,
            is_active=loc.is_active,
        )
        for loc in locations
    ]


def create_location(
    db: Session,
    payload: AdminLocationCreateRequest,
) -> AdminLocationItem:
    clean_name = payload.name.strip()
    if not clean_name:
        raise BadRequestError(ErrorCode.BAD_REQUEST, "Nama lokasi tidak boleh kosong")

    existing = db.scalar(
        select(Location).where(func.lower(Location.name) == clean_name.lower())
    )
    if existing is not None:
        raise ConflictError(ErrorCode.CONFLICT, "Lokasi duplikat")

    location = Location(
        name=clean_name,
        category="LAINNYA",
        description=payload.description,
        is_active=True,
    )
    db.add(location)
    db.commit()
    db.refresh(location)

    return AdminLocationItem(
        id=location.id,
        name=location.name,
        description=location.description,
        is_active=location.is_active,
    )


def update_location(
    db: Session,
    location_id: int,
    payload: AdminLocationUpdateRequest,
) -> AdminLocationItem:
    location = db.get(Location, location_id)
    if location is None:
        raise NotFoundError(ErrorCode.LOCATION_NOT_FOUND, "Lokasi tidak ditemukan")

    if payload.name is not None:
        clean_name = payload.name.strip()
        if not clean_name:
            raise BadRequestError(ErrorCode.BAD_REQUEST, "Nama lokasi tidak boleh kosong")

        duplicate = db.scalar(
            select(Location).where(
                func.lower(Location.name) == clean_name.lower(),
                Location.id != location_id,
            )
        )
        if duplicate is not None:
            raise ConflictError(ErrorCode.CONFLICT, "Lokasi duplikat")

        location.name = clean_name

    if payload.description is not None:
        location.description = payload.description

    db.commit()
    db.refresh(location)

    return AdminLocationItem(
        id=location.id,
        name=location.name,
        description=location.description,
        is_active=location.is_active,
    )


def deactivate_location(db: Session, location_id: int) -> AdminLocationDeactivateItem:
    location = db.get(Location, location_id)
    if location is None:
        raise NotFoundError(ErrorCode.LOCATION_NOT_FOUND, "Lokasi tidak ditemukan")

    if not location.is_active:
        raise ConflictError(
            ErrorCode.CONFLICT,
            "Lokasi sudah nonaktif atau tidak dapat dinonaktifkan",
        )

    location.is_active = False
    db.commit()
    db.refresh(location)

    return AdminLocationDeactivateItem(id=location.id, is_active=location.is_active)
