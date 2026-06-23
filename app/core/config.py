# config.py
import os
import sys
from pathlib import Path
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent


APP_NAME = os.getenv("APP_NAME", "test")
ENV_FILE_PATH = BASE_DIR / f".env.{APP_NAME}"

if not ENV_FILE_PATH.exists():
    print(f"[ERROR] Environment file not found at {ENV_FILE_PATH}", file=sys.stderr)
else:
    load_dotenv(dotenv_path=ENV_FILE_PATH, override=True)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE_PATH),
        env_file_encoding="utf-8",
        extra="ignore"  
    )

    REDIS_URL: str
    DATABASE_URL: str
    BASE_URL: str
    DATABASE_NAME: Optional[str] = None

    # ---- Admin panel (sqladmin) ----
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str
    SECRET_KEY: Optional[str] = None

    # ---- Upload Service ----
    UPLOAD_SERVICE_URL: str
    UPLOAD_SERVICE_API_KEY: str
    BANNERS_UPLOAD_FOLDER: str = "banners"

    @field_validator("DATABASE_URL", "BASE_URL", mode="before")
    @classmethod
    def _strip_whitespace(cls, v):
        # مقادیر env گاهی فاصله‌ی ابتدایی دارند (مثل "DATABASE_URL= postgres...")
        return v.strip() if isinstance(v, str) else v

try:
    settings = Settings()
    print(f"[OK] Settings loaded successfully for {APP_NAME} from {ENV_FILE_PATH.name}")
except Exception as e:
    print(f"[ERROR] Failed to load settings: {e}", file=sys.stderr)
    print(f"   Make sure your .env file is correct and exists at: {ENV_FILE_PATH}", file=sys.stderr)
    print("   Required keys include ADMIN_PASSWORD (and ideally SECRET_KEY).", file=sys.stderr)
    sys.exit(1)


if not settings.SECRET_KEY:
    import secrets as _secrets
    settings.SECRET_KEY = _secrets.token_urlsafe(48)
    print(
        "[WARN] SECRET_KEY is not set - generated a temporary one. "
        "Admin sessions will reset on every restart.",
        file=sys.stderr,
    )


