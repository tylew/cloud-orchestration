"""Integration tests for /api/options endpoints."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.options import OPTIONS_REGISTRY
from core.schemas.enums import NodeType

# Import router directly — avoids pulling in the full app with its broken
# packages.core.* legacy imports in other handlers.
from packages.api.handlers.options import router

app = FastAPI()
app.include_router(router, prefix="/api")
client = TestClient(app)


def test_get_all_options_returns_200_with_node_types():
    resp = client.get("/api/options")
    assert resp.status_code == 200
    data = resp.json()
    assert "last_updated" in data
    assert "node_types" in data
    assert isinstance(data["node_types"], dict)
    assert len(data["node_types"]) > 0
    for nt, entry in data["node_types"].items():
        assert "fields" in entry, f"{nt} missing 'fields'"
        assert isinstance(entry["fields"], dict)


def test_get_all_options_covers_all_registry_node_types():
    resp = client.get("/api/options")
    data = resp.json()
    registry_types = {nt.value for (nt, _) in OPTIONS_REGISTRY}
    assert set(data["node_types"].keys()) == registry_types


def test_get_options_cloud_sql_returns_200():
    resp = client.get("/api/options/cloud_sql")
    assert resp.status_code == 200
    data = resp.json()
    assert data["node_type"] == "cloud_sql"
    assert "fields" in data
    assert "database_version" in data["fields"]
    opts = data["fields"]["database_version"]
    assert len(opts) > 0
    assert "value" in opts[0]
    assert "label" in opts[0]


def test_get_options_nonexistent_returns_404():
    resp = client.get("/api/options/nonexistent")
    assert resp.status_code == 404
