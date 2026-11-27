from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.core.pagination import PageParams
from app.core.security import CurrentUser, require_approved_driver
from app.db.session import get_db

from . import service
from .schemas import OrderAcceptResponse, OrderListResponse

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
