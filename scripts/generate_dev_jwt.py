from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Allow `python scripts/generate_dev_jwt.py` from the project root without
# requiring PYTHONPATH to be set manually.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import jwt

from app.core.config import settings


def main() -> None:
    if settings.APP_ENV != "development":
        raise SystemExit("APP_ENV must be 'development' to generate a development JWT")
    if not settings.DEV_JWT_ENABLED:
        raise SystemExit("DEV_JWT_ENABLED must be true")
    if not settings.DEV_JWT_SECRET:
        raise SystemExit("DEV_JWT_SECRET is not configured")

    now = datetime.now(timezone.utc)
    payload = {
        "id": settings.DEV_JWT_USER_ID,
        "role": settings.DEV_JWT_ROLE.upper(),
        "iss": settings.DEV_JWT_ISSUER,
        "aud": settings.DEV_JWT_AUDIENCE,
        "iat": now,
        "exp": now + timedelta(days=settings.DEV_JWT_TTL_DAYS),
        "device": "SWAGGER",
    }

    token = jwt.encode(
        payload,
        settings.DEV_JWT_SECRET,
        algorithm="HS256",
        headers={"kid": settings.DEV_JWT_KID},
    )

    print(token)


if __name__ == "__main__":
    main()
