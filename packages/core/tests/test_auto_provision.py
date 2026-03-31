"""Auto-provisioning logic tests — service account + networking auto-creation."""

import pytest

from packages.core.auto_provision import auto_provision_for_node


class TestNonComputeNodes:
    """Non-compute nodes should produce no auto-provisioned resources."""

    def test_firestore_node_creates_nothing(self):
        node = {"name": "my-db", "type": "firestore", "depends_on": []}
        result = auto_provision_for_node(node, [])
        assert result["created"] == []

    def test_pubsub_node_creates_nothing(self):
        node = {"name": "my-topic", "type": "pubsub_topic", "depends_on": []}
        result = auto_provision_for_node(node, [])
        assert result["created"] == []

    def test_vpc_node_creates_nothing(self):
        node = {"name": "my-vpc", "type": "vpc", "depends_on": []}
        result = auto_provision_for_node(node, [])
        assert result["created"] == []


class TestServiceAccountCreation:
    """Compute nodes should get auto-created service accounts."""

    def test_cloud_run_creates_sa(self):
        node = {"name": "api-service", "type": "cloud_run", "depends_on": []}
        result = auto_provision_for_node(node, [])
        created = result["created"]
        sa_nodes = [n for n in created if n["type"] == "service_account"]
        assert len(sa_nodes) == 1
        assert sa_nodes[0]["name"] == "sa-api-service"
        assert sa_nodes[0]["auto_provisioned"] is True

    def test_cloud_run_job_creates_sa(self):
        node = {"name": "worker", "type": "cloud_run_job", "depends_on": []}
        result = auto_provision_for_node(node, [])
        sa_nodes = [n for n in result["created"] if n["type"] == "service_account"]
        assert len(sa_nodes) == 1
        assert sa_nodes[0]["name"] == "sa-worker"

    def test_cloud_function_creates_sa(self):
        node = {"name": "handler", "type": "cloud_function", "depends_on": []}
        result = auto_provision_for_node(node, [])
        sa_nodes = [n for n in result["created"] if n["type"] == "service_account"]
        assert len(sa_nodes) == 1
        assert sa_nodes[0]["name"] == "sa-handler"

    def test_sa_has_correct_structure(self):
        node = {"name": "api", "type": "cloud_run", "depends_on": []}
        result = auto_provision_for_node(node, [])
        sa = [n for n in result["created"] if n["type"] == "service_account"][0]
        assert sa["config"]["account_id"] == "sa-api"
        assert sa["depends_on"] == []
        assert sa["auto_provisioned"] is True

    def test_existing_sa_skips_creation(self):
        node = {"name": "api", "type": "cloud_run", "depends_on": []}
        existing = [
            {"name": "sa-api", "type": "service_account", "depends_on": []},
        ]
        result = auto_provision_for_node(node, existing)
        sa_nodes = [n for n in result["created"] if n["type"] == "service_account"]
        assert len(sa_nodes) == 0


class TestNetworkingAutoProvision:
    """Compute nodes with private-access deps should get VPC/subnet/connector."""

    def test_cloud_run_with_cloud_sql_creates_networking(self):
        node = {"name": "api", "type": "cloud_run", "depends_on": ["my-db"]}
        existing = [
            {"name": "my-db", "type": "cloud_sql", "depends_on": []},
        ]
        result = auto_provision_for_node(node, existing)
        types_created = [n["type"] for n in result["created"]]
        assert "vpc" in types_created
        assert "subnet" in types_created
        assert "vpc_connector" in types_created

    def test_cloud_run_with_bigtable_creates_networking(self):
        node = {"name": "api", "type": "cloud_run", "depends_on": ["my-bt"]}
        existing = [
            {"name": "my-bt", "type": "bigtable", "depends_on": []},
        ]
        result = auto_provision_for_node(node, existing)
        types_created = [n["type"] for n in result["created"]]
        assert "vpc" in types_created

    def test_cloud_run_with_firestore_no_networking(self):
        node = {"name": "api", "type": "cloud_run", "depends_on": ["my-fs"]}
        existing = [
            {"name": "my-fs", "type": "firestore", "depends_on": []},
        ]
        result = auto_provision_for_node(node, existing)
        types_created = [n["type"] for n in result["created"]]
        assert "vpc" not in types_created
        assert "subnet" not in types_created
        assert "vpc_connector" not in types_created

    def test_cloud_run_with_pubsub_no_networking(self):
        node = {"name": "api", "type": "cloud_run", "depends_on": ["my-topic"]}
        existing = [
            {"name": "my-topic", "type": "pubsub_topic", "depends_on": []},
        ]
        result = auto_provision_for_node(node, existing)
        types_created = [n["type"] for n in result["created"]]
        assert "vpc" not in types_created

    def test_networking_nodes_are_auto_provisioned(self):
        node = {"name": "api", "type": "cloud_run", "depends_on": ["my-db"]}
        existing = [
            {"name": "my-db", "type": "cloud_sql", "depends_on": []},
        ]
        result = auto_provision_for_node(node, existing)
        for created_node in result["created"]:
            assert created_node["auto_provisioned"] is True

    def test_networking_uses_fixed_names(self):
        node = {"name": "api", "type": "cloud_run", "depends_on": ["my-db"]}
        existing = [
            {"name": "my-db", "type": "cloud_sql", "depends_on": []},
        ]
        result = auto_provision_for_node(node, existing)
        names = {n["name"] for n in result["created"]}
        assert "default-vpc" in names
        assert "default-subnet" in names
        assert "default-connector" in names

    def test_subnet_depends_on_vpc(self):
        node = {"name": "api", "type": "cloud_run", "depends_on": ["my-db"]}
        existing = [
            {"name": "my-db", "type": "cloud_sql", "depends_on": []},
        ]
        result = auto_provision_for_node(node, existing)
        subnet = [n for n in result["created"] if n["type"] == "subnet"][0]
        assert "default-vpc" in subnet["depends_on"]

    def test_connector_depends_on_subnet(self):
        node = {"name": "api", "type": "cloud_run", "depends_on": ["my-db"]}
        existing = [
            {"name": "my-db", "type": "cloud_sql", "depends_on": []},
        ]
        result = auto_provision_for_node(node, existing)
        connector = [n for n in result["created"] if n["type"] == "vpc_connector"][0]
        assert "default-subnet" in connector["depends_on"]


class TestNoDuplicateNetworking:
    """Second compute node should reuse existing networking."""

    def test_existing_vpc_skips_networking(self):
        node = {"name": "worker", "type": "cloud_run_job", "depends_on": ["my-db"]}
        existing = [
            {"name": "my-db", "type": "cloud_sql", "depends_on": []},
            {"name": "default-vpc", "type": "vpc", "depends_on": []},
            {"name": "default-subnet", "type": "subnet", "depends_on": ["default-vpc"]},
            {"name": "default-connector", "type": "vpc_connector", "depends_on": ["default-subnet"]},
        ]
        result = auto_provision_for_node(node, existing)
        types_created = [n["type"] for n in result["created"]]
        assert "vpc" not in types_created
        assert "subnet" not in types_created
        assert "vpc_connector" not in types_created

    def test_existing_networking_still_creates_sa(self):
        node = {"name": "worker", "type": "cloud_run_job", "depends_on": ["my-db"]}
        existing = [
            {"name": "my-db", "type": "cloud_sql", "depends_on": []},
            {"name": "default-vpc", "type": "vpc", "depends_on": []},
            {"name": "default-subnet", "type": "subnet", "depends_on": ["default-vpc"]},
            {"name": "default-connector", "type": "vpc_connector", "depends_on": ["default-subnet"]},
        ]
        result = auto_provision_for_node(node, existing)
        sa_nodes = [n for n in result["created"] if n["type"] == "service_account"]
        assert len(sa_nodes) == 1


class TestDependsOnUpdates:
    """Compute node's depends_on should include auto-created SA and connector."""

    def test_compute_depends_on_includes_sa(self):
        node = {"name": "api", "type": "cloud_run", "depends_on": []}
        result = auto_provision_for_node(node, [])
        assert "sa-api" in node["depends_on"]

    def test_compute_with_networking_depends_on_connector(self):
        node = {"name": "api", "type": "cloud_run", "depends_on": ["my-db"]}
        existing = [
            {"name": "my-db", "type": "cloud_sql", "depends_on": []},
        ]
        result = auto_provision_for_node(node, existing)
        assert "default-connector" in node["depends_on"]
        assert "sa-api" in node["depends_on"]
