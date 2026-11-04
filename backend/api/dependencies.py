"""
backend/api/dependencies.py
============================
Shared FastAPI dependency functions for authentication and authorization.

Reads the JWT access token from:
1. The HttpOnly 'access_token' cookie set at login (primary transport).
2. The 'Authorization: Bearer <token>' header as a standard fallback.

Does NOT accept tokens in URL query parameters.

Usage:
    from backend.api.dependencies import get_current_user, require_role

    @router.get("/protected")
    async def endpoint(user: dict = Depends(get_current_user)):
        ...

    @router.post("/admin-only")
    async def admin_endpoint(user: dict = Depends(require_role("ADMIN"))):
        ...

    @router.get("/viewer-or-admin")
    async def shared_endpoint(user: dict = Depends(require_role("ADMIN", "VIEWER"))):
        ...
"""

import logging
import os
from typing import Optional

from fastapi import Cookie, Depends, HTTPException, Request, status
import jwt
from jwt.exceptions import PyJWTError, ExpiredSignatureError, InvalidTokenError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Settings — shared with auth.py
# ---------------------------------------------------------------------------

SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "thermalx-sih2026-jwt-secret-change-in-production-please")
ALGORITHM: str = "HS256"


# ---------------------------------------------------------------------------
# Core dependency: get_current_user
# ---------------------------------------------------------------------------

def get_current_user(
    request: Request,
    access_token: Optional[str] = Cookie(None),
) -> dict:
    """
    Validate the JWT from either:
    1. HttpOnly 'access_token' cookie
    2. 'Authorization: Bearer <token>' header

    Returns:
        dict with keys: email, role, name, initials

    Raises:
        HTTP 401 — if token is missing, invalid, or expired.
    """
    token = access_token

    # Header fallback
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub", "")
        role: str = payload.get("role", "")
        name: str = payload.get("name", "")
        initials: str = payload.get("initials", "")

        if not email or not role:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except (InvalidTokenError, PyJWTError) as exc:
        logger.debug("JWT decode failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return {"email": email, "role": role.upper(), "name": name, "initials": initials}


# ---------------------------------------------------------------------------
# Role enforcement: require_role
# ---------------------------------------------------------------------------

def require_role(*allowed_roles: str):
    """
    Factory that returns a FastAPI dependency enforcing role-based access.

    Args:
        *allowed_roles: One or more role strings (case-insensitive), e.g. "ADMIN", "VIEWER".

    Returns:
        HTTP 403 if the authenticated user's role is not in allowed_roles.
        Otherwise returns the user dict.
    """
    allowed_upper = {r.upper() for r in allowed_roles}

    def _checker(user: dict = Depends(get_current_user)) -> dict:
        if user["role"].upper() not in allowed_upper:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(allowed_roles)}",
            )
        return user

    return _checker
