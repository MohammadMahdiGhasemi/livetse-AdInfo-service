from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import jwt
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.jwks import JwksError, jwks_client
from app.shared.enums import normalize_data_tier

logger = logging.getLogger(__name__)
_optional_bearer = HTTPBearer(auto_error=False)


def _coerce_bool(value) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    return None


@dataclass(frozen=True)
class CurrentUser:
    id: str
    phoneNumber: Optional[str] = None
    dataTier: Optional[str] = None
    role: Optional[str] = None
    liveTreadAccess: Optional[bool] = None
    userDataGroup: Optional[str] = None
    device: Optional[str] = None
    iat: Optional[int] = None
    exp: Optional[int] = None



def _unauthorized(detail: str = "Invalid token") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def _verification_key(token: str):
    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as exc:
        raise _unauthorized() from exc

    if header.get("alg") != "RS256":
        logger.info("Rejected JWT with unexpected alg=%r", header.get("alg"))
        raise _unauthorized()

    if settings.JWT_JWKS_URL:
        kid = str(header.get("kid") or "").strip()
        if not kid:
            raise _unauthorized()
        try:
            return await jwks_client.get_key(kid)
        except JwksError as exc:
            # Do not disclose key infrastructure details to the caller.
            logger.warning("JWT key resolution failed: %s", str(exc))
            raise _unauthorized() from exc

    static_key = settings.jwt_static_public_key
    if static_key:
        return static_key

    logger.error("JWT verification key is not configured")
    raise _unauthorized()


async def _decode_jwt(token: str) -> CurrentUser:
    key = await _verification_key(token)

    required_claims = ["id"]
    if settings.JWT_REQUIRE_EXP:
        required_claims.append("exp")

    options = {"require": required_claims}
    decode_kwargs = {
        "key": key,
        "algorithms": ["RS256"],
        "leeway": settings.JWT_LEEWAY_SECONDS,
        "options": options,
    }
    if settings.JWT_ISSUER:
        decode_kwargs["issuer"] = settings.JWT_ISSUER
    if settings.JWT_AUDIENCE:
        decode_kwargs["audience"] = settings.JWT_AUDIENCE
    else:
        decode_kwargs["options"] = {**options, "verify_aud": False}

    try:
        payload = jwt.decode(token, **decode_kwargs)
    except jwt.ExpiredSignatureError as exc:
        raise _unauthorized("Token expired") from exc
    except jwt.InvalidTokenError as exc:
        logger.info("JWT validation failed: %s", exc.__class__.__name__)
        raise _unauthorized() from exc

    user_id = str(payload.get("id") or "").strip()
    if not user_id:
        raise _unauthorized()

    role = payload.get("role")
    normalized_role = str(role).strip().upper() if role is not None else None

    return CurrentUser(
        id=user_id,
        phoneNumber=payload.get("phoneNumber"),
        dataTier=normalize_data_tier(payload.get("dataTier")),
        role=normalized_role or None,
        liveTreadAccess=_coerce_bool(payload.get("liveTreadAccess")),
        userDataGroup=payload.get("userDataGroup"),
        device=payload.get("device"),
        iat=payload.get("iat"),
        exp=payload.get("exp"),
    )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_optional_bearer),
) -> Optional[CurrentUser]:
    """Optional bearer auth: missing header => anonymous, invalid token => 401."""
    if credentials is None:
        return None
    return await _decode_jwt(credentials.credentials)


async def require_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_optional_bearer),
) -> CurrentUser:
    if credentials is None:
        raise _unauthorized("Authorization header required")
    return await _decode_jwt(credentials.credentials)
