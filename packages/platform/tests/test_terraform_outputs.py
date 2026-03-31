"""Terraform output block generation and classification tests."""

import sys
import os

from core.terraform.generator import generate_terraform
from core.schemas.base import Envelope

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


class TestCloudBuildOutput:
    """Tests for D-03: Cloud Build terraform output step."""

    def test_get_build_terraform_output_function_exists(self):
        from packages.platform.gcp.cloud_build import get_build_terraform_output
        import inspect
        sig = inspect.signature(get_build_terraform_output)
        assert "host_project_id" in sig.parameters
        assert "build_id" in sig.parameters

    def test_submit_terraform_build_has_output_step(self):
        """Verify the source code includes terraform output -json step."""
        import inspect
        from packages.platform.gcp import cloud_build
        source = inspect.getsource(cloud_build.submit_terraform_build)
        assert "terraform output -json" in source
        assert "outputs.json" in source

    def test_output_step_skipped_for_plan_only(self):
        """Verify plan_only mode guard exists."""
        import inspect
        from packages.platform.gcp import cloud_build
        source = inspect.getsource(cloud_build.submit_terraform_build)
        assert 'plan_only' in source


class TestOutputStorage:
    """Tests for D-04: Output parsing and Firestore storage."""

    def test_parse_terraform_outputs_flat(self):
        from packages.platform.deploy_orchestrator import _parse_terraform_outputs
        raw = {
            "my-service_endpoint": {"sensitive": False, "type": "string", "value": "https://example.run.app"},
            "my-db_connection_name": {"sensitive": False, "type": "string", "value": "proj:region:db"},
        }
        result = _parse_terraform_outputs(raw)
        assert result["outputs"]["my-service_endpoint"] == "https://example.run.app"
        assert result["outputs"]["my-db_connection_name"] == "proj:region:db"

    def test_parse_terraform_outputs_by_node(self):
        from packages.platform.deploy_orchestrator import _parse_terraform_outputs
        raw = {
            "my-service_endpoint": {"sensitive": False, "type": "string", "value": "https://example.run.app"},
            "my-db_ip": {"sensitive": False, "type": "string", "value": "10.0.0.1"},
        }
        result = _parse_terraform_outputs(raw)
        assert "my-service" in result["by_node"]
        assert result["by_node"]["my-service"]["endpoint"] == "https://example.run.app"
        assert "my-db" in result["by_node"]
        assert result["by_node"]["my-db"]["ip"] == "10.0.0.1"

    def test_parse_terraform_outputs_list_value(self):
        from packages.platform.deploy_orchestrator import _parse_terraform_outputs
        raw = {
            "my-zone_name_servers": {
                "sensitive": False,
                "type": ["list", "string"],
                "value": ["ns1.google.com.", "ns2.google.com."],
            },
        }
        result = _parse_terraform_outputs(raw)
        assert isinstance(result["outputs"]["my-zone_name_servers"], list)
        assert len(result["outputs"]["my-zone_name_servers"]) == 2

    def test_parse_terraform_outputs_empty(self):
        from packages.platform.deploy_orchestrator import _parse_terraform_outputs
        result = _parse_terraform_outputs({})
        assert result["outputs"] == {}
        assert result["by_node"] == {}

    def test_parse_terraform_outputs_by_node_multi_underscore(self):
        from packages.platform.deploy_orchestrator import _parse_terraform_outputs
        raw = {
            "my-zone_name_servers": {
                "sensitive": False, "type": ["list", "string"],
                "value": ["ns1.google.com.", "ns2.google.com."],
            },
            "my-db_connection_name": {
                "sensitive": False, "type": "string",
                "value": "proj:us-central1:my-db",
            },
            "my-db_private_ip": {
                "sensitive": False, "type": "string",
                "value": "10.0.0.5",
            },
        }
        result = _parse_terraform_outputs(raw, node_names=["my-zone", "my-db"])
        assert "my-zone" in result["by_node"]
        assert result["by_node"]["my-zone"]["name_servers"] == ["ns1.google.com.", "ns2.google.com."]
        assert "my-db" in result["by_node"]
        assert result["by_node"]["my-db"]["connection_name"] == "proj:us-central1:my-db"
        assert result["by_node"]["my-db"]["private_ip"] == "10.0.0.5"

    def test_parse_terraform_outputs_by_node_with_node_names(self):
        from packages.platform.deploy_orchestrator import _parse_terraform_outputs
        raw = {
            "my-service_endpoint": {
                "sensitive": False, "type": "string",
                "value": "https://example.run.app",
            },
        }
        result = _parse_terraform_outputs(raw, node_names=["my-service"])
        assert result["by_node"]["my-service"]["endpoint"] == "https://example.run.app"

    def test_parse_terraform_outputs_by_node_fallback_without_node_names(self):
        from packages.platform.deploy_orchestrator import _parse_terraform_outputs
        raw = {
            "my-service_endpoint": {
                "sensitive": False, "type": "string",
                "value": "https://example.run.app",
            },
        }
        # Call WITHOUT node_names -- should still work for simple cases via rsplit fallback
        result = _parse_terraform_outputs(raw)
        assert result["by_node"]["my-service"]["endpoint"] == "https://example.run.app"

    def test_save_env_outputs_function_exists(self):
        from packages.platform.store.deploys import save_env_outputs
        import inspect
        sig = inspect.signature(save_env_outputs)
        assert "tenant_id" in sig.parameters
        assert "project_ref_id" in sig.parameters
        assert "env_name" in sig.parameters
        assert "outputs" in sig.parameters
        assert "deploy_id" in sig.parameters

    def test_get_env_outputs_function_exists(self):
        from packages.platform.store.deploys import get_env_outputs
        import inspect
        sig = inspect.signature(get_env_outputs)
        assert "tenant_id" in sig.parameters
        assert "project_ref_id" in sig.parameters
        assert "env_name" in sig.parameters

    def test_update_deploy_status_accepts_terraform_outputs(self):
        import inspect
        from packages.platform.store.deploys import update_deploy_status
        sig = inspect.signature(update_deploy_status)
        assert "terraform_outputs" in sig.parameters


class TestMcpGetOutputs:
    """Tests for D-05: get_deploy_outputs MCP tool."""

    def test_get_deploy_outputs_tool_exists(self):
        from packages.mcp.tools.deploy import get_deploy_outputs
        import inspect
        sig = inspect.signature(get_deploy_outputs)
        assert "project_ref_id" in sig.parameters
        assert "env_name" in sig.parameters

    def test_get_deploy_outputs_default_env(self):
        from packages.mcp.tools.deploy import get_deploy_outputs
        import inspect
        sig = inspect.signature(get_deploy_outputs)
        assert sig.parameters["env_name"].default == "dev"

    def test_get_deploy_status_unchanged(self):
        """D-06: get_deploy_status must NOT include terraform_outputs."""
        import inspect
        from packages.mcp.tools.deploy import get_deploy_status
        source = inspect.getsource(get_deploy_status)
        assert "terraform_outputs" not in source
        assert "get_env_outputs" not in source
