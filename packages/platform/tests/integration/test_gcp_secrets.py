"""Integration tests for Secret Manager operations."""

import os
import pytest
from google.cloud import secretmanager

pytestmark = pytest.mark.integration

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "my-super-cool-app-dev-3f74d0")


class TestSecretManagerOperations:
    def test_create_and_read_secret(self, test_prefix):
        client = secretmanager.SecretManagerServiceClient()
        secret_id = f"{test_prefix}-secret"
        parent = f"projects/{PROJECT_ID}"
        secret_name = f"{parent}/secrets/{secret_id}"

        try:
            client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": secret_id,
                    "secret": {"replication": {"automatic": {}}},
                }
            )
            client.add_secret_version(
                request={
                    "parent": secret_name,
                    "payload": {"data": b"test-value-123"},
                }
            )
            response = client.access_secret_version(
                request={"name": f"{secret_name}/versions/latest"}
            )
            assert response.payload.data == b"test-value-123"
        finally:
            try:
                client.delete_secret(request={"name": secret_name})
            except Exception:
                pass
