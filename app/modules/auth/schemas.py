"""Schema Pydantic (request/response) modul auth.

Bentuk data mengikuti Master API Reference v1.3 bagian 4 (Authentication API).
"""
from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    # Role sengaja tidak ada: pengguna baru selalu CUSTOMER, ditentukan Backend.
    # Field tambahan (mis. "role") di request diabaikan oleh Pydantic.
    # Format/domain email dan kekuatan password diperiksa di service.
    name: str = Field(min_length=1, max_length=100)  # 100 = panjang kolom users.name
    email: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str  # CUSTOMER | DRIVER | ADMIN


class RegisterResponse(BaseModel):
    message: str
    user: UserOut


class LoginResponse(BaseModel):
    message: str
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # detik
    user: UserOut