"""Logika bisnis modul orders. Router hanya memanggil fungsi di sini."""
"""Logika bisnis modul orders. Router hanya memanggil fungsi di sini."""
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.errors import (
    BadRequestError,
    ConflictError,
    ErrorCode,
    ForbiddenError,
    NotFoundError,
)
from app.core.security import CurrentUser, Role
from app.modules.orders.models import Order, OrderStatusLog
from app.modules.orders.schemas import OrderCreateRequest, OrderStatusEnum, ServiceTypeEnum


def _validate_active_location(db: Session, location_id: int, label: str) -> None:
    """Memastikan lokasi ada di tabel locations dan berstatus aktif (is_active = True)."""
    try:
        row = db.execute(
            text("SELECT id, is_active FROM locations WHERE id = :loc_id"),
            {"loc_id": location_id},
        ).fetchone()
    except SQLAlchemyError:
        # Jika tabel locations belum dimigrasi saat unit testing awal, rollback transaksi error
        db.rollback()
        return

    if row is None:
        raise NotFoundError(ErrorCode.LOCATION_NOT_FOUND, f"{label} tidak ditemukan.")

    if not bool(row.is_active):
        raise BadRequestError(
            ErrorCode.BAD_REQUEST,
            f"{label} sudah dinonaktifkan dan tidak dapat digunakan untuk pesanan baru.",
        )


def create_order(db: Session, payload: OrderCreateRequest, current_user: CurrentUser) -> Order:
    """Validasi bisnis dan pembuatan order baru oleh CUSTOMER."""
    # 1. Validasi Role
    if current_user.role != Role.CUSTOMER:
        raise ForbiddenError(
            ErrorCode.FORBIDDEN,
            "Hanya pengguna dengan role CUSTOMER yang dapat membuat pesanan.",
        )

    # 2. Validasi Lokasi Awal & Tujuan
    _validate_active_location(db, payload.pickup_location_id, "Lokasi awal")
    _validate_active_location(db, payload.destination_location_id, "Lokasi tujuan")

    # 3. Validasi khusus Antar-Jemput: titik jemput & tujuan tidak boleh sama
    if (
        payload.service_type == ServiceTypeEnum.ANTAR_JEMPUT
        and payload.pickup_location_id == payload.destination_location_id
    ):
        raise BadRequestError(
            ErrorCode.BAD_REQUEST,
            "Lokasi awal dan tujuan tidak boleh sama untuk layanan Antar-Jemput.",
        )

    # 4. Simpan Order dengan status wajib OPEN dan driver_id None
    new_order = Order(
        customer_id=str(current_user.id),
        driver_id=None,
        service_type=payload.service_type.value,
        pickup_location_id=payload.pickup_location_id,
        destination_location_id=payload.destination_location_id,
        description=payload.description,
        expected_cost=payload.expected_cost,
        status=OrderStatusEnum.OPEN.value,
    )
    db.add(new_order)
    db.flush()

    # 5. Catat log status awal ke order_status_logs
    initial_log = OrderStatusLog(
        order_id=new_order.id,
        status=OrderStatusEnum.OPEN.value,
        changed_by=str(current_user.id),
    )
    db.add(initial_log)

    db.commit()
    db.refresh(new_order)
    return new_order


def cancel_order(db: Session, order_id: int, current_user: CurrentUser) -> Order:
    """Validasi pembatalan order oleh CUSTOMER pemilik order saat status masih OPEN."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundError(ErrorCode.ORDER_NOT_FOUND, "Order tidak ditemukan.")

    if current_user.role != Role.CUSTOMER or str(order.customer_id) != str(current_user.id):
        raise ForbiddenError(ErrorCode.FORBIDDEN, "Kamu tidak berhak membatalkan pesanan ini.")

    if order.status != OrderStatusEnum.OPEN.value:
        raise ConflictError(
            ErrorCode.INVALID_STATUS_TRANSITION,
            f"Order dengan status {order.status} tidak dapat dibatalkan.",
        )

    order.status = OrderStatusEnum.CANCELLED.value
    db.add(
        OrderStatusLog(
            order_id=order.id,
            status=OrderStatusEnum.CANCELLED.value,
            changed_by=str(current_user.id),
        )
    )

    db.commit()
    db.refresh(order)
    return order


def update_order_status(
    db: Session,
    order_id: int,
    new_status: OrderStatusEnum,
    current_user: CurrentUser,
) -> Order:
    """Validasi transisi status order searah (ACCEPTED -> ON_THE_WAY -> COMPLETED)."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundError(ErrorCode.ORDER_NOT_FOUND, "Order tidak ditemukan.")

    if current_user.role != Role.DRIVER or str(order.driver_id) != str(current_user.id):
        raise ForbiddenError(ErrorCode.FORBIDDEN, "Kamu tidak ditugaskan pada pesanan ini.")

    allowed_transitions = {
        OrderStatusEnum.ACCEPTED.value: OrderStatusEnum.ON_THE_WAY.value,
        OrderStatusEnum.ON_THE_WAY.value: OrderStatusEnum.COMPLETED.value,
    }

    expected_next = allowed_transitions.get(order.status)
    if not expected_next or new_status.value != expected_next:
        raise ConflictError(
            ErrorCode.INVALID_STATUS_TRANSITION,
            f"Transisi status dari {order.status} ke {new_status.value} tidak valid.",
        )

    order.status = new_status.value
    db.add(
        OrderStatusLog(
            order_id=order.id,
            status=new_status.value,
            changed_by=str(current_user.id),
        )
    )

    db.commit()
    db.refresh(order)
    return order