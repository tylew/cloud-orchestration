"""Debug API endpoint tests — verify raw state inspection routes (AGT-12)."""

import os
import pytest
from unittest.mock import patch, MagicMock

# Ensure auth bypass before importing app
os.environ["AUTH_DISABLED"] = "true"
os.environ["ENVIRONMENT"] = "dev"
os.environ["DEV_TENANT_ID"] = "test-tenant-uid"
os.environ["DEV_USER_EMAIL"] = "dev@test.com"
os.environ["DEV_USER_DISPLAY_NAME"] = "Test Dev"

from fastapi.testclient import TestClient
from packages.api.main import app

client = TestClient(app)

# Common test data
_PROJECT_REF = "test-project-ref-123"
_TENANT_ID = "test-tenant-uid"


@pytest.fixture(autouse=True)
def mock_project_lookup():
    """Mock find_project_for_user so auth/authz doesn't hit Firestore."""
    project = {
        "id": _PROJECT_REF,
        "display_name": "Test Project",
        "environments": [{"name": "dev"}],
        "collaborators": {},
    }
    with patch("packages.platform.auth.authz.find_project_for_user", return_value=(project, _TENANT_ID)):
        yield


class TestDebugState:
    """GET /api/debug/{project_ref_id}/state"""

    @patch("packages.api.handlers.debug.project_store")
    def test_returns_project_doc(self, mock_store):
        mock_store.get_project.return_value = {
            "id": _PROJECT_REF,
            "display_name": "My Project",
            "environments": [{"name": "dev"}],
        }
        resp = client.get(f"/api/debug/{_PROJECT_REF}/state")
        assert resp.status_code == 200
        data = resp.json()
        assert data["display_name"] == "My Project"

    @patch("packages.api.handlers.debug.project_store")
    def test_returns_404_when_missing(self, mock_store):
        mock_store.get_project.return_value = None
        resp = client.get(f"/api/debug/{_PROJECT_REF}/state")
        assert resp.status_code == 404


class TestDebugValidation:
    """GET /api/debug/{project_ref_id}/{env_name}/validation"""

    @patch("packages.api.handlers.debug.blueprint_store")
    def test_returns_validation_doc(self, mock_store):
        mock_store.get_validation_doc.return_value = {
            "valid": True, "issues": [], "checked_at": "2026-03-27T00:00:00Z"
        }
        resp = client.get(f"/api/debug/{_PROJECT_REF}/dev/validation")
        assert resp.status_code == 200
        assert resp.json()["valid"] is True

    @patch("packages.api.handlers.debug.blueprint_store")
    def test_returns_empty_when_no_validation(self, mock_store):
        mock_store.get_validation_doc.return_value = None
        resp = client.get(f"/api/debug/{_PROJECT_REF}/dev/validation")
        assert resp.status_code == 200
        assert resp.json() == {"valid": None, "issues": []}


class TestDebugTerraform:
    """GET /api/debug/{project_ref_id}/{env_name}/terraform"""

    @patch("packages.api.handlers.debug.generate_terraform")
    @patch("packages.api.handlers.debug.blueprint_store")
    def test_returns_compiled_tf(self, mock_bp, mock_gen):
        mock_bp.get_env_blueprint.return_value = {
            "env": "dev",
            "envelope": {
                "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
                "nodes": [{"name": "vpc", "type": "vpc", "config": {"auto_create_subnetworks": False}}],
            },
        }
        mock_gen.return_value = {"main.tf": "resource ...", "provider.tf": "provider ..."}
        resp = client.get(f"/api/debug/{_PROJECT_REF}/dev/terraform")
        assert resp.status_code == 200
        data = resp.json()
        assert "main.tf" in data["files"]

    @patch("packages.api.handlers.debug.blueprint_store")
    def test_returns_empty_when_no_blueprint(self, mock_bp):
        mock_bp.get_env_blueprint.return_value = None
        resp = client.get(f"/api/debug/{_PROJECT_REF}/dev/terraform")
        assert resp.status_code == 200
        assert resp.json()["files"] == {}


class TestDebugDeploys:
    """GET /api/debug/{project_ref_id}/deploys"""

    @patch("packages.api.handlers.debug.deploy_store")
    def test_returns_deploy_list(self, mock_store):
        mock_store.list_deploys.return_value = [
            {"id": "d1", "status": "success", "env_name": "dev"},
            {"id": "d2", "status": "failed", "env_name": "dev"},
        ]
        resp = client.get(f"/api/debug/{_PROJECT_REF}/deploys")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["deploys"]) == 2


class TestDebugNodeStatus:
    """GET /api/debug/{project_ref_id}/{env_name}/nodes/status"""

    @patch("packages.api.handlers.debug.deploy_store")
    @patch("packages.api.handlers.debug.blueprint_store")
    def test_returns_node_status_list(self, mock_bp, mock_deploy):
        mock_bp.list_nodes.return_value = [
            {"slug": "my-vpc", "name": "my-vpc", "type": "vpc", "config": {}},
            {"slug": "my-sa", "name": "my-sa", "type": "service_account", "config": {}},
        ]
        mock_deploy.get_node_deploy_status_doc.return_value = {
            "nodes": {
                "my-vpc": {"deployed_version": "v1", "deployed_at": "2026-03-27T00:00:00Z"},
            }
        }
        resp = client.get(f"/api/debug/{_PROJECT_REF}/dev/nodes/status")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["nodes"]) == 2
        # my-vpc has deploy status, my-sa does not
        vpc_node = next(n for n in data["nodes"] if n["slug"] == "my-vpc")
        assert vpc_node["deployed_version"] == "v1"
        sa_node = next(n for n in data["nodes"] if n["slug"] == "my-sa")
        assert sa_node["deployed_version"] is None
