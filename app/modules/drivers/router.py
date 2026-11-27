from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.pagination import PageParams
from app.core.security import (
    CurrentUser,
    get_current_user,
    require_approved_driver,
)
from app.db.session import get_db

from . import service
from .schemas import (
    DriverAvailabilityResponse,
    DriverApplicationCreate,
    DriverApplicationResponse,
    DriverOrderHistoryResponse,
)

router = APIRouter(prefix="/driver", tags=["Driver"])


@router.post(
    "/applications",
    status_code=status.HTTP_201_CREATED,
    response_model=DriverApplicationResponse,
)
def create_application(
    payload: DriverApplicationCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    return service.create_application(db, user, payload.application_note)


@router.get("/application", response_model=DriverApplicationResponse)
def get_application(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    return service.get_application(db, user)


@router.post("/availability/toggle", response_model=DriverAvailabilityResponse)
def toggle_availability(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_approved_driver),
):
    return service.toggle_availability(db, user)


@router.get("/orders/history", response_model=DriverOrderHistoryResponse)
def get_order_history(
    params: PageParams = Depends(),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_approved_driver),
):
    return service.get_history(db, user, params.page, params.limit)
