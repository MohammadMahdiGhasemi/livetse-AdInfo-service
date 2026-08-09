from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException

from conftest import TEST_PRIVATE_KEY
from app.core.security import require_admin
from app.shared.auth import CurrentUser, _decode_jwt


def _token(*, role="VIP", expires_in_minutes=5, alg="RS256"):
    now = datetime.now(timezone.utc)
    payload = {
        "id": "673b335fc932fc7671ee73d7",
        "phoneNumber": "09015111697",
        "dataTier": "GOLD",
        "role": role,
        "userDataGroup": "COMPLETE",
        "device": "DESKTOP",
        "iat": now,
        "exp": now + timedelta(minutes=expires_in_minutes),
    }
    key = TEST_PRIVATE_KEY if alg == "RS256" else "wrong-shared-secret-that-is-at-least-32-bytes-long"
    return jwt.encode(payload, key, algorithm=alg, headers={"kid": "test-key-1"})


@pytest.mark.asyncio
async def test_rs256_jwt_extracts_verified_user_claims():
    user = await _decode_jwt(_token())

    assert user.id == "673b335fc932fc7671ee73d7"
    assert user.phoneNumber == "09015111697"
    assert user.dataTier == "GOLD"
    assert user.role == "VIP"
    assert user.userDataGroup == "COMPLETE"
    assert user.device == "DESKTOP"
    assert user.exp is not None


@pytest.mark.asyncio
async def test_expired_jwt_is_rejected():
    with pytest.raises(HTTPException) as exc:
        await _decode_jwt(_token(expires_in_minutes=-1))
    assert exc.value.status_code == 401
    assert exc.value.detail == "Token expired"


@pytest.mark.asyncio
async def test_non_rs256_jwt_is_rejected_before_claims_are_trusted():
    with pytest.raises(HTTPException) as exc:
        await _decode_jwt(_token(alg="HS256"))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_admin_role_is_authorized_from_verified_user():
    user = CurrentUser(id="user-1", role="ADMIN")
    assert await require_admin(user) == user


@pytest.mark.asyncio
async def test_non_admin_role_is_forbidden():
    user = CurrentUser(id="user-1", role="VIP")
    with pytest.raises(HTTPException) as exc:
        await require_admin(user)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_jwks_mode_uses_kid_to_resolve_signing_key(monkeypatch):
    from conftest import TEST_PUBLIC_KEY
    from app.core.config import settings
    from app.shared import auth as auth_module

    seen = {}

    async def fake_get_key(kid: str):
        seen["kid"] = kid
        return TEST_PUBLIC_KEY

    monkeypatch.setattr(settings, "JWT_JWKS_URL", "https://auth.example.test/.well-known/jwks.json")
    monkeypatch.setattr(settings, "JWT_PUBLIC_KEY", None)
    monkeypatch.setattr(settings, "JWT_PUBLIC_KEY_PATH", None)
    monkeypatch.setattr(auth_module.jwks_client, "get_key", fake_get_key)

    user = await auth_module._decode_jwt(_token())

    assert seen["kid"] == "test-key-1"
    assert user.id == "673b335fc932fc7671ee73d7"
