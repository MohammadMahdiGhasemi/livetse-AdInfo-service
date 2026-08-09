from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.security import verify_admin_authorization
from app.shared.auth import _decode_jwt


@pytest.mark.asyncio
async def test_admin_auth_accepts_configured_secret():
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=settings.ADMIN_PASSWORD,
    )
    assert await verify_admin_authorization(credentials) == settings.ADMIN_PASSWORD


@pytest.mark.asyncio
async def test_admin_auth_rejects_wrong_secret():
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="wrong")
    with pytest.raises(HTTPException) as exc:
        await verify_admin_authorization(credentials)
    assert exc.value.status_code == 403


def test_jwt_requires_user_id_and_valid_expiry():
    token = jwt.encode(
        {
            "id": "user-1",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            "dataTier": "gold",
        },
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    user = _decode_jwt(token)
    assert user.id == "user-1"
    assert user.dataTier == "GOLD"


def test_expired_jwt_is_rejected():
    token = jwt.encode(
        {
            "id": "user-1",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    with pytest.raises(HTTPException) as exc:
        _decode_jwt(token)
    assert exc.value.status_code == 401
