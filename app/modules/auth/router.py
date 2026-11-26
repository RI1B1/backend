"""Endpoint Auth sesuai Master API Reference v1.3 bagian 4.

Catatan format: Master API memakai respons "polos" (tanpa pembungkus {success, data}),
jadi router ini mengembalikan model langsung, tidak lewat ok(). Lihat catatan serah terima
tentang perbedaan ini dengan app/core/response.py.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.modules.auth import service
from app.modules.auth.schemas import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=RegisterResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Daftar akun baru dengan email @mail.ugm.ac.id. Role otomatis CUSTOMER. Akses: publik."""
    return service.register(db, payload.name, payload.email, payload.password)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Login dengan email dan password. Akses: publik."""
    return service.login(db, payload.email, payload.password)


@router.get("/me", response_model=UserOut)
def me(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """Profil dasar pengguna yang sedang login. Akses: semua pengguna login."""
    return service.get_me(db, current_user.id)
