import logging
import secrets
from typing import Optional

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

logger = logging.getLogger(__name__)
_admin_bearer = HTTPBearer(auto_error=False)


async def verify_admin_authorization(
    credentials: Optional[HTTPAuthorizationCredentials],
):
    """Validate the admin bearer secret using constant-time comparison."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if credentials.scheme.lower() != "bearer" or not secrets.compare_digest(
        credentials.credentials,
        settings.ADMIN_PASSWORD,
    ):
        logger.warning("Invalid admin authorization attempt")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid authorization",
        )
    return credentials.credentials


async def require_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_admin_bearer),
):
    return await verify_admin_authorization(credentials)
