"""
backend/api/auth.py
====================
JWT authentication endpoints with Argon2 password hashing.

Endpoints:
    POST /api/auth/login   — authenticates user, sets HttpOnly cookie, returns user metadata
    POST /api/auth/logout  — clears HttpOnly cookie
    GET  /api/auth/me      — returns profile of currently authenticated user

Security features:
  - Argon2id password hashing via argon2-cffi (RFC 9106 standard).
  - HS256 signed JWT via PyJWT with configurable expiration.
  - HttpOnly cookie transport to protect against XSS token theft.
  - Generic authentication errors to prevent username enumeration.
  - Dummy verification on unknown users to prevent timing analysis.
"""

import json
import logging
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
import jwt

from backend.api.dependencies import ALGORITHM, SECRET_KEY, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Authentication"])

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))  # 8 hours
COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"
USERS_FILE = Path(__file__).resolve().parents[2] / "data" / "users.json"

ph = PasswordHasher()

# Dummy argon2 hash for constant-time comparison when username does not exist
_DUMMY_ARGON2_HASH = ph.hash("dummy_constant_time_salt_password_xyz")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class LoginPayload(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: str


# ---------------------------------------------------------------------------
# User persistence helpers
# ---------------------------------------------------------------------------

def _load_users() -> list:
    if not USERS_FILE.exists():
        return []
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Auth: failed to load users.json: %s", exc)
        return []


def _save_users(users: list) -> None:
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)


def _get_user(email: str) -> Optional[dict]:
    clean_email = email.strip().lower()
    for u in _load_users():
        if u.get("email", "").strip().lower() == clean_email:
            return u
    return None


def _verify_password(plain: str, hashed: str) -> bool:
    try:
        return ph.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
    except Exception as exc:
        logger.warning("Auth: password verify error: %s", exc)
        return False


def _hash_password(plain: str) -> str:
    return ph.hash(plain)


def _create_access_token(data: dict) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload["exp"] = expire
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ---------------------------------------------------------------------------
# Initial user provisioning
# ---------------------------------------------------------------------------

def ensure_users_initialized() -> None:
    """
    Provision default ADMIN and VIEWER accounts if users.json is missing
    or contains invalid placeholder hashes.
    """
    existing = _load_users()
    has_valid_argon2 = (
        len(existing) > 0
        and all(u.get("hashed_password", "").startswith("$argon2") for u in existing)
    )

    if has_valid_argon2:
        logger.info("Auth: users.json loaded with %d valid account(s).", len(existing))
        return

    logger.info("Auth: Initializing default accounts with Argon2 password hashing...")

    admin_email = os.getenv("ADMIN_EMAIL", "official@thermalx.gov.in")
    admin_pass = os.getenv("ADMIN_PASSWORD", "ThermalX@123")
    viewer_email = os.getenv("VIEWER_EMAIL", "viewer@thermalx.gov.in")
    viewer_pass = os.getenv("VIEWER_PASSWORD", "Viewer@123")

    users = [
        {
            "email": admin_email,
            "hashed_password": _hash_password(admin_pass),
            "role": "ADMIN",
            "name": "Admin Official",
            "initials": "AS",
        },
        {
            "email": viewer_email,
            "hashed_password": _hash_password(viewer_pass),
            "role": "VIEWER",
            "name": "Viewer Analyst",
            "initials": "VR",
        },
    ]
    _save_users(users)
    logger.info("Auth: initialized accounts for %s", [u["email"] for u in users])


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/auth/login")
async def login(
    request: Request,
    response: Response,
):
    """
    Authenticate user via credentials.
    Supports either JSON body or application/x-www-form-urlencoded.
    Sets HttpOnly 'access_token' cookie and returns user metadata.
    """
    username = ""
    password = ""

    # Parse JSON or form data
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
            username = body.get("username") or body.get("email") or ""
            password = body.get("password") or ""
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON body")
    else:
        form = await request.form()
        username = form.get("username") or form.get("email") or ""
        password = form.get("password") or ""

    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username/email and password are required",
        )

    user = _get_user(str(username))

    # Constant-time verification
    hashed = user["hashed_password"] if user else _DUMMY_ARGON2_HASH
    is_valid = _verify_password(str(password), hashed)

    if not user or not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Please try again.",
        )

    token = _create_access_token({
        "sub": user["email"],
        "role": user["role"].upper(),
        "name": user["name"],
        "initials": user.get("initials", ""),
    })

    # Set HttpOnly cookie
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=COOKIE_SECURE,
        path="/",
    )

    return {
        "status": "authenticated",
        "user": {
            "email": user["email"],
            "name": user["name"],
            "role": user["role"].upper(),
            "initials": user.get("initials", ""),
        },
        "token_type": "bearer",
    }


@router.post("/auth/logout")
async def logout(response: Response):
    """Clear HttpOnly access_token cookie."""
    response.delete_cookie(key="access_token", path="/")
    return {"status": "logged_out", "detail": "Session ended successfully"}


@router.get("/auth/me")
async def me(current_user: dict = Depends(get_current_user)):
    """Return profile of the authenticated user validated from the JWT cookie."""
    return {
        "email": current_user["email"],
        "name": current_user["name"],
        "role": current_user["role"],
        "initials": current_user.get("initials", ""),
    }
