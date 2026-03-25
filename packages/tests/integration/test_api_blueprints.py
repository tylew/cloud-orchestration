"""API layered tests — blueprint validation and CRUD."""

import pytest

pytestmark = pytest.mark.integration


class TestBlueprintValidation:
    def test_validate_valid_envelope(self, api_client, sample_envelope_data):
        response = api_client.post("/api/blueprints/validate", json=sample_envelope_data)
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True

    def test_validate_invalid_envelope_missing_global(self, api_client):
        response = api_client.post("/api/blueprints/validate", json={"nodes": []})
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False

    def test_validate_returns_issues_for_bad_deps(self, api_client):
        payload = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": "my-vpc", "type": "vpc", "config": {"auto_create_subnetworks": False},
                 "depends_on": ["ghost"]},
            ],
        }
        response = api_client.post("/api/blueprints/validate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["issues"]) >= 1

    def test_schema_validate_valid(self, api_client, sample_envelope_data):
        response = api_client.post("/api/schema/validate", json=sample_envelope_data)
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["node_count"] == 3

    def test_schema_validate_invalid(self, api_client):
        response = api_client.post("/api/schema/validate", json={"bad": "data"})
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
