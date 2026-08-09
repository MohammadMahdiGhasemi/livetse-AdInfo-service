from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BASE_DIR.parent


def _env_file() -> str | None:
    """Load a local env file only when it actually exists.

    Production deployments should inject environment variables through the
    orchestrator / secret store. APP_ENV_FILE can be used explicitly for local
    or staging runs without coupling the service to a hard-coded filename.
    """
    explicit = os.getenv("APP_ENV_FILE")
    if explicit:
        path = Path(explicit).expanduser()
        return str(path)

    app_env = os.getenv("APP_ENV", "development").strip().lower()
    candidates = (
        PROJECT_DIR / f".env.{app_env}",
        PROJECT_DIR / ".env",
        BASE_DIR / f".env.{app_env}",
        BASE_DIR / ".env",
    )
    for path in candidates:
        if path.exists():
            return str(path)
    return None


ENV_FILE_PATH = _env_file()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    APP_NAME: str = "livetse-promotion-service"
    APP_ENV: Literal["development", "test", "staging", "production"] = "development"
    APP_VERSION: str = "1.1.0"

    DATABASE_URL: str
    REDIS_URL: Optional[str] = None
    BASE_URL: Optional[str] = None
    DATABASE_NAME: Optional[str] = None

    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    AUTO_CREATE_SCHEMA: bool = False

    # Authentication: this service validates RS256 access tokens issued by
    # the identity service. Prefer JWKS for automatic key rotation. A static
    # public key/path is supported for environments where JWKS is unavailable.
    JWT_JWKS_URL: Optional[str] = None
    JWT_PUBLIC_KEY: Optional[str] = None
    JWT_PUBLIC_KEY_PATH: Optional[str] = None
    JWT_ISSUER: Optional[str] = None
    JWT_AUDIENCE: Optional[str] = None
    JWT_REQUIRE_EXP: bool = True
    JWT_LEEWAY_SECONDS: int = 10
    JWT_JWKS_CACHE_TTL_SECONDS: int = 300
    JWT_JWKS_CONNECT_TIMEOUT: float = 3.0
    JWT_JWKS_READ_TIMEOUT: float = 5.0
    ADMIN_ROLES: str = "ADMIN,SUPER_ADMIN"

    UPLOAD_SERVICE_URL: str
    UPLOAD_SERVICE_API_KEY: str
    UPLOAD_CONNECT_TIMEOUT: float = 5.0
    UPLOAD_READ_TIMEOUT: float = 60.0
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_UPLOAD_CONTENT_TYPES: str = "image/jpeg,image/png,image/webp,image/gif"
    BANNERS_UPLOAD_FOLDER: str = "banners"
    ANNOUNCEMENTS_UPLOAD_FOLDER: str = "announcements"
    ADS_UPLOAD_FOLDER: str = "ads"

    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True
    ENABLE_DOCS: Optional[bool] = None
    CORS_ORIGINS: str = ""
    TRUSTED_HOSTS: str = "*"

    @field_validator(
        "DATABASE_URL",
        "BASE_URL",
        "UPLOAD_SERVICE_URL",
        "JWT_JWKS_URL",
        "JWT_PUBLIC_KEY",
        "JWT_PUBLIC_KEY_PATH",
        "UPLOAD_SERVICE_API_KEY",
        mode="before",
    )
    @classmethod
    def _strip_whitespace(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("DB_POOL_SIZE", "DB_MAX_OVERFLOW", "DB_POOL_TIMEOUT", "DB_POOL_RECYCLE")
    @classmethod
    def _validate_non_negative_ints(cls, value: int) -> int:
        if value < 0:
            raise ValueError("database pool settings must be non-negative")
        return value


    @field_validator("JWT_JWKS_CACHE_TTL_SECONDS")
    @classmethod
    def _validate_jwks_cache_ttl(cls, value: int) -> int:
        if value < 30:
            raise ValueError("JWT_JWKS_CACHE_TTL_SECONDS must be at least 30")
        return value

    @field_validator("MAX_UPLOAD_SIZE_MB")
    @classmethod
    def _validate_upload_size(cls, value: int) -> int:
        if value <= 0 or value > 100:
            raise ValueError("MAX_UPLOAD_SIZE_MB must be between 1 and 100")
        return value

    @model_validator(mode="after")
    def _production_safety_checks(self) -> "Settings":
        if not self.DATABASE_URL.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must use the postgresql+asyncpg driver")

        if self.APP_ENV == "production":
            if not (self.JWT_JWKS_URL or self.JWT_PUBLIC_KEY or self.JWT_PUBLIC_KEY_PATH):
                raise ValueError("Configure JWT_JWKS_URL, JWT_PUBLIC_KEY, or JWT_PUBLIC_KEY_PATH in production")
            if len(self.UPLOAD_SERVICE_API_KEY) < 16 or self.UPLOAD_SERVICE_API_KEY == "dev-placeholder":
                raise ValueError("UPLOAD_SERVICE_API_KEY is not production-safe")
            if self.AUTO_CREATE_SCHEMA:
                raise ValueError("AUTO_CREATE_SCHEMA must be false in production; use Alembic migrations")
            if "*" in self.trusted_hosts:
                raise ValueError("TRUSTED_HOSTS must be explicit in production")
            if "*" in self.cors_origins:
                raise ValueError("CORS_ORIGINS cannot contain '*' in production")
        return self

    @property
    def docs_enabled(self) -> bool:
        if self.ENABLE_DOCS is not None:
            return self.ENABLE_DOCS
        return self.APP_ENV != "production"

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.CORS_ORIGINS.split(",") if item.strip()]

    @property
    def trusted_hosts(self) -> list[str]:
        hosts = [item.strip() for item in self.TRUSTED_HOSTS.split(",") if item.strip()]
        return hosts or ["*"]


    @property
    def admin_roles(self) -> set[str]:
        return {item.strip().upper() for item in self.ADMIN_ROLES.split(",") if item.strip()}

    @property
    def jwt_static_public_key(self) -> str | None:
        if self.JWT_PUBLIC_KEY:
            return self.JWT_PUBLIC_KEY.replace("\\n", "\n").strip()
        if self.JWT_PUBLIC_KEY_PATH:
            path = Path(self.JWT_PUBLIC_KEY_PATH).expanduser()
            return path.read_text(encoding="utf-8").strip()
        return None

    @property
    def allowed_upload_content_types(self) -> set[str]:
        return {
            item.strip().lower()
            for item in self.ALLOWED_UPLOAD_CONTENT_TYPES.split(",")
            if item.strip()
        }


settings = Settings()
