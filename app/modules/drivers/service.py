"""Logika bisnis modul drivers. Router hanya memanggil fungsi di sini."""
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, aliased

from app.core.constants import DriverApplicationStatus
from app.core.errors import ConflictError, ErrorCode, NotFoundError
from app.core.response import ok, paginated
from app.core.security import CurrentUser
from app.modules.locations.models import Location
from app.modules.orders.models import Order
from app.modules.services.models import ServiceType
from app.modules.users.models import User

from .models import DriverApplication
from .schemas import DriverAvailabilityStatus


def get_availability(db: Session, user: CurrentUser) -> dict:
    availability_status = db.execute(
        text("SELECT availability_status FROM users WHERE id = :user_id"),
        {"user_id": user.id},
    ).scalar_one_or_none()
    if availability_status is None:
        raise ConflictError(
            ErrorCode.CONFLICT,
            "Status ketersediaan Driver tidak ditemukan.",
        )
    return ok({"availability_status": availability_status})


def update_availability(
    db: Session,
    user: CurrentUser,
    availability_status: DriverAvailabilityStatus,
) -> dict:
    result = db.execute(
        text(
            """
            UPDATE users
            SET availability_status = :availability_status,
            updated_at = CURRENT_TIMESTAMP
            WHERE id = :user_id
            RETURNING availability_status
            """
        ),
        {
            "availability_status": availability_status.value,
            "user_id": user.id,
        },
    )
    availability_status = result.scalar_one_or_none()
    if availability_status is None:
        raise ConflictError(
            ErrorCode.CONFLICT,
            "Status ketersediaan Driver tidak dapat diubah.",
        )

    db.commit()
    return ok({"availability_status": availability_status})


def create_application(
    db: Session,
    user: CurrentUser,
    application_note: str | None,
) -> dict:
    active_application = db.scalar(
        select(DriverApplication).where(
            DriverApplication.user_id == user.id,
            DriverApplication.status.in_(
                [
                    DriverApplicationStatus.PENDING.value,
                    DriverApplicationStatus.APPROVED.value,
                ]
            ),
        )
    )
    if active_application is not None:
        raise ConflictError(
            ErrorCode.DRIVER_APPLICATION_EXISTS,
            "Pengajuan Driver masih aktif atau sudah disetujui.",
        )

    application = DriverApplication(
        user_id=user.id,
        status=DriverApplicationStatus.PENDING.value,
        application_note=application_note,
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    applicant = db.get(User, application.user_id)
    return ok(application_to_dict(application, applicant))


def get_application(db: Session, user: CurrentUser) -> dict:
    result = db.execute(
        select(DriverApplication, User)
        .join(User, User.id == DriverApplication.user_id)
        .where(DriverApplication.user_id == user.id)
        .order_by(DriverApplication.created_at.desc(), DriverApplication.id.desc())
        .limit(1)
    ).one_or_none()
    if result is None:
        raise NotFoundError(
            ErrorCode.DRIVER_APPLICATION_NOT_FOUND,
            "Pengajuan Driver tidak ditemukan.",
        )
    application, applicant = result
    return ok(application_to_dict(application, applicant))


def get_history(db: Session, user: CurrentUser, page: int, limit: int) -> dict:
    customer = aliased(User)
    driver = aliased(User)
    pickup = aliased(Location)
    destination = aliased(Location)
    offset = (page - 1) * limit
    total = db.scalar(
        select(func.count(Order.id)).where(Order.driver_id == user.id)
    ) or 0

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
        .join(ServiceType, ServiceType.id == Order.service_type_id)
        .outerjoin(driver, driver.id == Order.driver_id)
        .outerjoin(pickup, pickup.id == Order.pickup_location_id)
        .outerjoin(destination, destination.id == Order.destination_location_id)
        .where(Order.driver_id == user.id)
        .order_by(Order.created_at.desc(), Order.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return paginated(
        [
            order_to_dict(
                order,
                customer,
                driver,
                service_type,
                pickup_location,
                destination_location,
            )
            for (
                order,
                customer,
                driver,
                service_type,
                pickup_location,
                destination_location,
            ) in results
        ],
        page,
        limit,
        total,
    )


def application_to_dict(application: DriverApplication, user: User) -> dict:
    return {
        "id": application.id,
        "status": application.status,
        "application_note": application.application_note,
        "reviewed_at": application.reviewed_at,
        "created_at": application.created_at,
        "user": {"id": user.id, "name": user.name},
    }


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
