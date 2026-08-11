from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BASE_DIR.parent


def _env_file() -> str | None:
    explicit = os.getenv("APP_ENV_FILE")
    if explicit:
        return str(Path(explicit).expanduser())

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
    APP_VERSION: str = "1.2.0"

    # Feature switches
    ENABLE_ANNOUNCEMENTS: bool = True
    ENABLE_BANNERS: bool = True
    ENABLE_ADS: bool = True
    ENABLE_UPLOADS: bool = True
    ENABLE_DOCS: Optional[bool] = None

    # Database
    DATABASE_URL: str
    DATABASE_NAME: Optional[str] = None
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    DB_ECHO: bool = False
    AUTO_CREATE_SCHEMA: bool = False
    HEALTH_READY_DB_CHECK_ENABLED: bool = True

    # Redis / rate limiting
    REDIS_ENABLED: bool = False
    REDIS_URL: Optional[str] = None
    REDIS_CONNECT_TIMEOUT: float = 2.0
    REDIS_SOCKET_TIMEOUT: float = 2.0
    REDIS_HEALTH_CHECK_INTERVAL: int = 30
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_BACKEND: Literal["memory", "redis"] = "memory"
    RATE_LIMIT_REQUESTS: int = 120
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_PREFIX: str = "promotion:ratelimit"
    RATE_LIMIT_FAIL_OPEN: bool = True
    RATE_LIMIT_EXEMPT_PATHS: str = "/health/live,/health/ready"

    # JWT verification
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

    # Upload service
    UPLOAD_SERVICE_URL: str
    UPLOAD_SERVICE_API_KEY: str
    UPLOAD_CONNECT_TIMEOUT: float = 5.0
    UPLOAD_READ_TIMEOUT: float = 60.0
    UPLOAD_MAX_CONNECTIONS: int = 50
    UPLOAD_MAX_KEEPALIVE_CONNECTIONS: int = 20
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_UPLOAD_CONTENT_TYPES: str = "image/jpeg,image/png,image/webp,image/gif"
    BANNERS_UPLOAD_FOLDER: str = "banners"
    ANNOUNCEMENTS_UPLOAD_FOLDER: str = "announcements"
    ADS_UPLOAD_FOLDER: str = "ads"

    # HTTP middleware
    ENABLE_REQUEST_CONTEXT: bool = True
    ENABLE_SECURITY_HEADERS: bool = True
    ENABLE_GZIP: bool = True
    GZIP_MINIMUM_SIZE: int = 1024
    ENABLE_CORS: bool = True
    CORS_ORIGINS: str = ""
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: str = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
    CORS_ALLOW_HEADERS: str = "Authorization,Content-Type,X-Request-ID"
    ENABLE_TRUSTED_HOSTS: bool = True
    TRUSTED_HOSTS: str = "*"

    # Logging
    LOG_ENABLED: bool = True
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True
    LOG_ACCESS_ENABLED: bool = True
    LOG_SQL_ENABLED: bool = False
    LOG_UVICORN_ACCESS_ENABLED: bool = False

    # Advertisement placement rules
    ADS_POSITION_CONFLICT_CHECK_ENABLED: bool = True
    ADS_MIN_POSITION: int = 1
    ADS_MAX_POSITION: int = 100

    BASE_URL: Optional[str] = None

    @field_validator(
        "DATABASE_URL", "BASE_URL", "UPLOAD_SERVICE_URL", "REDIS_URL",
        "JWT_JWKS_URL", "JWT_PUBLIC_KEY", "JWT_PUBLIC_KEY_PATH",
        "UPLOAD_SERVICE_API_KEY", mode="before",
    )
    @classmethod
    def _strip_whitespace(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator(
        "DB_POOL_SIZE", "DB_MAX_OVERFLOW", "DB_POOL_TIMEOUT", "DB_POOL_RECYCLE",
        "REDIS_HEALTH_CHECK_INTERVAL", "RATE_LIMIT_REQUESTS", "RATE_LIMIT_WINDOW_SECONDS",
        "GZIP_MINIMUM_SIZE", "UPLOAD_MAX_CONNECTIONS", "UPLOAD_MAX_KEEPALIVE_CONNECTIONS",
    )
    @classmethod
    def _validate_non_negative_ints(cls, value: int) -> int:
        if value < 0:
            raise ValueError("numeric runtime settings must be non-negative")
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
    def _validate_runtime(self) -> "Settings":
        if not self.DATABASE_URL.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must use the postgresql+asyncpg driver")
        if self.RATE_LIMIT_REQUESTS <= 0:
            raise ValueError("RATE_LIMIT_REQUESTS must be greater than zero")
        if self.RATE_LIMIT_WINDOW_SECONDS <= 0:
            raise ValueError("RATE_LIMIT_WINDOW_SECONDS must be greater than zero")
        if self.ADS_MIN_POSITION < 1 or self.ADS_MAX_POSITION < self.ADS_MIN_POSITION:
            raise ValueError("Invalid ADS_MIN_POSITION/ADS_MAX_POSITION range")

        if self.RATE_LIMIT_ENABLED and self.RATE_LIMIT_BACKEND == "redis":
            if not self.REDIS_ENABLED or not self.REDIS_URL:
                raise ValueError("Redis rate limiting requires REDIS_ENABLED=true and REDIS_URL")

        if self.APP_ENV == "production":
            if not (self.JWT_JWKS_URL or self.JWT_PUBLIC_KEY or self.JWT_PUBLIC_KEY_PATH):
                raise ValueError("Configure JWT_JWKS_URL, JWT_PUBLIC_KEY, or JWT_PUBLIC_KEY_PATH in production")
            if self.ENABLE_UPLOADS and (
                len(self.UPLOAD_SERVICE_API_KEY) < 16
                or self.UPLOAD_SERVICE_API_KEY == "dev-placeholder"
            ):
                raise ValueError("UPLOAD_SERVICE_API_KEY is not production-safe")
            if self.AUTO_CREATE_SCHEMA:
                raise ValueError("AUTO_CREATE_SCHEMA must be false in production; use Alembic migrations")
            if self.ENABLE_TRUSTED_HOSTS and "*" in self.trusted_hosts:
                raise ValueError("TRUSTED_HOSTS must be explicit in production")
            if self.ENABLE_CORS and "*" in self.cors_origins:
                raise ValueError("CORS_ORIGINS cannot contain '*' in production")
        return self

    @property
    def docs_enabled(self) -> bool:
        if self.ENABLE_DOCS is not None:
            return self.ENABLE_DOCS
        return self.APP_ENV != "production"

    @staticmethod
    def _csv(value: str) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()]

    @property
    def cors_origins(self) -> list[str]:
        return self._csv(self.CORS_ORIGINS)

    @property
    def cors_allow_methods(self) -> list[str]:
        return self._csv(self.CORS_ALLOW_METHODS)

    @property
    def cors_allow_headers(self) -> list[str]:
        return self._csv(self.CORS_ALLOW_HEADERS)

    @property
    def trusted_hosts(self) -> list[str]:
        return self._csv(self.TRUSTED_HOSTS) or ["*"]

    @property
    def rate_limit_exempt_paths(self) -> set[str]:
        return set(self._csv(self.RATE_LIMIT_EXEMPT_PATHS))

    @property
    def admin_roles(self) -> set[str]:
        return {item.upper() for item in self._csv(self.ADMIN_ROLES)}

    @property
    def jwt_static_public_key(self) -> str | None:
        if self.JWT_PUBLIC_KEY:
            return self.JWT_PUBLIC_KEY.replace("\\n", "\n").strip()
        if self.JWT_PUBLIC_KEY_PATH:
            return Path(self.JWT_PUBLIC_KEY_PATH).expanduser().read_text(encoding="utf-8").strip()
        return None

    @property
    def allowed_upload_content_types(self) -> set[str]:
        return {item.lower() for item in self._csv(self.ALLOWED_UPLOAD_CONTENT_TYPES)}


settings = Settings()
