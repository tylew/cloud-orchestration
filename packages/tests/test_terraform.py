"""Terraform generation and preview tests."""

from packages.core.terraform.generator import generate_terraform, preview_resources
from packages.core.schemas.base import Envelope


class TestGenerateTerraform:
    def test_produces_provider_and_variables(self, minimal_envelope):
        files = generate_terraform(minimal_envelope)
        assert "provider.tf" in files
        assert "variables.tf" in files
        assert "hashicorp/google" in files["provider.tf"]
        assert "gcp_project_id" in files["variables.tf"]

    def test_produces_main_tf(self, minimal_envelope):
        files = generate_terraform(minimal_envelope)
        assert "main.tf" in files
        assert len(files["main.tf"]) > 0

    def test_single_vpc_node(self):
        data = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": "my-vpc", "type": "vpc", "config": {"auto_create_subnetworks": False}},
            ],
        }
        envelope = Envelope.model_validate(data)
        files = generate_terraform(envelope)
        assert "main.tf" in files
        assert "google_compute_network" in files["main.tf"]

    def test_multi_node_dependencies(self, complex_envelope):
        files = generate_terraform(complex_envelope)
        main = files["main.tf"]
        assert "google_compute_network" in main
        assert "google_sql_database_instance" in main

    def test_backend_tf_generated_when_config_present(self):
        data = {
            "global": {
                "project_id": "test", "region": "us-central1", "environment": "dev",
                "backend": {"type": "gcs", "bucket": "my-bucket", "prefix": "terraform/state"},
            },
            "nodes": [
                {"name": "my-vpc", "type": "vpc", "config": {"auto_create_subnetworks": False}},
            ],
        }
        envelope = Envelope.model_validate(data)
        files = generate_terraform(envelope)
        assert "backend.tf" in files
        assert "gcs" in files["backend.tf"]

    def test_no_backend_tf_without_config(self, minimal_envelope):
        files = generate_terraform(minimal_envelope)
        assert "backend.tf" not in files


class TestPreviewResources:
    def test_preview_lists_expected_resources(self, minimal_envelope):
        resources = preview_resources(minimal_envelope)
        types = {r["terraform_resource"] for r in resources}
        assert "google_compute_network" in types
        assert "google_service_account" in types
        assert "google_cloud_run_v2_service" in types

    def test_preview_count_matches_nodes_with_tf_resources(self, complex_envelope):
        resources = preview_resources(complex_envelope)
        assert len(resources) >= 7

    def test_nodes_without_terraform_resource_excluded(self):
        data = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": "ext-api", "type": "third_party_api", "config": {"base_url": "https://example.com", "provider": "example"}},
            ],
        }
        envelope = Envelope.model_validate(data)
        resources = preview_resources(envelope)
        assert len(resources) == 0
