"""Kerangka autentikasi yang dipakai semua modul.

Kerangka (Tech Lead BE) : Role, CurrentUser, get_current_user, require_role
Diisi lebih lanjut (Sava/Hafizh): login Google, refresh token, cek status user di database.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.errors import ErrorCode, ForbiddenError, UnauthorizedError


class Role(str, Enum):
    ADMIN = "ADMIN"
    DRIVER = "DRIVER"
    CUSTOMER = "CUSTOMER"


@dataclass
class CurrentUser:
    id: str
    role: Role


bearer_scheme = HTTPBearer(auto_error=False)


def create_access_token(user_id: str, role: Role, expires_minutes: int | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": str(user_id), "role": role.value, "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> CurrentUser:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return CurrentUser(id=payload["sub"], role=Role(payload["role"]))
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError(ErrorCode.TOKEN_EXPIRED, "Sesi sudah berakhir, silakan login lagi.")
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise UnauthorizedError(ErrorCode.INVALID_TOKEN, "Token tidak valid.")


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    if credentials is None:
        raise UnauthorizedError()
    return decode_access_token(credentials.credentials)


def require_role(*roles: Role):
    """Pakai: current_user: CurrentUser = Depends(require_role(Role.ADMIN))"""

    def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise ForbiddenError()
        return user

    return dependency
