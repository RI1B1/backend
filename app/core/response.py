"""Format respons standar. SEMUA endpoint wajib memakai helper di sini.

Sukses : {"success": true, "data": ..., "meta": {"page", "limit", "total"}}  (meta hanya untuk daftar)
Gagal  : {"success": false, "error": {"code": "...", "message": "...", "details": ...}}
"""
from typing import Any, Generic, Sequence, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Meta(BaseModel):
    page: int
    limit: int
    total: int


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    meta: Meta | None = None


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


def ok(data: Any = None) -> dict:
    """Respons sukses biasa."""
    return {"success": True, "data": data}


def paginated(items: Sequence[Any], page: int, limit: int, total: int) -> dict:
    """Respons sukses untuk daftar, lengkap dengan meta."""
    return {
        "success": True,
        "data": list(items),
        "meta": {"page": page, "limit": limit, "total": total},
    }


def fail(code: str, message: str, details: Any = None) -> dict:
    body: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        body["details"] = details
    return {"success": False, "error": body}
