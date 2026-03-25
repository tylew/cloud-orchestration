"""Integration test fixtures — GCP clients, cleanup helpers, test identity."""

import os
import uuid

import pytest

# Ensure env is set for auth bypass
os.environ.setdefault("AUTH_DISABLED", "true")
os.environ.setdefault("ENVIRONMENT", "dev")


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
    project = os.environ.get("GCP_PROJECT_ID", "my-super-cool-app-dev-3f74d0")
    database = os.environ.get("FIRESTORE_DATABASE", "(default)")
    return firestore.Client(project=project, database=database)


@pytest.fixture
def gcs_client():
    from google.cloud import storage
    return storage.Client(project=os.environ.get("GCP_PROJECT_ID", "my-super-cool-app-dev-3f74d0"))


@pytest.fixture
def api_client():
    from fastapi.testclient import TestClient
    from packages.api.main import app
    return TestClient(app)


@pytest.fixture
def sample_envelope_data():
    return {
        "global": {
            "project_id": os.environ.get("GCP_PROJECT_ID", "my-super-cool-app-dev-3f74d0"),
            "region": "us-central1",
            "environment": "dev",
        },
        "nodes": [
            {"name": "test-vpc", "type": "vpc", "config": {"auto_create_subnetworks": False}},
            {"name": "test-sa", "type": "service_account", "config": {"account_id": "test-sa"}},
            {"name": "test-service", "type": "cloud_run", "config": {
                "image": "gcr.io/test/image:latest",
                "service_account": "test-sa",
            }, "depends_on": ["test-vpc", "test-sa"]},
        ],
    }
