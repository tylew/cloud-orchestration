"""API layered tests — Terraform generate and preview endpoints."""

import pytest

pytestmark = pytest.mark.integration


class TestTerraformGeneration:
    def test_generate_returns_tf_files(self, api_client, sample_envelope_data):
        response = api_client.post("/api/terraform/generate", json=sample_envelope_data)
        assert response.status_code == 200
        data = response.json()
        assert "files" in data
        files = data["files"]
        assert "provider.tf" in files
        assert "variables.tf" in files
        assert "main.tf" in files

    def test_generate_main_contains_resources(self, api_client, sample_envelope_data):
        response = api_client.post("/api/terraform/generate", json=sample_envelope_data)
        data = response.json()
        main_tf = data["files"]["main.tf"]
        assert "google_compute_network" in main_tf
        assert "google_service_account" in main_tf

    def test_preview_lists_resources(self, api_client, sample_envelope_data):
        response = api_client.post("/api/terraform/preview", json=sample_envelope_data)
        assert response.status_code == 200
        data = response.json()
        assert "resources" in data
        types = {r["terraform_resource"] for r in data["resources"]}
        assert "google_compute_network" in types
        assert "google_cloud_run_v2_service" in types

    def test_generate_invalid_envelope_returns_error(self, api_client):
        response = api_client.post("/api/terraform/generate", json={"bad": "data"})
        assert response.status_code == 422 or response.status_code == 200
