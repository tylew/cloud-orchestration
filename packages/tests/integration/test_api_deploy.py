"""API layered tests — full deploy pipeline (crown jewel)."""

import os
import time
import pytest

pytestmark = pytest.mark.integration

skip_deploy = os.environ.get("SKIP_DEPLOY_TEST", "").lower() in ("true", "1")


@pytest.mark.skipif(skip_deploy, reason="SKIP_DEPLOY_TEST is set")
class TestDeployPipeline:
    @pytest.mark.timeout(300)
    def test_full_deploy_flow(self, api_client, test_prefix, sample_envelope_data, sample_project_data):
        # Create project with per-env GCP fields
        create_resp = api_client.post("/api/projects", json=sample_project_data)
        assert create_resp.status_code == 200
        created = create_resp.json()
        project_ref_id = created.get("id")
        assert project_ref_id, f"Expected 'id' in create response, got: {created}"

        try:
            save_resp = api_client.put(
                f"/api/projects/{project_ref_id}/envs/dev/blueprint",
                json=sample_envelope_data,
            )
            assert save_resp.status_code == 200

            deploy_resp = api_client.post(
                f"/api/projects/{project_ref_id}/envs/dev/deploy",
            )
            assert deploy_resp.status_code in (200, 202)
            deploy_data = deploy_resp.json()
            deploy_id = deploy_data.get("deploy_id") or deploy_data.get("id")

            if deploy_id:
                for _ in range(48):
                    status_resp = api_client.get(
                        f"/api/projects/{project_ref_id}/deploys/{deploy_id}/status"
                    )
                    if status_resp.status_code == 200:
                        status = status_resp.json().get("status", "")
                        if status in ("success", "completed", "failed", "error"):
                            break
                    time.sleep(5)
        finally:
            api_client.delete(f"/api/projects/{project_ref_id}")
