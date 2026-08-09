import logging

from fastapi import Depends, HTTPException, status

from app.core.config import settings
from app.shared.auth import CurrentUser, require_current_user

logger = logging.getLogger(__name__)


async def require_admin(
    current_user: CurrentUser = Depends(require_current_user),
) -> CurrentUser:
    """Authorize admin routes from the verified JWT role claim."""
    role = (current_user.role or "").upper()
    if role not in settings.admin_roles:
        logger.warning(
            "Admin authorization denied user_id=%s role=%s",
            current_user.id,
            role or None,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return current_user
