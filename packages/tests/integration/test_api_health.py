"""API layered tests — health, config, schema endpoints."""

import pytest

pytestmark = pytest.mark.integration


class TestHealthEndpoints:
    def test_health_returns_ok(self, api_client):
        response = api_client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_me_returns_dev_user(self, api_client):
        response = api_client.get("/api/me")
        assert response.status_code == 200
        data = response.json()
        assert "tenant_id" in data
        assert "email" in data

    def test_schema_types_returns_all_node_types(self, api_client):
        response = api_client.get("/api/schema/types")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 23
        assert "cloud_run" in data
        assert "firestore" in data
        assert "vpc" in data

    def test_schema_type_has_expected_fields(self, api_client):
        response = api_client.get("/api/schema/types")
        data = response.json()
        cr = data["cloud_run"]
        assert cr["label"] == "Cloud Run"
        assert cr["category"] == "Compute"
        assert cr["is_compute"] is True
        assert cr["terraform_resource"] == "google_cloud_run_v2_service"
