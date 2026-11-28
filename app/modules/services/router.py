from fastapi import APIRouter

router = APIRouter(prefix="/services", tags=["Services"])

# TODO (services): tambahkan endpoint di sini. Logika bisnis taruh di service.py.
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response import ok
from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.modules.services.service import get_all_services

router = APIRouter(prefix="/services", tags=["Services"])


@router.get("")
def list_services(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    services = get_all_services(db)
    return ok({"services": services})