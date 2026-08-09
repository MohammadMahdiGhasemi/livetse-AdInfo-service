import logging
from dataclasses import dataclass
from typing import Optional

import jwt
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
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


@dataclass
class CurrentUser:
    id: str
    phoneNumber: Optional[str] = None
    dataTier: Optional[str] = None
    liveTreadAccess: Optional[bool] = None
    userDataGroup: Optional[str] = None
    device: Optional[str] = None


def _decode_jwt(token: str) -> CurrentUser:
    options = {"require": ["exp"]} if settings.JWT_REQUIRE_EXP else None
    decode_kwargs = {
        "key": settings.JWT_SECRET,
        "algorithms": [settings.JWT_ALGORITHM],
        "leeway": settings.JWT_LEEWAY_SECONDS,
        "options": options,
    }
    if settings.JWT_ISSUER:
        decode_kwargs["issuer"] = settings.JWT_ISSUER
    if settings.JWT_AUDIENCE:
        decode_kwargs["audience"] = settings.JWT_AUDIENCE
    else:
        # Do not reject a token merely because another service includes an aud
        # claim when this service has no configured audience contract yet.
        decode_kwargs["options"] = {
            **(options or {}),
            "verify_aud": False,
        }

    try:
        payload = jwt.decode(token, **decode_kwargs)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidTokenError as exc:
        logger.info("JWT validation failed: %s", exc.__class__.__name__)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_id = str(payload.get("id") or "").strip()
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return CurrentUser(
        id=user_id,
        phoneNumber=payload.get("phoneNumber"),
        dataTier=normalize_data_tier(payload.get("dataTier")),
        liveTreadAccess=_coerce_bool(payload.get("liveTreadAccess")),
        userDataGroup=payload.get("userDataGroup"),
        device=payload.get("device"),
    )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_optional_bearer),
) -> Optional[CurrentUser]:
    """Optional bearer auth: missing header => anonymous, invalid token => 401."""
    if credentials is None:
        return None
    return _decode_jwt(credentials.credentials)


async def require_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_optional_bearer),
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _decode_jwt(credentials.credentials)
