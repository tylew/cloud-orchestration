"""API layered tests — project CRUD lifecycle."""

import os

import pytest

pytestmark = pytest.mark.integration


class TestProjectLifecycle:
    def test_create_list_delete(self, api_client, test_prefix):
        project_data = {
            "project_id": f"gcp-proj-{test_prefix}",
            "display_name": f"API Test {test_prefix}",
            "region": "us-central1",
        }
        create_resp = api_client.post("/api/projects", json=project_data)
        assert create_resp.status_code == 200
        created = create_resp.json()
        # The store returns the Firestore document ID as "id"
        project_ref_id = created.get("id")
        assert project_ref_id, f"Expected 'id' in create response, got: {created}"

        try:
            list_resp = api_client.get("/api/projects")
            assert list_resp.status_code == 200
            projects = list_resp.json()
            ids = [p.get("id") for p in projects]
            assert project_ref_id in ids

            delete_resp = api_client.delete(f"/api/projects/{project_ref_id}")
            assert delete_resp.status_code == 200

            list_resp2 = api_client.get("/api/projects")
            ids2 = [p.get("id") for p in list_resp2.json()]
            assert project_ref_id not in ids2
        except Exception:
            api_client.delete(f"/api/projects/{project_ref_id}")
            raise


class TestProjectEnvFields:
    def test_create_project_with_env_fields(self, api_client, test_prefix):
        """Verify projects can be created with per-env GCP fields."""
        gcp_project_id = os.environ.get("GCP_PROJECT_ID", "my-super-cool-app-dev-3f74d0")
        project_data = {
            "project_id": gcp_project_id,
            "display_name": f"Env Test {test_prefix}",
            "region": "us-central1",
            "environments": [{
                "id": "test-env-id",
                "name": "dev",
                "order": 0,
                "deployed": False,
                "deployed_at": None,
                "gcp_project_id": gcp_project_id,
                "tf_bucket": f"{gcp_project_id}-tfstate",
                "region": "us-central1",
                "provision_status": "ready",
                "provision_id": "",
            }],
        }
        create_resp = api_client.post("/api/projects", json=project_data)
        assert create_resp.status_code == 200
        created = create_resp.json()
        project_ref_id = created.get("id")

        try:
            # Verify env fields are stored
            get_resp = api_client.get(f"/api/projects/{project_ref_id}")
            assert get_resp.status_code == 200
            project = get_resp.json()
            envs = project.get("environments", [])
            assert len(envs) == 1
            env = envs[0]
            assert env["name"] == "dev"
            assert env["gcp_project_id"] == gcp_project_id
            assert env["tf_bucket"] == f"{gcp_project_id}-tfstate"
            assert env["provision_status"] == "ready"
        finally:
            api_client.delete(f"/api/projects/{project_ref_id}")
