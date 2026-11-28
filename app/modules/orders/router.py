from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from app.core.pagination import PageParams
from app.core.security import (
    CurrentUser,
    Role,
    get_current_user,
    require_approved_driver,
    require_role,
)
from app.db.session import get_db
from app.modules.orders import service
from app.modules.orders.schemas import (
    OrderAcceptResponse,
    OrderCreate,
    OrderListResponse,
    OrderStatusUpdate,
)

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get(
    "/available",
    response_model=OrderListResponse,
)
def get_available_orders(
    params: PageParams = Depends(),
    db: Session = Depends(get_db),
    _user: CurrentUser = Depends(require_approved_driver),
):
    return service.get_available_orders(db, params.page, params.limit)


@router.post(
    "/{order_id}/accept",
    response_model=OrderAcceptResponse,
    response_model_exclude={"meta"},
)
def accept_order(
    order_id: int = Path(gt=0),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_approved_driver),
):
    return service.accept_order(db, order_id, user)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreate,
    user: CurrentUser = Depends(require_role(Role.CUSTOMER)),
    db: Session = Depends(get_db),
):
    return service.create_order(db, user.id, payload)


@router.get("/my")
def get_my_orders(
    user: CurrentUser = Depends(require_role(Role.CUSTOMER)),
    db: Session = Depends(get_db),
):
    return service.get_my_orders(db, user.id)


@router.patch("/{order_id}/status")
def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    user: CurrentUser = Depends(require_role(Role.DRIVER)),
    approved_driver: CurrentUser = Depends(require_approved_driver),
    db: Session = Depends(get_db),
):
    return {
        "message": "Status order berhasil diperbarui",
        "order": service.update_order_status(db, order_id, user.id, payload.status),
    }


@router.post("/{order_id}/cancel")
def cancel_order(
    order_id: int,
    user: CurrentUser = Depends(require_role(Role.CUSTOMER)),
    db: Session = Depends(get_db),
):
    return {
        "message": "Order berhasil dibatalkan",
        "order": service.cancel_order(db, order_id, user.id),
    }


@router.get("/{order_id}/status-history")
def get_order_status_history(
    order_id: int,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.get_order_status_history(db, order_id, user)


@router.get("/{order_id}")
def get_order(
    order_id: int,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.get_order(db, order_id, user)
