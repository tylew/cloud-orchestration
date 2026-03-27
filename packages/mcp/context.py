"""Tenant context for MCP server operations."""

import os
from dataclasses import dataclass


@dataclass
class CurrentUser:
    tenant_id: str
    email: str
    display_name: str
    is_admin: bool


def get_tenant_id() -> str:
    """Return the current tenant ID from env or fallback."""
    return os.environ.get("DEV_TENANT_ID", "dev-local")


def get_current_user() -> CurrentUser:
    """Return a CurrentUser for MCP operations (dev mode)."""
    return CurrentUser(
        tenant_id=get_tenant_id(),
        email=os.environ.get("DEV_USER_EMAIL", "dev@local"),
        display_name=os.environ.get("DEV_USER_DISPLAY_NAME", "Dev User"),
        is_admin=True,
    )
