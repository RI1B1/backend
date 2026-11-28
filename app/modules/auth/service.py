"""Logika bisnis modul auth. Router hanya memanggil fungsi di sini."""
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import (
    AppException,
    ConflictError,
    ErrorCode,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
)
from app.core.password import hash_password, verify_password
from app.core.security import Role, create_access_token
from app.modules.auth.schemas import LoginResponse, RegisterResponse, UserOut
from app.modules.users.models import User

# Batas minimum password. Master API v1.3 hanya menulis "memenuhi ketentuan keamanan"
# tanpa angka, jadi nilai ini perlu disepakati tim (lihat catatan serah terima).
MIN_PASSWORD_LENGTH = 8

# Hash palsu untuk menyamakan waktu respons saat email tidak ditemukan, supaya
# penyerang tidak bisa menebak email mana yang terdaftar dari lama-cepatnya respons.
_DUMMY_HASH = hash_password("password-palsu-untuk-menyamakan-waktu")


def _validation_error(field: str, message: str) -> AppException:
    return AppException(
        ErrorCode.VALIDATION_ERROR,
        "Data yang dikirim tidak valid.",
        details=[{"field": field, "message": message}],
        status_code=422,
    )


def normalize_email(email: str) -> str:
    """Hapus spasi di tepi dan jadikan huruf kecil (email tidak case-sensitive)."""
    return email.strip().lower()


def validate_email_domain(email: str) -> None:
    """Pastikan email valid secara bentuk dan berdomain @mail.ugm.ac.id.

    Email harus sudah dinormalisasi. Domain diambil dari settings.ALLOWED_EMAIL_DOMAIN.
    """
    local, sep, domain = email.partition("@")
    if not sep or not local or not domain or "@" in domain or " " in email:
        raise _validation_error("email", "Format email tidak valid.")
    if domain != settings.ALLOWED_EMAIL_DOMAIN.lower():
        raise AppException(
            ErrorCode.EMAIL_DOMAIN_NOT_ALLOWED,
            f"Email harus menggunakan domain @{settings.ALLOWED_EMAIL_DOMAIN}.",
            status_code=422,
        )


def validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise _validation_error("password", f"Password minimal {MIN_PASSWORD_LENGTH} karakter.")


def to_user_out(user: User) -> UserOut:
    return UserOut(id=user.id, name=user.name, email=user.email, role=user.role)


def register(db: Session, name: str, email: str, password: str) -> RegisterResponse:
    """Daftarkan akun baru. Role selalu CUSTOMER dan tidak bisa ditentukan pengguna.

    Tidak membuat token dan tidak membuat Driver Application.
    """
    name = name.strip()
    if not name:
        raise _validation_error("name", "Nama wajib diisi.")
    email = normalize_email(email)
    validate_email_domain(email)
    validate_password(password)

    already = ConflictError(ErrorCode.CONFLICT, "Email sudah terdaftar.")
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise already

    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role=Role.CUSTOMER.value,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Dua request dengan email sama bersamaan: constraint unique di DB yang menang.
        db.rollback()
        raise already
    db.refresh(user)
    return RegisterResponse(message="Registrasi berhasil", user=to_user_out(user))


def login(db: Session, email: str, password: str) -> LoginResponse:
    """Login dengan email + password. Urutan pemeriksaan:

    1. Domain email (422)  2. Kredensial (401, pesan sama untuk email/password salah)
    3. Akun aktif (403)    4. Buat token.
    """
    email = normalize_email(email)
    validate_email_domain(email)

    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        verify_password(password, _DUMMY_HASH)  # samakan waktu respons
        raise UnauthorizedError(ErrorCode.INVALID_CREDENTIALS, "Email atau password salah.")
    if not verify_password(password, user.password_hash):
        raise UnauthorizedError(ErrorCode.INVALID_CREDENTIALS, "Email atau password salah.")

    # Dicek SETELAH password benar, agar status akun tidak bocor ke orang yang tidak punya password.
    if not user.is_active:
        raise ForbiddenError(ErrorCode.USER_SUSPENDED, "Akun kamu dinonaktifkan.")

    try:
        role = Role(user.role)
    except ValueError:
        raise ForbiddenError()

    return LoginResponse(
        message="Login berhasil",
        access_token=create_access_token(user.id, role),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=to_user_out(user),
    )


def get_me(db: Session, user_id: int) -> UserOut:
    """Profil dasar user yang sedang login (user_id berasal dari get_current_user)."""
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError(ErrorCode.USER_NOT_FOUND, "Pengguna tidak ditemukan.")
    return to_user_out(user)
