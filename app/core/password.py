from argon2 import PasswordHasher
from argon2.exceptions import (
    HashingError,
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)

password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Menghasilkan hash password menggunakan Argon2id."""
    return password_hasher.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    """Memverifikasi password dengan hash yang tersimpan."""
    try:
        return password_hasher.verify(
            hashed_password,
            plain_password
        )
    except (
        VerifyMismatchError,
        VerificationError,
        InvalidHashError,
        HashingError,
    ):
        return False
