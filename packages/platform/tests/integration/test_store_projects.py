"""Integration tests for Firestore project CRUD."""

import pytest
from packages.platform.store import projects as project_store

pytestmark = pytest.mark.integration


class TestProjectLifecycle:
    def test_create_and_read(self, tenant_id, test_prefix):
        project_data = {
            "name": f"Test Project {test_prefix}",
            "owner_uid": tenant_id,
            "environments": ["dev"],
        }
        saved = project_store.save_project(tenant_id, project_data)
        project_id = saved["id"]
        try:
            result = project_store.get_project(tenant_id, project_id)
            assert result is not None
            assert result["name"] == project_data["name"]
        finally:
            project_store.delete_project(tenant_id, project_id)

    def test_list_projects(self, tenant_id, test_prefix):
        project_data = {
            "name": f"List Test {test_prefix}",
            "owner_uid": tenant_id,
            "environments": ["dev"],
        }
        saved = project_store.save_project(tenant_id, project_data)
        project_id = saved["id"]
        try:
            projects = project_store.list_projects(tenant_id)
            ids = [p.get("id") for p in projects]
            assert project_id in ids
        finally:
            project_store.delete_project(tenant_id, project_id)

    def test_delete_project(self, tenant_id, test_prefix):
        project_data = {
            "name": f"Delete Test {test_prefix}",
            "owner_uid": tenant_id,
            "environments": ["dev"],
        }
        saved = project_store.save_project(tenant_id, project_data)
        project_id = saved["id"]
        project_store.delete_project(tenant_id, project_id)
        result = project_store.get_project(tenant_id, project_id)
        assert result is None

    def test_update_settings(self, tenant_id, test_prefix):
        project_data = {
            "name": f"Update Test {test_prefix}",
            "owner_uid": tenant_id,
            "environments": ["dev"],
        }
        saved = project_store.save_project(tenant_id, project_data)
        project_id = saved["id"]
        try:
            project_store.update_project_settings(tenant_id, project_id, {"region": "europe-west1"})
            result = project_store.get_project(tenant_id, project_id)
            assert result.get("region") == "europe-west1"
        finally:
            project_store.delete_project(tenant_id, project_id)
