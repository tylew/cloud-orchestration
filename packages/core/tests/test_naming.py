"""Tests for BaseNode resource_id auto-generation and resolve_gcp_name()."""

import pytest
from core.schemas.base import BaseNode
from core.schemas.enums import NodeType
from core.terraform.naming import resolve_gcp_name


# --- resource_id auto-generation ---


def test_resource_id_auto_generated():
    node = BaseNode(name="my-svc", type=NodeType.CLOUD_RUN)
    assert len(node.resource_id) == 8
    assert all(c in "0123456789abcdef" for c in node.resource_id)


def test_resource_id_deterministic():
    """Same id always produces the same resource_id."""
    fixed_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    n1 = BaseNode(id=fixed_id, name="svc-a", type=NodeType.CLOUD_RUN)
    n2 = BaseNode(id=fixed_id, name="svc-b", type=NodeType.CLOUD_RUN)
    assert n1.resource_id == n2.resource_id
    assert n1.resource_id == "a1b2c3d4"


def test_resource_id_preserves_explicit():
    """If resource_id is explicitly provided, it is not overwritten."""
    node = BaseNode(
        id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        resource_id="custom99",
        name="svc-x",
        type=NodeType.CLOUD_RUN,
    )
    assert node.resource_id == "custom99"


def test_basenode_backward_compat():
    """Existing fixtures that omit id/resource_id still work."""
    node = BaseNode(name="old-node", type=NodeType.CLOUD_RUN)
    assert node.id  # auto-generated UUID
    assert node.resource_id  # auto-derived


# --- resolve_gcp_name ---


def _node(node_type: NodeType, rid: str = "ab12cd34") -> BaseNode:
    # Minimal required configs for types that need them
    configs: dict = {
        NodeType.BIGQUERY: {"dataset_id": "ds"},
        NodeType.BIGTABLE: {"instance_id": "i", "cluster": {"cluster_id": "c", "zone": "z"}},
        NodeType.VPC: {"auto_create_subnetworks": False},
        NodeType.CLOUD_SQL_DATABASE: {"parentRef": "p", "name": "n"},
        NodeType.CLOUD_SQL_TABLE: {"parentRef": "p", "name": "n"},
        NodeType.THIRD_PARTY_API: {"provider": "x", "base_url": "http://x"},
    }
    return BaseNode(
        id="ab12cd34-0000-0000-0000-000000000000",
        resource_id=rid,
        name="my-node",
        type=node_type,
        config=configs.get(node_type, {}),
    )


def test_env_prefixed():
    assert resolve_gcp_name(_node(NodeType.CLOUD_RUN), "dev") == "dev-ab12cd34"


def test_sa_prefixed():
    assert resolve_gcp_name(_node(NodeType.SERVICE_ACCOUNT), "dev") == "sa-ab12cd34"


def test_bq_underscore():
    assert resolve_gcp_name(_node(NodeType.BIGQUERY), "dev") == "bq_ab12cd34"


def test_firestore_default():
    assert resolve_gcp_name(_node(NodeType.FIRESTORE), "dev") == "(default)"


def test_bare_rid():
    assert resolve_gcp_name(_node(NodeType.VPC), "dev") == "ab12cd34"


def test_no_template_returns_empty():
    assert resolve_gcp_name(_node(NodeType.THIRD_PARTY_API), "dev") == ""
    assert resolve_gcp_name(_node(NodeType.CLOUD_SQL_TABLE), "dev") == ""


def test_bigtable():
    assert resolve_gcp_name(_node(NodeType.BIGTABLE), "prod") == "bt-ab12cd34"


def test_cloud_sql_database():
    assert resolve_gcp_name(_node(NodeType.CLOUD_SQL_DATABASE), "dev") == "ab12cd34"
