"""Integration tests for Firestore secrets store with GCP Secret Manager."""

import pytest
from packages.platform.store import secrets as secret_store

pytestmark = pytest.mark.integration

GCP_PROJECT = "my-super-cool-app-dev-3f74d0"


class TestSecretLifecycle:
    def test_create_and_read(self, tenant_id, test_prefix):
        project_ref_id = f"{test_prefix}-sec"
        secret_id = f"{test_prefix}-secret"
        try:
            result = secret_store.create_secret(
                tenant_id, project_ref_id, "dev",
                GCP_PROJECT, secret_id, "my-secret-value-123456",
                "test secret", "test@test.com",
            )
            assert result["status"] == "active"
            assert result["version"] == "1"

            secret = secret_store.get_secret(tenant_id, project_ref_id, "dev", secret_id)
            assert secret is not None
            assert secret["secret_id"] == secret_id
            assert secret["status"] == "active"
            assert secret["active_version_count"] == 1
            assert secret["masked_value"] is not None
        finally:
            try:
                secret_store.delete_secret(tenant_id, project_ref_id, "dev", GCP_PROJECT, secret_id)
            except Exception:
                pass

    def test_add_version(self, tenant_id, test_prefix):
        project_ref_id = f"{test_prefix}-ver"
        secret_id = f"{test_prefix}-versioned"
        try:
            secret_store.create_secret(
                tenant_id, project_ref_id, "dev",
                GCP_PROJECT, secret_id, "initial-value-123456",
                "", "test@test.com",
            )
            result = secret_store.add_version(
                tenant_id, project_ref_id, "dev",
                GCP_PROJECT, secret_id, "updated-value-654321",
                "test@test.com",
            )
            assert result["version"] == "2"

            secret = secret_store.get_secret(tenant_id, project_ref_id, "dev", secret_id)
            assert secret["active_version_count"] == 2
            assert secret["latest_version"] == "2"
        finally:
            try:
                secret_store.delete_secret(tenant_id, project_ref_id, "dev", GCP_PROJECT, secret_id)
            except Exception:
                pass

    def test_destroy_version_soft_delete(self, tenant_id, test_prefix):
        project_ref_id = f"{test_prefix}-dst"
        secret_id = f"{test_prefix}-destroy"
        try:
            secret_store.create_secret(
                tenant_id, project_ref_id, "dev",
                GCP_PROJECT, secret_id, "value-one-123456",
                "", "test@test.com",
            )
            secret_store.add_version(
                tenant_id, project_ref_id, "dev",
                GCP_PROJECT, secret_id, "value-two-654321",
                "test@test.com",
            )
            result = secret_store.destroy_version(
                tenant_id, project_ref_id, "dev",
                GCP_PROJECT, secret_id, "2",
                "test@test.com",
            )
            assert result["status"] == "destroyed"

            secret = secret_store.get_secret(tenant_id, project_ref_id, "dev", secret_id)
            assert secret["active_version_count"] == 1
            assert secret["status"] == "active"

            versions = secret_store.list_versions(tenant_id, project_ref_id, "dev", secret_id)
            v2 = next(v for v in versions if v["version"] == "2")
            assert v2["status"] == "destroyed"
            assert v2["destroyed_by"] == "test@test.com"
        finally:
            try:
                secret_store.delete_secret(tenant_id, project_ref_id, "dev", GCP_PROJECT, secret_id)
            except Exception:
                pass

    def test_destroy_last_version_sets_empty(self, tenant_id, test_prefix):
        project_ref_id = f"{test_prefix}-emp"
        secret_id = f"{test_prefix}-empty"
        try:
            secret_store.create_secret(
                tenant_id, project_ref_id, "dev",
                GCP_PROJECT, secret_id, "only-value-123456",
                "", "test@test.com",
            )
            secret_store.destroy_version(
                tenant_id, project_ref_id, "dev",
                GCP_PROJECT, secret_id, "1",
                "test@test.com",
            )
            secret = secret_store.get_secret(tenant_id, project_ref_id, "dev", secret_id)
            assert secret["status"] == "empty"
            assert secret["active_version_count"] == 0
            assert secret["masked_value"] is None
        finally:
            try:
                secret_store.delete_secret(tenant_id, project_ref_id, "dev", GCP_PROJECT, secret_id)
            except Exception:
                pass

    def test_add_version_revives_empty(self, tenant_id, test_prefix):
        project_ref_id = f"{test_prefix}-rev"
        secret_id = f"{test_prefix}-revive"
        try:
            secret_store.create_secret(
                tenant_id, project_ref_id, "dev",
                GCP_PROJECT, secret_id, "first-value-123456",
                "", "test@test.com",
            )
            secret_store.destroy_version(
                tenant_id, project_ref_id, "dev",
                GCP_PROJECT, secret_id, "1",
                "test@test.com",
            )
            secret_store.add_version(
                tenant_id, project_ref_id, "dev",
                GCP_PROJECT, secret_id, "revived-value-123456",
                "test@test.com",
            )
            secret = secret_store.get_secret(tenant_id, project_ref_id, "dev", secret_id)
            assert secret["status"] == "active"
            assert secret["active_version_count"] == 1
        finally:
            try:
                secret_store.delete_secret(tenant_id, project_ref_id, "dev", GCP_PROJECT, secret_id)
            except Exception:
                pass

    def test_delete_secret_marks_destroyed(self, tenant_id, test_prefix):
        project_ref_id = f"{test_prefix}-del"
        secret_id = f"{test_prefix}-delete"
        secret_store.create_secret(
            tenant_id, project_ref_id, "dev",
            GCP_PROJECT, secret_id, "delete-me-123456",
            "", "test@test.com",
        )
        result = secret_store.delete_secret(tenant_id, project_ref_id, "dev", GCP_PROJECT, secret_id)
        assert result["status"] == "destroyed"

        secret = secret_store.get_secret(tenant_id, project_ref_id, "dev", secret_id)
        assert secret["status"] == "destroyed"
        assert secret["active_version_count"] == 0

    def test_short_secret_masked_as_none(self, tenant_id, test_prefix):
        project_ref_id = f"{test_prefix}-shrt"
        secret_id = f"{test_prefix}-short"
        try:
            secret_store.create_secret(
                tenant_id, project_ref_id, "dev",
                GCP_PROJECT, secret_id, "abc",
                "", "test@test.com",
            )
            secret = secret_store.get_secret(tenant_id, project_ref_id, "dev", secret_id)
            assert secret["masked_value"] is None
        finally:
            try:
                secret_store.delete_secret(tenant_id, project_ref_id, "dev", GCP_PROJECT, secret_id)
            except Exception:
                pass

    def test_list_secrets(self, tenant_id, test_prefix):
        project_ref_id = f"{test_prefix}-lst"
        sid1 = f"{test_prefix}-list-a"
        sid2 = f"{test_prefix}-list-b"
        try:
            secret_store.create_secret(tenant_id, project_ref_id, "dev",
                                       GCP_PROJECT, sid1, "value-aaa-123456", "", "test@test.com")
            secret_store.create_secret(tenant_id, project_ref_id, "dev",
                                       GCP_PROJECT, sid2, "value-bbb-123456", "", "test@test.com")
            secrets = secret_store.list_secrets(tenant_id, project_ref_id, "dev")
            ids = [s["secret_id"] for s in secrets]
            assert sid1 in ids
            assert sid2 in ids
        finally:
            for sid in [sid1, sid2]:
                try:
                    secret_store.delete_secret(tenant_id, project_ref_id, "dev", GCP_PROJECT, sid)
                except Exception:
                    pass
