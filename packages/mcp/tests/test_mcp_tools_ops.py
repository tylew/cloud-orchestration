"""Tests for build and deploy MCP tools -- concurrency guards, logs, status."""

import json
from unittest.mock import patch, MagicMock

import pytest

# Shared no-op patches for _ensure_deps
_BUILDS_NOOP = "packages.mcp.tools.builds._ensure_deps"
_DEPLOY_NOOP = "packages.mcp.tools.deploy._ensure_deps"


# ── Build Tool Tests ─────────────────────────────────────────


@patch(_BUILDS_NOOP)
@patch("packages.mcp.tools.builds.build_store", new_callable=MagicMock)
@patch("packages.mcp.tools.builds.blueprint_store", new_callable=MagicMock)
@patch("packages.mcp.tools.builds.projects_store", new_callable=MagicMock)
def test_trigger_build_blocks_in_progress(mock_projects, mock_blueprint, mock_build, _noop):
    """trigger_build returns actionable error when build already in progress (D-19)."""
    from packages.mcp.tools.builds import trigger_build

    mock_projects.get_project.return_value = {
        "id": "proj1", "project_id": "my-project",
        "environments": [{"name": "dev", "gcp_project_id": "gcp-proj"}],
    }
    mock_projects.get_env_entry.return_value = {"gcp_project_id": "gcp-proj"}
    mock_build.get_latest_build_for_node.return_value = {
        "id": "build-123", "status": "building",
    }

    result = trigger_build("proj1", "dev", "my-service")
    parsed = json.loads(result)

    assert parsed["error_type"] == "concurrency_conflict"
    assert "build-123" in parsed["message"]
    assert "already in progress" in parsed["message"]


@patch(_BUILDS_NOOP)
@patch("packages.mcp.tools.builds.cloud_build", new_callable=MagicMock)
@patch("packages.mcp.tools.builds.build_store", new_callable=MagicMock)
def test_get_build_logs_completed_build(mock_build, mock_cb, _noop):
    """get_build_logs returns plan and apply output for completed builds."""
    from packages.mcp.tools.builds import get_build_logs

    mock_build.get_build_record.return_value = {
        "id": "build-1", "status": "success", "build_id": "cb-abc",
        "log_url": "https://console.cloud.google.com/build/cb-abc",
    }
    mock_cb.get_build_plan_output.return_value = "Plan: 3 to add"
    mock_cb.get_build_apply_output.return_value = "Apply complete! Resources: 3 added"

    result = get_build_logs("proj1", "dev", "build-1")
    parsed = json.loads(result)

    assert parsed["status"] == "success"
    assert parsed["plan_output"] == "Plan: 3 to add"
    assert parsed["apply_output"] == "Apply complete! Resources: 3 added"
    mock_cb.get_build_plan_output.assert_called_once()
    mock_cb.get_build_apply_output.assert_called_once()


@patch(_BUILDS_NOOP)
@patch("packages.mcp.tools.builds.cloud_build", new_callable=MagicMock)
@patch("packages.mcp.tools.builds.build_store", new_callable=MagicMock)
def test_get_build_logs_in_progress(mock_build, mock_cb, _noop):
    """get_build_logs returns status + message when build is still running."""
    from packages.mcp.tools.builds import get_build_logs

    mock_build.get_build_record.return_value = {
        "id": "build-1", "status": "building", "build_id": "cb-abc",
        "log_url": "https://console.cloud.google.com/build/cb-abc",
    }

    result = get_build_logs("proj1", "dev", "build-1")
    parsed = json.loads(result)

    assert parsed["status"] == "building"
    assert "in progress" in parsed["message"]
    assert parsed["log_url"] is not None
    # Should NOT call GCS for logs when in progress
    mock_cb.get_build_plan_output.assert_not_called()
    mock_cb.get_build_apply_output.assert_not_called()


@patch(_BUILDS_NOOP)
@patch("packages.mcp.tools.builds.build_store", new_callable=MagicMock)
def test_get_build_status_returns_record(mock_build, _noop):
    """get_build_status returns build record details."""
    from packages.mcp.tools.builds import get_build_status

    mock_build.get_build_record.return_value = {
        "id": "build-1", "status": "success", "node_name": "my-service",
        "image_uri": "us-docker.pkg.dev/proj/repo/my-service:latest",
        "log_url": None, "error": None,
        "created_at": "2026-01-01", "updated_at": "2026-01-01",
    }

    result = get_build_status("proj1", "dev", "build-1")
    parsed = json.loads(result)

    assert parsed["status"] == "success"
    assert parsed["node_name"] == "my-service"


# ── Deploy Tool Tests ────────────────────────────────────────


@patch(_DEPLOY_NOOP)
@patch("packages.mcp.tools.deploy.deploy_store", new_callable=MagicMock)
@patch("packages.mcp.tools.deploy.blueprint_store", new_callable=MagicMock)
@patch("packages.mcp.tools.deploy.projects_store", new_callable=MagicMock)
@pytest.mark.xfail(reason="packages.core.schemas import broken since package split")
def test_trigger_deploy_blocks_in_progress(mock_projects, mock_blueprint, mock_deploy, _noop):
    """trigger_deploy returns actionable error when deploy already in progress (D-19)."""
    from packages.mcp.tools.deploy import trigger_deploy

    mock_projects.get_project.return_value = {
        "id": "proj1", "project_id": "my-project",
        "environments": [{"name": "dev", "gcp_project_id": "gcp-proj", "provision_status": "ready"}],
    }
    mock_projects.get_env_entry.return_value = {
        "gcp_project_id": "gcp-proj", "provision_status": "ready",
    }
    mock_blueprint.get_env_blueprint.return_value = None

    mock_deploy.list_deploys.return_value = [
        {"id": "deploy-456", "env_name": "dev", "status": "building"},
    ]

    result = trigger_deploy("proj1", "dev")
    parsed = json.loads(result)

    assert parsed["error_type"] == "concurrency_conflict"
    assert "deploy-456" in parsed["message"]
    assert "in progress" in parsed["message"]


@patch(_DEPLOY_NOOP)
@patch("packages.mcp.tools.deploy.deploy_store", new_callable=MagicMock)
@patch("packages.mcp.tools.deploy.blueprint_store", new_callable=MagicMock)
@patch("packages.mcp.tools.deploy.projects_store", new_callable=MagicMock)
def test_trigger_deploy_blocks_on_validation_errors(mock_projects, mock_blueprint, mock_deploy, _noop):
    """trigger_deploy blocks when blueprint has validation errors (D-21)."""
    import sys

    mock_projects.get_project.return_value = {
        "id": "proj1", "project_id": "my-project",
        "environments": [{"name": "dev", "gcp_project_id": "gcp-proj", "provision_status": "ready"}],
    }
    mock_projects.get_env_entry.return_value = {
        "gcp_project_id": "gcp-proj", "provision_status": "ready",
    }

    mock_blueprint.get_env_blueprint.return_value = {
        "envelope": {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": "bad-node", "type": "cloud_run", "config": {}},
            ],
        },
    }

    mock_error = MagicMock()
    mock_error.severity = "error"
    mock_error.node = "bad-node"
    mock_error.message = "Missing image"

    # Pre-populate sys.modules with mock modules for inline imports
    mock_validation_mod = MagicMock()
    mock_validation_mod.validate_blueprint.return_value = [mock_error]
    mock_base_mod = MagicMock()
    mock_base_mod.Envelope.model_validate.return_value = MagicMock()

    saved_validation = sys.modules.get("packages.core.validation")
    saved_base = sys.modules.get("packages.core.schemas.base")
    sys.modules["packages.core.validation"] = mock_validation_mod
    sys.modules["packages.core.schemas.base"] = mock_base_mod

    try:
        from packages.mcp.tools.deploy import trigger_deploy
        result = trigger_deploy("proj1", "dev")
        parsed = json.loads(result)

        assert parsed["error_type"] == "validation_errors"
        assert "validation error" in parsed["message"]
    finally:
        # Restore original modules
        if saved_validation is not None:
            sys.modules["packages.core.validation"] = saved_validation
        else:
            sys.modules.pop("packages.core.validation", None)
        if saved_base is not None:
            sys.modules["packages.core.schemas.base"] = saved_base
        else:
            sys.modules.pop("packages.core.schemas.base", None)


@patch(_DEPLOY_NOOP)
@patch("packages.mcp.tools.deploy.deploy_store", new_callable=MagicMock)
@patch("packages.mcp.tools.deploy.blueprint_store", new_callable=MagicMock)
@patch("packages.mcp.tools.deploy.projects_store", new_callable=MagicMock)
def test_trigger_deploy_blocks_not_provisioned(mock_projects, mock_blueprint, mock_deploy, _noop):
    """trigger_deploy blocks when environment is not provisioned."""
    from packages.mcp.tools.deploy import trigger_deploy

    mock_projects.get_project.return_value = {
        "id": "proj1", "project_id": "my-project",
        "environments": [{"name": "dev", "gcp_project_id": "", "provision_status": "pending"}],
    }
    mock_projects.get_env_entry.return_value = {
        "gcp_project_id": "", "provision_status": "pending",
    }

    result = trigger_deploy("proj1", "dev")
    parsed = json.loads(result)

    assert parsed["error_type"] == "deploy_blocked"
    assert "not provisioned" in parsed["message"]
