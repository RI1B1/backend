"""Logika bisnis modul orders. Router hanya memanggil fungsi di sini."""

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.constants import OrderStatus, can_transition
from app.core.errors import (
    AppException,
    ConflictError,
    ErrorCode,
    ForbiddenError,
    NotFoundError,
)
from app.core.security import CurrentUser, Role
from app.modules.locations.models import Location
from app.modules.orders.models import Order
from app.modules.orders.schemas import OrderCreate
from app.modules.orders.status_models import OrderStatusLog
from app.modules.services.models import ServiceType


def _validation_error(field: str, message: str) -> None:
    raise AppException(
        ErrorCode.VALIDATION_ERROR,
        "Data yang dikirim tidak valid.",
        details=[{"field": field, "message": message}],
        status_code=422,
    )


def _get_order(db: Session, order_id: int) -> tuple[Order, str]:
    row = db.execute(
        select(Order, ServiceType.code)
        .join(ServiceType, ServiceType.id == Order.service_type_id)
        .where(Order.id == order_id)
    ).one_or_none()
    if row is None:
        raise NotFoundError(ErrorCode.ORDER_NOT_FOUND, "Pesanan tidak ditemukan.")
    return row[0], row[1]


def _order_response(order: Order, service_type: str) -> dict:
    description = (
        order.item_description
        if service_type == "JASA_TITIP"
        else order.notes
    )
    return {
        "id": order.id,
        "customer_id": order.customer_id,
        "driver_id": order.driver_id,
        "service_type": service_type,
        "pickup_location_id": order.pickup_location_id,
        "destination_location_id": order.destination_location_id,
        "description": description,
        "expected_cost": order.optional_cost_expectation,
        "status": order.status,
    }


def create_order(db: Session, customer_id: int, payload: OrderCreate) -> dict:
    service_type = db.scalar(
        select(ServiceType).where(
            ServiceType.code == payload.service_type,
            ServiceType.is_active.is_(True),
        )
    )
    if service_type is None:
        raise NotFoundError(ErrorCode.SERVICE_NOT_FOUND, "Jenis layanan tidak ditemukan.")

    if payload.pickup_location_id == payload.destination_location_id:
        _validation_error(
            "destination_location_id",
            "Lokasi awal dan tujuan tidak boleh sama.",
        )

    locations = {
        location.id: location
        for location in db.scalars(
            select(Location).where(
                Location.id.in_(
                    [payload.pickup_location_id, payload.destination_location_id]
                )
            )
        )
    }
    for field, location_id in (
        ("pickup_location_id", payload.pickup_location_id),
        ("destination_location_id", payload.destination_location_id),
    ):
        location = locations.get(location_id)
        if location is None:
            raise NotFoundError(ErrorCode.LOCATION_NOT_FOUND, "Lokasi tidak ditemukan.")
        if not location.is_active:
            raise AppException(
                ErrorCode.LOCATION_INACTIVE,
                "Lokasi tidak aktif untuk pesanan baru.",
                details=[{"field": field, "message": "Pilih lokasi yang masih aktif."}],
                status_code=422,
            )

    order = Order(
        customer_id=customer_id,
        service_type_id=service_type.id,
        status=OrderStatus.OPEN.value,
        pickup_location_id=payload.pickup_location_id,
        destination_location_id=payload.destination_location_id,
        item_description=(
            payload.description if payload.service_type == "JASA_TITIP" else None
        ),
        notes=payload.description if payload.service_type == "ANTAR_JEMPUT" else None,
        optional_cost_expectation=payload.expected_cost,
    )
    db.add(order)
    db.flush()
    db.add(
        OrderStatusLog(
            order_id=order.id,
            old_status=None,
            new_status=OrderStatus.OPEN.value,
            changed_by=customer_id,
        )
    )
    db.commit()
    db.refresh(order)

    return {
        "message": "Order berhasil dibuat",
        "order": _order_response(order, service_type.code),
    }


def get_my_orders(db: Session, customer_id: int) -> dict:
    rows = db.execute(
        select(Order, ServiceType.code)
        .join(ServiceType, ServiceType.id == Order.service_type_id)
        .where(Order.customer_id == customer_id)
        .order_by(Order.created_at.desc(), Order.id.desc())
    ).all()
    return {
        "orders": [_order_response(order, service_type) for order, service_type in rows]
    }


def _ensure_order_access(order: Order, user: CurrentUser) -> None:
    if user.role == Role.ADMIN:
        return
    if user.role == Role.CUSTOMER and order.customer_id == user.id:
        return
    if user.role == Role.DRIVER and order.driver_id == user.id:
        return
    raise ForbiddenError(
        ErrorCode.ORDER_ACCESS_DENIED,
        "Kamu tidak memiliki akses ke pesanan ini.",
    )


def get_order(db: Session, order_id: int, user: CurrentUser) -> dict:
    order, service_type = _get_order(db, order_id)
    _ensure_order_access(order, user)
    return _order_response(order, service_type)


def update_order_status(
    db: Session,
    order_id: int,
    driver_id: int,
    new_status: str,
) -> dict:
    order, service_type = _get_order(db, order_id)
    if order.driver_id != driver_id:
        raise ForbiddenError(
            ErrorCode.ORDER_ACCESS_DENIED,
            "Hanya Driver yang menerima pesanan ini yang dapat mengubah status.",
        )

    old_status = OrderStatus(order.status)
    target_status = OrderStatus(new_status)
    if not can_transition(old_status, target_status):
        raise ConflictError(
            ErrorCode.INVALID_STATUS_TRANSITION,
            "Transisi status pesanan tidak valid.",
        )

    result = db.execute(
        update(Order)
        .where(
            Order.id == order_id,
            Order.driver_id == driver_id,
            Order.status == old_status.value,
        )
        .values(status=target_status.value)
    )
    if result.rowcount != 1:
        db.rollback()
        raise ConflictError(
            ErrorCode.INVALID_STATUS_TRANSITION,
            "Status pesanan sudah berubah. Muat ulang pesanan dan coba lagi.",
        )

    db.add(
        OrderStatusLog(
            order_id=order_id,
            old_status=old_status.value,
            new_status=target_status.value,
            changed_by=driver_id,
        )
    )
    db.commit()
    db.refresh(order)
    return _order_response(order, service_type)


def cancel_order(db: Session, order_id: int, customer_id: int) -> dict:
    order, service_type = _get_order(db, order_id)
    if order.customer_id != customer_id:
        raise ForbiddenError(
            ErrorCode.ORDER_ACCESS_DENIED,
            "Kamu tidak memiliki akses ke pesanan ini.",
        )

    if order.status != OrderStatus.OPEN.value or order.driver_id is not None:
        raise ConflictError(
            ErrorCode.ORDER_NOT_CANCELLABLE,
            "Pesanan tidak dapat dibatalkan.",
        )

    result = db.execute(
        update(Order)
        .where(
            Order.id == order_id,
            Order.status == OrderStatus.OPEN.value,
            Order.driver_id.is_(None),
        )
        .values(status=OrderStatus.CANCELLED.value)
    )
    if result.rowcount != 1:
        db.rollback()
        raise ConflictError(
            ErrorCode.ORDER_NOT_CANCELLABLE,
            "Status pesanan sudah berubah. Muat ulang pesanan dan coba lagi.",
        )

    db.add(
        OrderStatusLog(
            order_id=order_id,
            old_status=OrderStatus.OPEN.value,
            new_status=OrderStatus.CANCELLED.value,
            changed_by=customer_id,
        )
    )
    db.commit()
    db.refresh(order)
    return _order_response(order, service_type)


def get_order_status_history(
    db: Session,
    order_id: int,
    user: CurrentUser,
) -> dict:
    order, _ = _get_order(db, order_id)
    _ensure_order_access(order, user)
    history = db.scalars(
        select(OrderStatusLog)
        .where(OrderStatusLog.order_id == order_id)
        .order_by(OrderStatusLog.created_at, OrderStatusLog.id)
    ).all()
    return {
        "status_history": [
            {
                "id": entry.id,
                "order_id": entry.order_id,
                "status": entry.new_status,
                "changed_by": entry.changed_by,
                "created_at": entry.created_at,
            }
            for entry in history
        ]
    }
