"""Terraform validation tests — generates HCL from blueprints and runs terraform validate.

Requires terraform CLI on PATH. Tests are skipped if terraform is not available.
"""

import os
import shutil
import subprocess
import tempfile

import pytest

from core.schemas.base import Envelope
from core.terraform.generator import generate_terraform


_HAS_TERRAFORM = shutil.which("terraform") is not None

pytestmark = pytest.mark.skipif(not _HAS_TERRAFORM, reason="terraform CLI not on PATH")


VARIABLES_TF = """\
variable "gcp_project_id" {
  default = "test-project"
}
variable "gcp_region" {
  default = "us-central1"
}
variable "environment" {
  default = "dev"
}
"""

# Minimal provider block so terraform validate accepts google_ resources
PROVIDER_TF = """\
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = ">= 5.0"
    }
  }
}
"""


def _global(project_id="test-project", region="us-central1", env="dev"):
    return {"project_id": project_id, "region": region, "environment": env}


def _node(name, node_type, config=None, depends_on=None):
    d = {"name": name, "type": node_type, "config": config or {}}
    if depends_on:
        d["depends_on"] = depends_on
    return d


def _validate_blueprint(nodes, init=True):
    """Generate TF from a blueprint and run terraform validate.

    Returns (success: bool, stderr: str).
    """
    envelope = Envelope.model_validate({
        "global": _global(),
        "nodes": nodes,
    })
    files = generate_terraform(envelope)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Write generated HCL (includes provider.tf and variables.tf)
        for filename, content in files.items():
            with open(os.path.join(tmpdir, filename), "w") as f:
                f.write(content)

        if init:
            result = subprocess.run(
                ["terraform", "init", "-backend=false", "-no-color"],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                return False, f"terraform init failed:\n{result.stderr}"

        result = subprocess.run(
            ["terraform", "validate", "-no-color"],
            cwd=tmpdir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.returncode == 0, result.stdout + result.stderr


class TestTerraformValidate:
    """Each test generates a real blueprint, writes HCL, runs terraform validate."""

    def test_vpc_only(self):
        ok, output = _validate_blueprint([
            _node("my-vpc", "vpc", {"auto_create_subnetworks": False}),
        ])
        assert ok, output

    def test_vpc_subnet_chain(self):
        ok, output = _validate_blueprint([
            _node("my-vpc", "vpc", {"auto_create_subnetworks": False}),
            _node("my-subnet", "subnet", {
                "ip_cidr_range": "10.0.0.0/24",
                "region": "us-central1",
                "network": "my-vpc",
            }, depends_on=["my-vpc"]),
        ])
        assert ok, output

    def test_service_account(self):
        ok, output = _validate_blueprint([
            _node("test-sa", "service_account", {"account_id": "test-service-acct"}),
        ])
        assert ok, output

    def test_cloud_run_minimal(self):
        ok, output = _validate_blueprint([
            _node("test-sa", "service_account", {"account_id": "test-service-acct"}),
            _node("my-service", "cloud_run", {
                "image": "us-docker.pkg.dev/cloudrun/container/hello",
                "service_account": "my-sa",
            }, depends_on=["test-sa"]),
        ])
        assert ok, output

    def test_cloud_run_full(self):
        ok, output = _validate_blueprint([
            _node("test-sa", "service_account", {"account_id": "test-service-acct"}),
            _node("my-service", "cloud_run", {
                "image": "us-docker.pkg.dev/cloudrun/container/hello",
                "service_account": "my-sa",
                "description": "Test service",
                "cpu": "2",
                "memory": "1Gi",
                "min_instances": 1,
                "max_instances": 5,
                "port": 8080,
                "ingress": "INGRESS_TRAFFIC_ALL",
                "execution_environment": "EXECUTION_ENVIRONMENT_GEN2",
                "labels": {"team": "backend"},
            }, depends_on=["test-sa"]),
        ])
        assert ok, output

    def test_cloud_run_job(self):
        ok, output = _validate_blueprint([
            _node("test-sa", "service_account", {"account_id": "test-service-acct"}),
            _node("my-job", "cloud_run_job", {
                "image": "us-docker.pkg.dev/cloudrun/container/job",
                "service_account": "my-sa",
                "task_count": 3,
                "parallelism": 2,
            }, depends_on=["test-sa"]),
        ])
        assert ok, output

    def test_cloud_function(self):
        ok, output = _validate_blueprint([
            _node("test-sa", "service_account", {"account_id": "my-func-sa"}),
            _node("my-func", "cloud_function", {
                "runtime": "python312",
                "entry_point": "main",
                "service_account": "my-sa",
                "source_bucket": "my-source-bucket",
                "source_object": "source.zip",
            }, depends_on=["test-sa"]),
        ])
        assert ok, output

    def test_cloud_sql(self):
        ok, output = _validate_blueprint([
            _node("my-db", "cloud_sql", {
                "database_version": "POSTGRES_15",
                "tier": "db-f1-micro",
            }),
        ])
        assert ok, output

    def test_firestore(self):
        ok, output = _validate_blueprint([
            _node("my-fs", "firestore", {
                "location_id": "nam5",
            }),
        ])
        assert ok, output

    def test_bigquery(self):
        ok, output = _validate_blueprint([
            _node("my-bq", "bigquery", {
                "dataset_id": "my_dataset",
                "location": "US",
            }),
        ])
        assert ok, output

    def test_pubsub(self):
        ok, output = _validate_blueprint([
            _node("my-topic", "pubsub_topic", {}),
            _node("my-sub", "pubsub_subscription", {
                "topic": "my-topic",
            }, depends_on=["my-topic"]),
        ])
        assert ok, output

    def test_gcs_bucket(self):
        ok, output = _validate_blueprint([
            _node("my-bucket", "gcs_bucket", {"location": "US"}),
        ])
        assert ok, output

    def test_secret_manager(self):
        ok, output = _validate_blueprint([
            _node("my-secret", "secret_manager", {"secret_id": "my-secret"}),
        ])
        assert ok, output

    def test_full_stack(self):
        """Full multi-resource blueprint — the real integration test."""
        ok, output = _validate_blueprint([
            _node("my-vpc", "vpc", {"auto_create_subnetworks": False}),
            _node("my-subnet", "subnet", {
                "ip_cidr_range": "10.0.0.0/24",
                "region": "us-central1",
                "network": "my-vpc",
            }, depends_on=["my-vpc"]),
            _node("test-sa", "service_account", {"account_id": "test-service-acct"}),
            _node("my-db", "cloud_sql", {
                "database_version": "POSTGRES_15",
                "tier": "db-f1-micro",
            }, depends_on=["my-vpc"]),
            _node("my-fs", "firestore", {"location_id": "nam5"}),
            _node("my-bucket", "gcs_bucket", {"location": "US"}),
            _node("my-topic", "pubsub_topic", {}),
            _node("my-secret", "secret_manager", {"secret_id": "api-key"}),
            _node("my-service", "cloud_run", {
                "image": "us-docker.pkg.dev/cloudrun/container/hello",
                "service_account": "my-sa",
                "public": True,
            }, depends_on=["my-sa", "my-db", "my-fs", "my-bucket"]),
        ])
        assert ok, output
