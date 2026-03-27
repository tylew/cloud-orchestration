"""MCP context and formatter unit tests."""

import json
import os
from unittest.mock import patch


def test_get_tenant_id_from_env():
    """get_tenant_id() returns DEV_TENANT_ID env var value when set."""
    with patch.dict(os.environ, {"DEV_TENANT_ID": "test-tenant-123"}):
        from packages.mcp.context import get_tenant_id
        assert get_tenant_id() == "test-tenant-123"


def test_get_tenant_id_fallback():
    """get_tenant_id() returns fallback 'dev-local' when env var unset."""
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("DEV_TENANT_ID", None)
        from packages.mcp.context import get_tenant_id
        assert get_tenant_id() == "dev-local"


def test_get_current_user_returns_current_user():
    """get_current_user() returns CurrentUser with tenant_id from env."""
    with patch.dict(os.environ, {"DEV_TENANT_ID": "user-abc"}):
        from packages.mcp.context import get_current_user
        user = get_current_user()
        assert user.tenant_id == "user-abc"
        assert user.email is not None
        assert user.display_name is not None
        assert user.is_admin is True


def test_format_json_response():
    """format_json_response(data) returns valid JSON string."""
    from packages.mcp.tools.formatters import format_json_response
    data = {"key": "value", "count": 42}
    result = format_json_response(data)
    parsed = json.loads(result)
    assert parsed == data


def test_format_error():
    """format_error(error_type, message) returns JSON with error_type and message keys."""
    from packages.mcp.tools.formatters import format_error
    result = format_error("not_found", "Project not found")
    parsed = json.loads(result)
    assert parsed["error_type"] == "not_found"
    assert parsed["message"] == "Project not found"
