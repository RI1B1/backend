from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

# Modul core/db (sesuaikan lokasi get_db dan get_current_user di repository Anda)
from app.db.session import get_db
from app.core.security import get_current_user

# Absolute import untuk User dari modules
from app.modules.users.models import User

# Relative import untuk skema dan service chat internal
from .schemas import ChatMessageCreate, ChatMessageResponse
from . import service

router = APIRouter(prefix="/orders", tags=["Chat"])


@router.get(
    "/{order_id}/messages",
    response_model=List[ChatMessageResponse],
    status_code=status.HTTP_200_OK,
    summary="Mengambil daftar pesan chat pesanan",
)
def get_messages(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.get_order_messages(db, order_id, current_user)


@router.post(
    "/{order_id}/messages",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Mengirim pesan chat baru",
)
def send_message(
    order_id: int,
    payload: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return service.send_order_message(db, order_id, current_user, payload)
