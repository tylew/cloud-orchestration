"""Shared test fixtures — reusable Envelope builders for unit tests."""

import pytest

try:
    from core.schemas.base import (
        Envelope, BaseNode, GlobalConfig, Metadata, NodeOutput,
    )
    from core.schemas.enums import NodeType
    _HAS_CORE = True
except ImportError:
    _HAS_CORE = False


def _global(project_id="test-project", region="us-central1", env="dev"):
    return {"project_id": project_id, "region": region, "environment": env}


def _node(name, node_type, config=None, depends_on=None, **kwargs):
    """Build a node dict for Envelope construction."""
    d = {"name": name, "type": node_type, "config": config or {}}
    if depends_on:
        d["depends_on"] = depends_on
    d.update(kwargs)
    return d


@pytest.fixture
def minimal_envelope_data():
    """Minimal valid blueprint: VPC + Service Account + Cloud Run."""
    return {
        "global": _global(),
        "nodes": [
            _node("my-vpc", "vpc", {"auto_create_subnetworks": False}),
            _node("my-sa", "service_account", {"account_id": "my-sa"}),
            _node("my-service", "cloud_run", {
                "image": "gcr.io/test/image:latest",
                "service_account": "my-sa",
            }, depends_on=["my-vpc", "my-sa"]),
        ],
    }


@pytest.fixture
def minimal_envelope(minimal_envelope_data):
    """Parsed Envelope from minimal valid blueprint."""
    if not _HAS_CORE:
        pytest.skip("packages.core not available")
    return Envelope.model_validate(minimal_envelope_data)


@pytest.fixture
def complex_envelope_data():
    """Complex blueprint: 8 nodes across multiple types with dependencies."""
    return {
        "global": _global(),
        "nodes": [
            _node("my-vpc", "vpc", {"auto_create_subnetworks": False}),
            _node("my-subnet", "subnet", {
                "ip_cidr_range": "10.0.0.0/24",
                "region": "us-central1",
                "network": "my-vpc",
            }, depends_on=["my-vpc"]),
            _node("my-sa", "service_account", {"account_id": "my-sa"}),
            _node("my-db", "cloud_sql", {
                "database_version": "POSTGRES_15",
                "tier": "db-f1-micro",
            }, depends_on=["my-vpc"]),
            _node("my-firestore", "firestore", {
                "location_id": "us-central",
            }),
            _node("my-bucket", "gcs_bucket", {"location": "US"}),
            _node("my-topic", "pubsub_topic", {}),
            _node("my-service", "cloud_run", {
                "image": "gcr.io/test/image:latest",
                "service_account": "my-sa",
            }, depends_on=["my-sa", "my-db", "my-firestore", "my-bucket"]),
        ],
    }


@pytest.fixture
def complex_envelope(complex_envelope_data):
    if not _HAS_CORE:
        pytest.skip("packages.core not available")
    return Envelope.model_validate(complex_envelope_data)


@pytest.fixture
def cyclic_envelope_data():
    """Invalid blueprint with a dependency cycle."""
    return {
        "global": _global(),
        "nodes": [
            _node("node-a", "vpc", {"auto_create_subnetworks": False}, depends_on=["node-b"]),
            _node("node-b", "vpc", {"auto_create_subnetworks": False}, depends_on=["node-a"]),
        ],
    }


@pytest.fixture
def output_test_envelope_data():
    """Blueprint with mixed external and internal nodes for output testing."""
    return {
        "global": _global(),
        "nodes": [
            _node("my-vpc", "vpc", {"auto_create_subnetworks": False}),
            _node("my-sa", "service_account", {"account_id": "my-sa"}),
            _node("my-db", "cloud_sql", {
                "database_version": "POSTGRES_15",
                "tier": "db-f1-micro",
            }, depends_on=["my-vpc"]),
            _node("my-service", "cloud_run", {
                "image": "gcr.io/test/image:latest",
                "service_account": "my-sa",
            }, depends_on=["my-sa", "my-db"]),
            _node("my-bucket", "gcs_bucket", {"location": "US"}),
            _node("my-topic", "pubsub_topic", {}),
        ],
    }


@pytest.fixture
def duplicate_names_envelope_data():
    """Invalid blueprint with duplicate node names."""
    return {
        "global": _global(),
        "nodes": [
            _node("my-vpc", "vpc", {"auto_create_subnetworks": False}),
            _node("my-vpc", "vpc", {"auto_create_subnetworks": True}),
        ],
    }
