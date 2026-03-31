"""Integration test fixtures — GCP clients, cleanup helpers, test identity."""

import os
import uuid

import pytest

# Ensure env is set for auth bypass
os.environ.setdefault("AUTH_DISABLED", "true")
os.environ.setdefault("ENVIRONMENT", "dev")

# Host project runs Firestore, Cloud Build, the API itself
_HOST_PROJECT = os.environ.get("GCP_PROJECT_ID", "pl4m-host-dev")
# Tenant project is the target GCP project for test deploys
_TENANT_PROJECT = os.environ.get("TEST_TENANT_PROJECT", "my-super-cool-app-dev-3f74d0")


def _test_prefix():
    return f"test-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_prefix():
    return _test_prefix()


@pytest.fixture
def tenant_id():
    return os.environ.get("DEV_TENANT_ID", "dev-local")


@pytest.fixture
def firestore_client():
    from google.cloud import firestore
    database = os.environ.get("FIRESTORE_DATABASE", "(default)")
    return firestore.Client(project=_HOST_PROJECT, database=database)


@pytest.fixture
def gcs_client():
    from google.cloud import storage
    return storage.Client(project=_HOST_PROJECT)


@pytest.fixture
def api_client():
    from fastapi.testclient import TestClient
    from packages.api.main import app
    return TestClient(app)


@pytest.fixture
def sample_project_data(test_prefix):
    """Project data with per-env GCP fields matching the new format."""
    return {
        "project_id": _TENANT_PROJECT,
        "display_name": f"Test Project {test_prefix}",
        "region": "us-central1",
        "environments": [{
            "id": str(uuid.uuid4()),
            "name": "dev",
            "order": 0,
            "deployed": False,
            "deployed_at": None,
            "gcp_project_id": _TENANT_PROJECT,
            "tf_bucket": f"{_TENANT_PROJECT}-tfstate",
            "region": "us-central1",
            "provision_status": "ready",
            "provision_id": "",
        }],
    }


@pytest.fixture
def sample_envelope_data():
    return {
        "global": {
            "project_id": _TENANT_PROJECT,
            "region": "us-central1",
            "environment": "dev",
        },
        "nodes": [
            {"name": "test-vpc", "type": "vpc", "config": {"auto_create_subnetworks": False}},
            {"name": "test-sa", "type": "service_account", "config": {}},
            {"name": "test-service", "type": "cloud_run", "config": {
                "image": "gcr.io/test/image:latest",
                "service_account": "test-sa",
            }, "depends_on": ["test-vpc", "test-sa"]},
        ],
    }
