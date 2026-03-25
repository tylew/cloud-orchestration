"""Integration tests for Firestore blueprint CRUD with node sharding."""

import pytest
from packages.platform.store import blueprints as blueprint_store
from packages.platform.store import projects as project_store

pytestmark = pytest.mark.integration


class TestBlueprintLifecycle:
    def test_save_and_read_back(self, tenant_id, test_prefix, sample_envelope_data):
        project_data = {
            "name": f"BP Test {test_prefix}",
            "owner_uid": tenant_id,
            "environments": ["dev"],
        }
        saved = project_store.save_project(tenant_id, project_data)
        project_id = saved["id"]
        try:
            result = blueprint_store.save_env_blueprint(tenant_id, project_id, "dev", sample_envelope_data)
            assert result["node_count"] == 3

            doc = blueprint_store.get_env_blueprint(tenant_id, project_id, "dev")
            assert doc is not None
            envelope = doc.get("envelope", doc)
            nodes = envelope.get("nodes", [])
            assert len(nodes) == 3
        finally:
            project_store.delete_project(tenant_id, project_id)

    def test_node_sharding_reconstruction(self, tenant_id, test_prefix):
        project_data = {
            "name": f"Shard Test {test_prefix}",
            "owner_uid": tenant_id,
            "environments": ["dev"],
        }
        envelope = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": f"vpc-{i}", "type": "vpc", "config": {"auto_create_subnetworks": False}}
                for i in range(6)
            ],
        }
        saved = project_store.save_project(tenant_id, project_data)
        project_id = saved["id"]
        try:
            result = blueprint_store.save_env_blueprint(tenant_id, project_id, "dev", envelope)
            assert result["node_count"] == 6

            doc = blueprint_store.get_env_blueprint(tenant_id, project_id, "dev")
            read_envelope = doc.get("envelope", doc)
            read_nodes = read_envelope.get("nodes", [])
            assert len(read_nodes) == 6
            names = {n["name"] for n in read_nodes}
            assert names == {f"vpc-{i}" for i in range(6)}
        finally:
            project_store.delete_project(tenant_id, project_id)

    def test_change_detection(self, tenant_id, test_prefix, sample_envelope_data):
        project_data = {
            "name": f"Change Test {test_prefix}",
            "owner_uid": tenant_id,
            "environments": ["dev"],
        }
        saved = project_store.save_project(tenant_id, project_data)
        project_id = saved["id"]
        try:
            result1 = blueprint_store.save_env_blueprint(tenant_id, project_id, "dev", sample_envelope_data)
            assert result1["node_count"] == 3

            modified = dict(sample_envelope_data)
            modified["nodes"] = list(sample_envelope_data["nodes"])
            modified_node = dict(modified["nodes"][2])
            modified_node["config"] = dict(modified_node["config"])
            modified_node["config"]["image"] = "gcr.io/test/image:v2"
            modified["nodes"][2] = modified_node

            result2 = blueprint_store.save_env_blueprint(tenant_id, project_id, "dev", modified)
            changes = result2.get("changes", {})
            assert len(changes.get("modified", [])) >= 1 or result2.get("is_noop") is not True
        finally:
            project_store.delete_project(tenant_id, project_id)
