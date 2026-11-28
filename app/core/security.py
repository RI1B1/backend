"""Autentikasi dan otorisasi yang dipakai semua modul.

Dependency yang tersedia (semua memvalidasi ke DATABASE, bukan hanya isi token):

  get_current_user        user dari token + cek ke DB: harus ada dan is_active.
                          Role yang dipakai adalah role di DB, BUKAN klaim di token.
  require_role(*roles)    get_current_user + role harus salah satu dari `roles`.
  require_approved_driver get_current_user + punya driver_applications berstatus APPROVED.

Pembuatan token login ada di modul auth (Sava); fungsi create_access_token disediakan di sini.
Tidak ada SSO/Google di MVP (D-013) dan tidak ada refresh token.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import DriverApplicationStatus
from app.core.errors import ErrorCode, ForbiddenError, UnauthorizedError
from app.db.session import get_db
from app.modules.drivers.models import DriverApplication
from app.modules.users.models import User


class Role(str, Enum):
    ADMIN = "ADMIN"
    DRIVER = "DRIVER"
    CUSTOMER = "CUSTOMER"


@dataclass
class CurrentUser:
    id: int
    role: Role


bearer_scheme = HTTPBearer(auto_error=False)


def create_access_token(user_id: int, role: Role, expires_minutes: int | None = None) -> str:
    """Buat JWT. `role` hanya informasi untuk Frontend; Backend selalu membaca role dari DB."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes if expires_minutes is not None else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": str(user_id), "role": role.value, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> CurrentUser:
    """Decode token saja (tanpa DB). Dipakai internal oleh get_current_user."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return CurrentUser(id=int(payload["sub"]), role=Role(payload["role"]))
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError(ErrorCode.TOKEN_EXPIRED, "Sesi sudah berakhir, silakan login lagi.")
    except (jwt.InvalidTokenError, KeyError, ValueError, TypeError):
        raise UnauthorizedError(ErrorCode.INVALID_TOKEN, "Token tidak valid.")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> CurrentUser:
    if credentials is None:
        raise UnauthorizedError()
    token_user = decode_access_token(credentials.credentials)

    user = db.get(User, token_user.id)
    if user is None:
        raise UnauthorizedError(ErrorCode.INVALID_TOKEN, "Token tidak valid.")
    if not user.is_active:
        raise ForbiddenError(ErrorCode.USER_SUSPENDED, "Akun kamu dinonaktifkan.")
    try:
        role = Role(user.role)
    except ValueError:
        raise ForbiddenError()
    return CurrentUser(id=user.id, role=role)


def require_role(*roles: Role):
    """Pakai: current_user: CurrentUser = Depends(require_role(Role.ADMIN))"""

    def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise ForbiddenError()
        return user

    return dependency


def require_approved_driver(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CurrentUser:
    """Hanya pengguna dengan pengajuan Driver berstatus APPROVED (PRD 6.2, aturan bisnis #3).

    Sumber kebenarannya adalah tabel driver_applications, bukan kolom users.role,
    sehingga Driver PENDING atau REJECTED tidak pernah lolos walau role-nya berubah.
    """
    approved_id = db.scalar(
        select(DriverApplication.id)
        .where(
            DriverApplication.user_id == user.id,
            DriverApplication.status == DriverApplicationStatus.APPROVED.value,
        )
        .limit(1)
    )
    if approved_id is None:
        raise ForbiddenError(ErrorCode.DRIVER_NOT_APPROVED, "Akun kamu belum disetujui sebagai Driver.")
    return user
