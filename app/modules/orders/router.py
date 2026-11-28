from fastapi import APIRouter

router = APIRouter(prefix="/orders", tags=["Orders"])

# TODO (orders): tambahkan endpoint di sini. Logika bisnis taruh di service.py.
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.response import ok
from app.core.security import CurrentUser, Role, get_current_user, require_role
from app.db.session import get_db
from app.modules.orders.schemas import (
    OrderCreateRequest,
    OrderResponse,
    OrderStatusResponse,
    OrderStatusUpdateRequest,
)
from app.modules.orders.service import cancel_order, create_order, update_order_status

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_new_order(
    payload: OrderCreateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(Role.CUSTOMER)),
):
    order = create_order(db=db, payload=payload, current_user=current_user)
    return ok({
        "message": "Order berhasil dibuat",
        "order": OrderResponse.model_validate(order).model_dump(),
    })


@router.post("/{order_id}/cancel")
def cancel_existing_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role(Role.CUSTOMER)),
):
    order = cancel_order(db=db, order_id=order_id, current_user=current_user)
    return ok({
        "message": "Order berhasil dibatalkan",
        "order": OrderStatusResponse(id=order.id, status=order.status).model_dump(),
    })


@router.patch("/{order_id}/status")
def patch_order_status(
    order_id: int,
    payload: OrderStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    order = update_order_status(
        db=db,
        order_id=order_id,
        new_status=payload.status,
        current_user=current_user,
    )
    return ok({
        "message": "Status order berhasil diperbarui",
        "order": OrderStatusResponse(id=order.id, status=order.status).model_dump(),
    })