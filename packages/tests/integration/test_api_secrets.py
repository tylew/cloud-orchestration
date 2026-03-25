"""Integration tests for env-scoped secret API endpoints."""

import pytest

pytestmark = pytest.mark.integration


class TestSecretAPI:
    def test_create_list_get_version_destroy_delete(self, api_client, test_prefix):
        env = "dev"
        secret_id = f"{test_prefix}-api-sec"
        # Use a dummy project_ref_id — authz will resolve via dev user
        prefix = f"/api/projects/test-proj/envs/{env}/secrets"

        # Create
        resp = api_client.post(prefix, json={
            "secret_id": secret_id,
            "value": "api-test-value-123456",
            "description": "API test secret",
        })
        if resp.status_code == 404:
            pytest.skip("Test project not found — need project setup for API tests")

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

    def test_create_missing_secret_id(self, api_client):
        resp = api_client.post("/api/projects/test-proj/envs/dev/secrets", json={"value": "something"})
        if resp.status_code == 404:
            pytest.skip("Test project not found")
        assert resp.status_code == 422

    def test_add_version_missing_value(self, api_client):
        resp = api_client.put("/api/projects/test-proj/envs/dev/secrets/nonexistent", json={})
        if resp.status_code == 404:
            pytest.skip("Test project not found")
        assert resp.status_code == 422
