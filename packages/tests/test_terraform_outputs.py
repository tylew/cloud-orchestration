"""Terraform output block generation and classification tests."""

import sys
import os

from packages.core.terraform.generator import generate_terraform
from packages.core.schemas.base import Envelope

# Import test helpers from conftest (same directory)
sys.path.insert(0, os.path.dirname(__file__))
from conftest import _global, _node


class TestOutputGeneration:
    """Tests that generate_terraform() produces correct outputs.tf content."""

    def test_outputs_tf_generated_for_cloud_run(self):
        data = {
            "global": _global(),
            "nodes": [
                _node("my-sa", "service_account", {"account_id": "my-sa"}),
                _node("my-service", "cloud_run", {
                    "image": "gcr.io/test/image:latest",
                    "service_account": "my-sa",
                }, depends_on=["my-sa"]),
            ],
        }
        envelope = Envelope.model_validate(data)
        files = generate_terraform(envelope)
        assert "outputs.tf" in files
        content = files["outputs.tf"]
        assert 'output "my-service_endpoint"' in content
        assert "google_cloud_run_v2_service.my-service.uri" in content

    def test_outputs_tf_generated_for_cloud_sql(self):
        data = {
            "global": _global(),
            "nodes": [
                _node("my-db", "cloud_sql", {
                    "database_version": "POSTGRES_15",
                    "tier": "db-f1-micro",
                }),
            ],
        }
        envelope = Envelope.model_validate(data)
        files = generate_terraform(envelope)
        assert "outputs.tf" in files
        content = files["outputs.tf"]
        assert 'output "my-db_connection_name"' in content
        assert "google_sql_database_instance.my-db.connection_name" in content
        assert 'output "my-db_private_ip"' in content
        assert "google_sql_database_instance.my-db.private_ip_address" in content

    def test_external_lb_uses_ip_suffix(self):
        data = {
            "global": _global(),
            "nodes": [
                _node("my-lb", "external_lb", {
                    "domain": "example.com",
                    "backends": [{"name": "my-svc", "type": "cloud_run"}],
                }),
            ],
        }
        envelope = Envelope.model_validate(data)
        files = generate_terraform(envelope)
        assert "outputs.tf" in files
        content = files["outputs.tf"]
        assert 'output "my-lb_ip_address"' in content
        assert "google_compute_global_address.my-lb_ip.address" in content

    def test_cloud_dns_name_servers(self):
        data = {
            "global": _global(),
            "nodes": [
                _node("my-zone", "cloud_dns", {
                    "dns_name": "example.com.",
                    "visibility": "public",
                }),
            ],
        }
        envelope = Envelope.model_validate(data)
        files = generate_terraform(envelope)
        assert "outputs.tf" in files
        content = files["outputs.tf"]
        assert 'output "my-zone_name_servers"' in content
        assert "google_dns_managed_zone.my-zone.name_servers" in content

    def test_no_outputs_tf_for_internal_only_blueprint(self):
        data = {
            "global": _global(),
            "nodes": [
                _node("my-vpc", "vpc", {"auto_create_subnetworks": False}),
                _node("my-subnet", "subnet", {
                    "ip_cidr_range": "10.0.0.0/24",
                    "region": "us-central1",
                    "network": "my-vpc",
                }, depends_on=["my-vpc"]),
                _node("my-conn", "vpc_connector", {
                    "ip_cidr_range": "10.8.0.0/28",
                    "network": "my-vpc",
                    "region": "us-central1",
                }, depends_on=["my-vpc"]),
            ],
        }
        envelope = Envelope.model_validate(data)
        files = generate_terraform(envelope)
        assert "outputs.tf" not in files

    def test_output_naming_convention(self):
        """Output names follow {node_name}_{registry_output_name} pattern."""
        data = {
            "global": _global(),
            "nodes": [
                _node("my-bucket", "gcs_bucket", {"location": "US"}),
            ],
        }
        envelope = Envelope.model_validate(data)
        files = generate_terraform(envelope)
        assert "outputs.tf" in files
        content = files["outputs.tf"]
        # GCS bucket has outputs: bucket, url
        assert 'output "my-bucket_url"' in content
        assert 'output "my-bucket_bucket"' in content

    def test_cloud_function_endpoint_output(self):
        """Cloud Function output uses nested service_config[0].uri."""
        data = {
            "global": _global(),
            "nodes": [
                _node("my-sa", "service_account", {"account_id": "my-sa"}),
                _node("my-func", "cloud_function", {
                    "runtime": "python312",
                    "entry_point": "main",
                    "service_account": "my-sa",
                }, depends_on=["my-sa"]),
            ],
        }
        envelope = Envelope.model_validate(data)
        files = generate_terraform(envelope)
        assert "outputs.tf" in files
        content = files["outputs.tf"]
        assert 'output "my-func_endpoint"' in content
        assert "google_cloudfunctions2_function.my-func.service_config[0].uri" in content

    def test_output_has_description(self):
        """Each output block includes a description field."""
        data = {
            "global": _global(),
            "nodes": [
                _node("my-sa", "service_account", {"account_id": "my-sa"}),
            ],
        }
        envelope = Envelope.model_validate(data)
        files = generate_terraform(envelope)
        assert "outputs.tf" in files
        content = files["outputs.tf"]
        assert 'description = "my-sa email"' in content


class TestOutputClassification:
    """Tests that internal-only types are excluded from outputs."""

    def test_vpc_excluded(self):
        data = {
            "global": _global(),
            "nodes": [
                _node("my-vpc", "vpc", {"auto_create_subnetworks": False}),
            ],
        }
        envelope = Envelope.model_validate(data)
        files = generate_terraform(envelope)
        assert "outputs.tf" not in files

    def test_subnet_excluded(self):
        data = {
            "global": _global(),
            "nodes": [
                _node("my-vpc", "vpc", {"auto_create_subnetworks": False}),
                _node("my-subnet", "subnet", {
                    "ip_cidr_range": "10.0.0.0/24",
                    "region": "us-central1",
                    "network": "my-vpc",
                }, depends_on=["my-vpc"]),
                _node("my-sa", "service_account", {"account_id": "my-sa"}),
            ],
        }
        envelope = Envelope.model_validate(data)
        files = generate_terraform(envelope)
        assert "outputs.tf" in files
        content = files["outputs.tf"]
        assert "my-subnet" not in content

    def test_vpc_connector_excluded(self):
        data = {
            "global": _global(),
            "nodes": [
                _node("my-vpc", "vpc", {"auto_create_subnetworks": False}),
                _node("my-conn", "vpc_connector", {
                    "ip_cidr_range": "10.8.0.0/28",
                    "network": "my-vpc",
                    "region": "us-central1",
                }, depends_on=["my-vpc"]),
                _node("my-sa", "service_account", {"account_id": "my-sa"}),
            ],
        }
        envelope = Envelope.model_validate(data)
        files = generate_terraform(envelope)
        assert "outputs.tf" in files
        content = files["outputs.tf"]
        assert "my-conn" not in content

    def test_service_account_email_included(self):
        data = {
            "global": _global(),
            "nodes": [
                _node("my-sa", "service_account", {"account_id": "my-sa"}),
            ],
        }
        envelope = Envelope.model_validate(data)
        files = generate_terraform(envelope)
        assert "outputs.tf" in files
        content = files["outputs.tf"]
        assert 'output "my-sa_email"' in content
        assert "google_service_account.my-sa.email" in content

    def test_mixed_blueprint_filters_correctly(self, output_test_envelope_data):
        envelope = Envelope.model_validate(output_test_envelope_data)
        files = generate_terraform(envelope)
        assert "outputs.tf" in files
        content = files["outputs.tf"]
        # Cloud Run and Cloud SQL should have outputs
        assert "my-service" in content
        assert "my-db" in content
        # VPC should NOT have outputs
        assert 'output "my-vpc' not in content
