"""Logika bisnis modul orders. Router hanya memanggil fungsi di sini."""
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, aliased

from app.core.constants import DriverApplicationStatus, OrderStatus
from app.core.errors import (
    ConflictError,
    ErrorCode,
    ForbiddenError,
    NotFoundError,
)
from app.core.response import ok, paginated
from app.core.security import CurrentUser
from app.modules.locations.models import Location
from app.modules.services.models import ServiceType
from app.modules.users.models import User

from .models import Order
from .status_models import OrderStatusLog


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
