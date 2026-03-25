"""Authentication middleware — Firebase token verification."""

import os
from dataclasses import dataclass

from fastapi import Request, HTTPException

_firebase_initialized = False


def _ensure_firebase():
    global _firebase_initialized
    if _firebase_initialized:
        return
    import firebase_admin
    firebase_admin.initialize_app()
    _firebase_initialized = True


@dataclass
class CurrentUser:
    tenant_id: str
    email: str
    display_name: str
    is_admin: bool = False


# Default dev tenant used when auth is disabled — configurable via env vars
_DEV_USER = CurrentUser(
    tenant_id=os.environ.get("DEV_TENANT_ID", "dev-local"),
    email=os.environ.get("DEV_USER_EMAIL", "dev@localhost"),
    display_name=os.environ.get("DEV_USER_DISPLAY_NAME", "Local Developer"),
    is_admin=os.environ.get("DEV_USER_IS_ADMIN", "true").lower() in ("true", "1", "yes"),
)


async def get_current_user(request: Request) -> CurrentUser:
    """FastAPI dependency that extracts the current user from the request.

    When AUTH_DISABLED=true (local dev), returns a default dev user.
    Otherwise, verifies a Firebase ID token from the Authorization header.
    """
    # Only allow AUTH_DISABLED in explicit development mode
    _auth_disabled = (
        os.environ.get("AUTH_DISABLED", "false").lower() in ("true", "1", "yes")
        and os.environ.get("ENVIRONMENT", "").lower() in ("dev", "development", "local", "")
    )
    if _auth_disabled:
        return _DEV_USER

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header[7:]

    _ensure_firebase()

    try:
        from firebase_admin import auth
        decoded = auth.verify_id_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    uid = decoded.get("uid", "")
    email = decoded.get("email", "")
    name = decoded.get("name", "")

    admin_emails = [e.strip() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()]
    is_admin = email in admin_emails

    return CurrentUser(tenant_id=uid, email=email, display_name=name, is_admin=is_admin)
