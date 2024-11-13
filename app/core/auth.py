from datetime import datetime, timedelta
from typing import Union, List, TYPE_CHECKING
from functools import wraps
import jwt
import logging
from flask import request, g
from werkzeug.security import generate_password_hash, check_password_hash

from app.core.exceptions import APIError
from app.models.responses.auth import TokenResponse
from app.core.config import settings
from app.models.enums import UserRole
from app.core.db import get_session
from app.services.auth import AuthService, Auth

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.models.user import User  # Import User model for type checking only


def has_required_roles(user: 'User', required_roles: Union[List[str], str]) -> bool:
    """Check if user has any of the required roles"""
    if not required_roles:
        return True

    if isinstance(required_roles, str):
        required_roles = [required_roles]

    user_role = UserRole(user.role)  # Convert string to enum
    return any(user_role == UserRole(role) for role in required_roles)


def require_roles(*roles: UserRole):
    """Decorator to require specific roles"""
    def decorator(f):
        # Store required roles on the function
        f._roles = [role.value for role in roles]  # Store string values

        @wraps(f)
        def decorated(*args, **kwargs):
            if not hasattr(g, 'user') or not has_required_roles(g.user, f._roles):
                raise APIError(
                    message="Insufficient permissions",
                    code="AUTH_INSUFFICIENT_PERMISSIONS",
                    status_code=403
                )
            return f(*args, **kwargs)
        return decorated
    return decorator


def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        logger.debug(f"Auth header: {auth_header!r}")
        if not auth_header:
            raise APIError(
                message="Missing authorization header",
                code="AUTH_MISSING_TOKEN",
                status_code=401
            )

        try:
            # Only split the header - specific ValueError case
            token_type, token = auth_header.split(' ', 1)
            logger.debug(f"Token type: {token_type!r}, Token: {token[:10]}...")
            if token_type.lower() != 'bearer':
                raise APIError(
                    message="Invalid token type",
                    code="AUTH_INVALID_TOKEN_TYPE",
                    status_code=401
                )

            db = next(get_session())
            auth_service = AuthService(db)
            user = auth_service.validate_token(token)

            g.user = user
            g.user_id = user.id

            # Let other exceptions propagate normally
            return f(*args, **kwargs)

        except ValueError as e:
            if "split" in str(e):  # Only catch header splitting errors
                logger.error(f"Header parsing error: {str(e)}")
                raise APIError(
                    message="Invalid authorization header format",
                    code="AUTH_INVALID_HEADER",
                    status_code=401
                )
            raise  # Let other ValueErrors propagate

    return decorated


def optional_auth(f):
    """Decorator that attempts to authenticate but doesn't require it"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return f(*args, **kwargs)

        try:
            token_type, token = auth_header.split()
            if token_type.lower() != 'bearer':
                return f(*args, **kwargs)

            db = next(get_session())
            auth_service = AuthService(db)
            user = auth_service.validate_token(token)

            g.user = user
            g.user_id = user.id

        except (ValueError, jwt.PyJWTError):
            pass  # Silently fail on auth errors

        return f(*args, **kwargs)
    return decorated
