"""Integration tests for collaborator management."""

import pytest
from packages.platform.store import collaborators as collab_store
from packages.platform.store import projects as project_store

pytestmark = pytest.mark.integration


class TestCollaboratorLifecycle:
    def test_add_and_list(self, tenant_id, test_prefix):
        project_data = {
            "name": f"Collab Test {test_prefix}",
            "owner_uid": tenant_id,
            "environments": ["dev"],
        }
        saved = project_store.save_project(tenant_id, project_data)
        project_id = saved["id"]
        try:
            collab_store.add_collaborator(
                tenant_id, project_id, "collab@test.com", "viewer",
                collaborator_uid="collab-user-123",
            )
            collabs = collab_store.list_collaborators(tenant_id, project_id)
            emails = [c.get("email") for c in collabs]
            assert "collab@test.com" in emails
        finally:
            collab_store.remove_collaborator(tenant_id, project_id, "collab-user-123")
            project_store.delete_project(tenant_id, project_id)

    def test_remove_collaborator(self, tenant_id, test_prefix):
        project_data = {
            "name": f"Remove Collab Test {test_prefix}",
            "owner_uid": tenant_id,
            "environments": ["dev"],
        }
        saved = project_store.save_project(tenant_id, project_data)
        project_id = saved["id"]
        try:
            collab_store.add_collaborator(
                tenant_id, project_id, "rm@test.com", "editor",
                collaborator_uid="rm-user-456",
            )
            collab_store.remove_collaborator(tenant_id, project_id, "rm-user-456")
            collabs = collab_store.list_collaborators(tenant_id, project_id)
            uids = [c.get("uid") for c in collabs]
            assert "rm-user-456" not in uids
        finally:
            project_store.delete_project(tenant_id, project_id)
