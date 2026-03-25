"""Integration tests for env-scoped secret API endpoints."""

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def test_project(api_client, test_prefix):
    """Create a real project and return its ref_id. Cleanup after."""
    project_data = {
        "project_id": "my-super-cool-app-dev-3f74d0",
        "display_name": f"Secrets Test {test_prefix}",
        "region": "us-central1",
    }
    resp = api_client.post("/api/projects", json=project_data)
    assert resp.status_code == 200
    created = resp.json()
    ref_id = created.get("id")
    yield ref_id
    api_client.delete(f"/api/projects/{ref_id}")


class TestSecretAPI:
    def test_create_list_get_version_destroy_delete(self, api_client, test_prefix, test_project):
        env = "dev"
        secret_id = f"{test_prefix}-api-sec"
        prefix = f"/api/projects/{test_project}/envs/{env}/secrets"

        # Create
        resp = api_client.post(prefix, json={
            "secret_id": secret_id,
            "value": "api-test-value-123456",
            "description": "API test secret",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["secret_id"] == secret_id

        try:
            # List
            list_resp = api_client.get(prefix)
            assert list_resp.status_code == 200
            secrets = list_resp.json()["secrets"]
            ids = [s["secret_id"] for s in secrets]
            assert secret_id in ids

            # Get with versions
            get_resp = api_client.get(f"{prefix}/{secret_id}")
            assert get_resp.status_code == 200
            detail = get_resp.json()
            assert detail["secret_id"] == secret_id
            assert "versions" in detail

            # Add version
            ver_resp = api_client.put(f"{prefix}/{secret_id}", json={"value": "updated-value-654321"})
            assert ver_resp.status_code == 200

            # List versions
            ver_list_resp = api_client.get(f"{prefix}/{secret_id}/versions")
            assert ver_list_resp.status_code == 200
            versions = ver_list_resp.json()["versions"]
            assert len(versions) >= 2

            # Destroy version 1
            del_ver_resp = api_client.delete(f"{prefix}/{secret_id}/versions/1")
            assert del_ver_resp.status_code == 200
            assert del_ver_resp.json()["status"] == "destroyed"

            # Delete secret
            del_resp = api_client.delete(f"{prefix}/{secret_id}")
            assert del_resp.status_code == 200
            assert del_resp.json()["status"] == "destroyed"
        except Exception:
            api_client.delete(f"{prefix}/{secret_id}")
            raise

    def test_create_missing_secret_id(self, api_client, test_project):
        prefix = f"/api/projects/{test_project}/envs/dev/secrets"
        resp = api_client.post(prefix, json={"value": "something"})
        assert resp.status_code == 422

    def test_add_version_missing_value(self, api_client, test_project):
        prefix = f"/api/projects/{test_project}/envs/dev/secrets/nonexistent"
        resp = api_client.put(prefix, json={})
        assert resp.status_code == 422
