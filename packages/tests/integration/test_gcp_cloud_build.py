"""Integration tests for Cloud Build submission and polling."""

import os
import pytest
from google.cloud.devtools import cloudbuild_v1

pytestmark = pytest.mark.integration

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "my-super-cool-app-dev-3f74d0")


class TestCloudBuild:
    @pytest.mark.timeout(120)
    def test_submit_and_poll_simple_build(self):
        client = cloudbuild_v1.CloudBuildClient()
        build = cloudbuild_v1.Build(
            steps=[
                cloudbuild_v1.BuildStep(
                    name="ubuntu",
                    args=["echo", "integration test passed"],
                ),
            ],
            timeout={"seconds": 60},
        )
        operation = client.create_build(project_id=PROJECT_ID, build=build)
        build_result = operation.result(timeout=120)
        assert build_result.status == cloudbuild_v1.Build.Status.SUCCESS
