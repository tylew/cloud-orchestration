"""MCP context, formatter, and tool unit tests."""

import json
import os
from unittest.mock import patch


# ── Context and Formatter Tests ──────────────────────────────


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


# ── Tool Logic Tests (pure functions, no store dependencies) ─


def test_list_projects_returns_formatted_list():
    """list_projects tool returns formatted list of projects."""
    from packages.mcp.tools.projects import _list_projects_impl
    mock_projects = [
        {"id": "proj-1", "display_name": "Project One", "provision_status": "ready"},
        {"id": "proj-2", "display_name": "Project Two", "provision_status": "pending"},
    ]
    result = _list_projects_impl(mock_projects)
    assert "Project One" in result
    assert "Project Two" in result
    assert "proj-1" in result


def test_get_project_status_returns_state():
    """get_project_status tool returns project state with env info and actions."""
    from packages.mcp.tools.projects import _get_project_status_impl
    project = {
        "id": "proj-1",
        "display_name": "My Project",
        "environments": [
            {"name": "dev", "gcp_project_id": "dev-proj", "provision_status": "ready"},
        ],
    }
    validation = {"errors": 0, "warnings": 1}
    nodes = [{"name": "svc", "type": "cloud_run"}]
    result = _get_project_status_impl(project, "dev", validation, nodes)
    parsed = json.loads(result)
    assert parsed["project_name"] == "My Project"
    assert parsed["node_count"] == 1
    assert "actions" in parsed


def test_get_blueprint_returns_formatted():
    """get_blueprint tool returns formatted blueprint with node count."""
    from packages.mcp.tools.blueprint import _get_blueprint_impl
    nodes = [
        {"slug": "vpc-1", "name": "my-vpc", "type": "vpc"},
        {"slug": "svc-1", "name": "my-svc", "type": "cloud_run"},
    ]
    result = _get_blueprint_impl(nodes)
    parsed = json.loads(result)
    assert parsed["node_count"] == 2
    assert len(parsed["nodes"]) == 2


def test_validate_blueprint_returns_results():
    """validate_blueprint tool returns validation results with counts."""
    from packages.mcp.tools.blueprint import _validate_blueprint_impl
    issues = [
        {"severity": "error", "node": "svc-1", "message": "Missing image"},
        {"severity": "warning", "node": "svc-1", "message": "CPU not set"},
    ]
    result = _validate_blueprint_impl(issues)
    parsed = json.loads(result)
    assert parsed["valid"] is False
    assert parsed["error_count"] == 1
    assert parsed["warning_count"] == 1


def test_preview_terraform_returns_files():
    """preview_terraform tool returns generated Terraform file list."""
    from packages.mcp.tools.blueprint import _preview_terraform_impl
    tf_files = {
        "vpc.tf": 'resource "google_compute_network" "my_vpc" {}',
        "cloud_run.tf": 'resource "google_cloud_run_v2_service" "my_svc" { very long content }',
    }
    result = _preview_terraform_impl(tf_files)
    parsed = json.loads(result)
    assert parsed["file_count"] == 2
    assert "vpc.tf" in parsed["files"]


def test_tool_errors_return_structured_json():
    """Tool errors return structured JSON with isError pattern."""
    from packages.mcp.tools.formatters import format_error
    result = format_error("validation_error", "Blueprint has 3 errors", details={"errors": 3})
    parsed = json.loads(result)
    assert parsed["error_type"] == "validation_error"
    assert parsed["message"] == "Blueprint has 3 errors"
    assert parsed["details"]["errors"] == 3
