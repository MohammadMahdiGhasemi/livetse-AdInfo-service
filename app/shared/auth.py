import logging
from typing import Optional
from dataclasses import dataclass

from fastapi import Header, HTTPException, status
import jwt

from app.core.config import settings
from app.shared.enums import normalize_data_tier

logger = logging.getLogger(__name__)


def _coerce_bool(value) -> Optional[bool]:
    """Defensive coercion: JWTs that arrived as 'True'/'False' strings
    (issued by older services) are normalized to real booleans. Anything
    unrecognisable becomes None."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"true", "1", "yes"}:
            return True
        if v in {"false", "0", "no"}:
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
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}"
        )

    return CurrentUser(
        id=str(payload.get("id", "")),
        phoneNumber=payload.get("phoneNumber"),
        # dataTier is the new normalization point — uppercase it here so
        # downstream SQL comparisons don't have to defend against mixed case.
        dataTier=normalize_data_tier(payload.get("dataTier")),
        liveTreadAccess=_coerce_bool(payload.get("liveTreadAccess")),
        userDataGroup=payload.get("userDataGroup"),
        device=payload.get("device"),
        # NOTE: payload 'role' is intentionally not read.
    )


async def get_current_user(authorization: Optional[str] = Header(None)) -> Optional[CurrentUser]:
    """Optional JWT dependency — returns None if no header provided.

    Use `require_current_user` for endpoints that demand a valid JWT."""
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "").strip()
    if not token:
        return None
    return _decode_jwt(token)


async def require_current_user(authorization: Optional[str] = Header(None)) -> CurrentUser:
    """Mandatory JWT dependency — raises 401 if missing/invalid."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
        )
    token = authorization.replace("Bearer ", "").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
        )
    return _decode_jwt(token)
