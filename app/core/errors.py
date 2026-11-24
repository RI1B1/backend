"""Error code, exception aplikasi, dan handler global.

Cara pakai di service:  raise NotFoundError(ErrorCode.ORDER_NOT_FOUND, "Pesanan tidak ditemukan.")
Error code baru ditambah lewat PR (jangan membuat string liar di service).
"""
from enum import Enum

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.response import fail


class ErrorCode(str, Enum):
    # umum
    BAD_REQUEST = "BAD_REQUEST"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    CONFLICT = "CONFLICT"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    # auth / user
    EMAIL_DOMAIN_NOT_ALLOWED = "EMAIL_DOMAIN_NOT_ALLOWED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    USER_SUSPENDED = "USER_SUSPENDED"
    # order
    ORDER_NOT_FOUND = "ORDER_NOT_FOUND"
    ORDER_ALREADY_TAKEN = "ORDER_ALREADY_TAKEN"
    INVALID_STATUS_TRANSITION = "INVALID_STATUS_TRANSITION"
    SERVICE_NOT_FOUND = "SERVICE_NOT_FOUND"
    LOCATION_NOT_FOUND = "LOCATION_NOT_FOUND"
    # chat
    CHAT_CLOSED = "CHAT_CLOSED"


class AppException(Exception):
    status_code = 400

    def __init__(self, code: ErrorCode | str, message: str, details=None, status_code: int | None = None):
        self.code = code.value if isinstance(code, ErrorCode) else code
        self.message = message
        self.details = details
        if status_code is not None:
            self.status_code = status_code
        super().__init__(message)


class BadRequestError(AppException):
    status_code = 400

    def __init__(self, code=ErrorCode.BAD_REQUEST, message="Permintaan tidak valid.", details=None):
        super().__init__(code, message, details)


class UnauthorizedError(AppException):
    status_code = 401

    def __init__(self, code=ErrorCode.UNAUTHORIZED, message="Silakan login terlebih dahulu."):
        super().__init__(code, message)


class ForbiddenError(AppException):
    status_code = 403

    def __init__(self, code=ErrorCode.FORBIDDEN, message="Kamu tidak punya akses ke sini."):
        super().__init__(code, message)


class NotFoundError(AppException):
    status_code = 404

    def __init__(self, code=ErrorCode.NOT_FOUND, message="Data tidak ditemukan."):
        super().__init__(code, message)


class ConflictError(AppException):
    status_code = 409

    def __init__(self, code=ErrorCode.CONFLICT, message="Terjadi konflik data."):
        super().__init__(code, message)


_HTTP_CODE_MAP = {
    400: ErrorCode.BAD_REQUEST,
    401: ErrorCode.UNAUTHORIZED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    405: ErrorCode.METHOD_NOT_ALLOWED,
    409: ErrorCode.CONFLICT,
}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(status_code=exc.status_code, content=fail(exc.code, exc.message, exc.details))

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        code = _HTTP_CODE_MAP.get(exc.status_code, ErrorCode.BAD_REQUEST).value
        return JSONResponse(status_code=exc.status_code, content=fail(code, str(exc.detail)))

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        details = [
            {"field": ".".join(str(p) for p in err["loc"][1:]) or str(err["loc"][0]), "message": err["msg"]}
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=fail(ErrorCode.VALIDATION_ERROR.value, "Data yang dikirim tidak valid.", details),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content=fail(ErrorCode.INTERNAL_ERROR.value, "Terjadi kesalahan pada server."),
        )
