from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Anterin Dong API"
    APP_ENV: str = "development"
    API_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "postgresql+psycopg2://anterin:anterin@db:5432/anterin_dong"

    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    # MVP tanpa refresh token, jadi access token berlaku 8 jam.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    ALLOWED_EMAIL_DOMAIN: str = "mail.ugm.ac.id"

    @model_validator(mode="after")
    def ensure_jwt_secret(self):
        """JWT_SECRET kosong di development -> pakai nilai sementara.
        Di luar development (staging/production) -> app menolak start."""
        if not self.JWT_SECRET.strip():
            if self.APP_ENV == "development":
                self.JWT_SECRET = "dev-only-change-me-dev-only-change-me"
            else:
                raise ValueError("JWT_SECRET wajib diisi di .env")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
