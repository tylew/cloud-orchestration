"""MCP node CRUD tool tests — add, update, delete, list with auto-provisioning."""

import json
from unittest.mock import patch, MagicMock


# ── Test Helpers ─────────────────────────────────────────────


def _make_node(slug, name, node_type, config=None, depends_on=None, auto_provisioned=False):
    """Create a minimal node dict for testing."""
    node = {
        "slug": slug,
        "name": name,
        "type": node_type,
        "config": config or {},
        "depends_on": depends_on or [],
    }
    if auto_provisioned:
        node["auto_provisioned"] = True
    return node


# Shared no-op for _ensure_deps since schema modules aren't in this worktree
_NOOP = "packages.mcp.tools.nodes._ensure_deps"


# ── Test 1: add_node for cloud_run returns created node + auto-provisioned SA ──


@patch(_NOOP)
@patch("packages.mcp.tools.nodes.blueprint_store", new_callable=MagicMock)
@patch("packages.mcp.tools.nodes.auto_provision_for_node")
@patch("packages.mcp.tools.nodes._run_validation_and_persist")
@patch("packages.mcp.tools.nodes._generate_slug")
def test_add_node_cloud_run_returns_auto_provisioned_sa(
    mock_slug, mock_validate, mock_auto, mock_store, _noop
):
    mock_slug.return_value = "cr-abc123"
    mock_store.get_node.return_value = None
    mock_store.save_node.return_value = {}
    mock_store.list_nodes.return_value = []
    mock_auto.return_value = {
        "created": [
            _make_node("sa-my-api", "sa-my-api", "service_account", auto_provisioned=True),
        ],
        "warnings": [],
    }
    mock_validate.return_value = {"cr-abc123": {"errors": [], "warnings": []}}

    from packages.mcp.tools.nodes import add_node
    result = add_node(project_ref_id="proj-1", env_name="dev", name="my-api", node_type="cloud_run")
    parsed = json.loads(result)

    assert parsed["node"]["slug"] == "cr-abc123"
    assert parsed["node"]["type"] == "cloud_run"
    assert len(parsed["auto_created"]) == 1
    assert parsed["auto_created"][0]["type"] == "service_account"
    mock_auto.assert_called_once()
    mock_store.save_node.assert_called()


# ── Test 2: add_node for firestore returns no auto-provisioned nodes ──


@patch(_NOOP)
@patch("packages.mcp.tools.nodes.blueprint_store", new_callable=MagicMock)
@patch("packages.mcp.tools.nodes.auto_provision_for_node")
@patch("packages.mcp.tools.nodes._run_validation_and_persist")
@patch("packages.mcp.tools.nodes._generate_slug")
def test_add_node_firestore_no_auto_provision(
    mock_slug, mock_validate, mock_auto, mock_store, _noop
):
    mock_slug.return_value = "fs-xyz789"
    mock_store.get_node.return_value = None
    mock_store.save_node.return_value = {}
    mock_store.list_nodes.return_value = []
    mock_auto.return_value = {"created": [], "warnings": []}
    mock_validate.return_value = {"fs-xyz789": {"errors": [], "warnings": []}}

    from packages.mcp.tools.nodes import add_node
    result = add_node(project_ref_id="proj-1", env_name="dev", name="my-db", node_type="firestore")
    parsed = json.loads(result)

    assert parsed["node"]["type"] == "firestore"
    assert parsed["auto_created"] == []


# ── Test 3: add_node response includes auto_created list (D-09) ──


@patch(_NOOP)
@patch("packages.mcp.tools.nodes.blueprint_store", new_callable=MagicMock)
@patch("packages.mcp.tools.nodes.auto_provision_for_node")
@patch("packages.mcp.tools.nodes._run_validation_and_persist")
@patch("packages.mcp.tools.nodes._generate_slug")
def test_add_node_includes_auto_created_key(
    mock_slug, mock_validate, mock_auto, mock_store, _noop
):
    mock_slug.return_value = "cr-aaa111"
    mock_store.get_node.return_value = None
    mock_store.save_node.return_value = {}
    mock_store.list_nodes.return_value = []
    mock_auto.return_value = {
        "created": [
            _make_node("sa-svc", "sa-svc", "service_account", auto_provisioned=True),
            _make_node("default-vpc", "default-vpc", "vpc", auto_provisioned=True),
        ],
        "warnings": ["VPC created for private access"],
    }
    mock_validate.return_value = {}

    from packages.mcp.tools.nodes import add_node
    result = add_node(project_ref_id="proj-1", env_name="dev", name="svc", node_type="cloud_run")
    parsed = json.loads(result)

    assert "auto_created" in parsed
    assert len(parsed["auto_created"]) == 2
    assert parsed["auto_created"][0]["auto_provisioned"] is True
    assert "warnings" in parsed


# ── Test 4: update_node returns updated node data + validation results ──


@patch(_NOOP)
@patch("packages.mcp.tools.nodes.blueprint_store", new_callable=MagicMock)
@patch("packages.mcp.tools.nodes._run_validation_and_persist")
def test_update_node_returns_updated_data(mock_validate, mock_store, _noop):
    existing = _make_node("cr-abc123", "my-api", "cloud_run", config={"image": "old"})
    mock_store.get_node.return_value = existing
    mock_store.save_node.return_value = {}
    mock_store.list_nodes.return_value = [existing]
    mock_validate.return_value = {"cr-abc123": {"errors": [], "warnings": []}}

    from packages.mcp.tools.nodes import update_node
    result = update_node(project_ref_id="proj-1", env_name="dev", slug="cr-abc123", config={"image": "new"})
    parsed = json.loads(result)

    assert parsed["node"]["config"]["image"] == "new"
    assert "validation" in parsed
    mock_store.save_node.assert_called_once()


# ── Test 5: delete_node returns list of deleted slugs ──


@patch(_NOOP)
@patch("packages.mcp.tools.nodes.blueprint_store", new_callable=MagicMock)
@patch("packages.mcp.tools.nodes._run_validation_and_persist")
def test_delete_node_returns_deleted_slugs(mock_validate, mock_store, _noop):
    mock_store.get_node.return_value = _make_node("cr-abc123", "my-api", "cloud_run")
    mock_store.delete_node.return_value = ["cr-abc123", "fc-child1"]
    mock_validate.return_value = {}

    from packages.mcp.tools.nodes import delete_node
    result = delete_node(project_ref_id="proj-1", env_name="dev", slug="cr-abc123")
    parsed = json.loads(result)

    assert parsed["deleted_slugs"] == ["cr-abc123", "fc-child1"]
    assert "validation" in parsed


# ── Test 6: list_nodes returns nodes with validation state ──


@patch(_NOOP)
@patch("packages.mcp.tools.nodes.blueprint_store", new_callable=MagicMock)
def test_list_nodes_returns_with_validation(mock_store, _noop):
    mock_store.list_nodes.return_value = [
        _make_node("cr-a1", "api", "cloud_run"),
        _make_node("fs-b2", "db", "firestore"),
    ]
    mock_store.get_validation_doc.return_value = {
        "nodes": {
            "cr-a1": {"errors": [{"message": "Missing image"}], "warnings": []},
            "fs-b2": {"errors": [], "warnings": [{"message": "Index recommended"}]},
        }
    }

    from packages.mcp.tools.nodes import list_nodes
    result = list_nodes(project_ref_id="proj-1", env_name="dev")
    parsed = json.loads(result)

    assert len(parsed["nodes"]) == 2
    # First node should have error count
    api_node = next(n for n in parsed["nodes"] if n["slug"] == "cr-a1")
    assert api_node["validation"]["error_count"] == 1


# ── Test 7: add_node with invalid type returns error ──


def test_add_node_invalid_type_returns_error():
    from packages.mcp.tools.nodes import add_node
    result = add_node(project_ref_id="proj-1", env_name="dev", name="bad", node_type="not_a_type")
    parsed = json.loads(result)

    assert "error_type" in parsed
    assert "validation" in parsed["error_type"].lower() or "invalid" in parsed["message"].lower()


# ── Test 8: delete_node with auto_provisioned warning (D-10) ──


@patch(_NOOP)
@patch("packages.mcp.tools.nodes.blueprint_store", new_callable=MagicMock)
@patch("packages.mcp.tools.nodes._run_validation_and_persist")
def test_delete_auto_provisioned_node_includes_warning(mock_validate, mock_store, _noop):
    auto_node = _make_node("sa-my-api", "sa-my-api", "service_account", auto_provisioned=True)
    mock_store.get_node.return_value = auto_node
    mock_store.delete_node.return_value = ["sa-my-api"]
    mock_validate.return_value = {}

    from packages.mcp.tools.nodes import delete_node
    result = delete_node(project_ref_id="proj-1", env_name="dev", slug="sa-my-api")
    parsed = json.loads(result)

    assert any("auto" in w.lower() or "provisioned" in w.lower() for w in parsed.get("warnings", []))
