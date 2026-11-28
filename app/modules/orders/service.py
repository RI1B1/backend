"""Logika bisnis modul orders. Router hanya memanggil fungsi di sini."""

from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session, aliased

from app.core.constants import DriverApplicationStatus, OrderStatus, can_transition
from app.core.errors import (
    AppException,
    ConflictError,
    ErrorCode,
    ForbiddenError,
    NotFoundError,
)
from app.core.response import ok, paginated
from app.core.security import CurrentUser, Role
from app.modules.locations.models import Location
from app.modules.orders.models import Order
from app.modules.orders.schemas import OrderCreate
from app.modules.orders.status_models import OrderStatusLog
from app.modules.services.models import ServiceType
from app.modules.users.models import User


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


def get_available_orders(
    db: Session,
    page: int,
    limit: int,
) -> dict:
    filters = (
        Order.status == OrderStatus.OPEN.value,
        Order.driver_id.is_(None),
    )
    total = db.scalar(select(func.count(Order.id)).where(*filters)) or 0

    customer = aliased(User)
    driver = aliased(User)
    pickup = aliased(Location)
    destination = aliased(Location)
    results = db.execute(
        select(
            Order,
            customer,
            driver,
            ServiceType,
            pickup,
            destination,
        )
        .join(customer, customer.id == Order.customer_id)
        .outerjoin(driver, driver.id == Order.driver_id)
        .join(ServiceType, ServiceType.id == Order.service_type_id)
        .outerjoin(pickup, pickup.id == Order.pickup_location_id)
        .outerjoin(destination, destination.id == Order.destination_location_id)
        .where(*filters)
        .order_by(Order.created_at.desc(), Order.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()

    return paginated(
        [
            order_to_dict(
                order,
                customer_user,
                driver_user,
                service_type,
                pickup_location,
                destination_location,
            )
            for (
                order,
                customer_user,
                driver_user,
                service_type,
                pickup_location,
                destination_location,
            ) in results
        ],
        page,
        limit,
        total,
    )


def accept_order(db: Session, order_id: int, user: CurrentUser) -> dict:
    active_driver = db.scalar(
        text(
            """
            SELECT 1
            FROM users
            WHERE id = :driver_id
              AND is_active = TRUE
              AND availability_status = :active_status
            """
        ),
        {
            "driver_id": user.id,
            "active_status": "ACTIVE",
        },
    )
    if active_driver is None:
        raise ForbiddenError(
            ErrorCode.FORBIDDEN,
            "Driver harus berstatus ACTIVE untuk menerima pesanan.",
        )

    accepted_id = db.execute(
        text(
            """
            UPDATE orders
            SET driver_id = :driver_id,
                status = :accepted_status,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :order_id
              AND status = :open_status
              AND driver_id IS NULL
              AND EXISTS (
                  SELECT 1
                  FROM users
                  WHERE id = :driver_id
                    AND is_active = TRUE
                    AND availability_status = :active_status
              )
              AND EXISTS (
                  SELECT 1
                  FROM driver_applications
                  WHERE user_id = :driver_id
                    AND status = :approved_status
              )
            RETURNING id
            """
        ),
        {
            "driver_id": user.id,
            "order_id": order_id,
            "open_status": OrderStatus.OPEN.value,
            "accepted_status": OrderStatus.ACCEPTED.value,
            "active_status": "ACTIVE",
            "approved_status": DriverApplicationStatus.APPROVED.value,
        },
    ).scalar_one_or_none()

    if accepted_id is None:
        order_exists = db.scalar(select(Order.id).where(Order.id == order_id))
        if order_exists is None:
            raise NotFoundError(ErrorCode.ORDER_NOT_FOUND, "Pesanan tidak ditemukan.")
        raise ConflictError(
            ErrorCode.ORDER_ALREADY_TAKEN,
            "Pesanan sudah diambil Driver lain atau tidak lagi tersedia.",
        )

    db.add(
        OrderStatusLog(
            order_id=accepted_id,
            old_status=OrderStatus.OPEN.value,
            new_status=OrderStatus.ACCEPTED.value,
            changed_by=user.id,
        )
    )
    db.commit()

    customer = aliased(User)
    driver = aliased(User)
    pickup = aliased(Location)
    destination = aliased(Location)
    (
        order,
        customer_user,
        driver_user,
        service_type,
        pickup_location,
        destination_location,
    ) = db.execute(
        select(
            Order,
            customer,
            driver,
            ServiceType,
            pickup,
            destination,
        )
        .join(customer, customer.id == Order.customer_id)
        .join(driver, driver.id == Order.driver_id)
        .join(ServiceType, ServiceType.id == Order.service_type_id)
        .outerjoin(pickup, pickup.id == Order.pickup_location_id)
        .outerjoin(destination, destination.id == Order.destination_location_id)
        .where(Order.id == accepted_id)
    ).one()

    return ok(
        order_to_dict(
            order,
            customer_user,
            driver_user,
            service_type,
            pickup_location,
            destination_location,
        )
    )


def _location_to_dict(location: Location | None) -> dict | None:
    if location is None:
        return None
    return {
        "id": location.id,
        "name": location.name,
        "category": location.category,
        "latitude": location.latitude,
        "longitude": location.longitude,
    }


def order_to_dict(
    order: Order,
    customer: User,
    driver: User | None,
    service_type: ServiceType,
    pickup_location: Location | None,
    destination_location: Location | None,
) -> dict:
    return {
        "id": order.id,
        "status": order.status,
        "service_type": {
            "id": service_type.id,
            "name": service_type.name,
            "code": service_type.code,
        },
        "customer": {"id": customer.id, "name": customer.name},
        "driver": {"id": driver.id, "name": driver.name} if driver is not None else None,
        "pickup_location": _location_to_dict(pickup_location),
        "destination_location": _location_to_dict(destination_location),
        "service_request_type": order.service_request_type,
        "item_description": order.item_description,
        "passenger_count": order.passenger_count,
        "optional_cost_expectation": order.optional_cost_expectation,
        "notes": order.notes,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
    }
