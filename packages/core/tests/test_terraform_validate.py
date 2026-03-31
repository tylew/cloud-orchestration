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


class TestTerraformValidateRichConfigs:
    """Tests for S01 schema additions — rich config fields across node types."""

    # ── Cloud Run ────────────────────────────────────────────────────

    def test_cloud_run_gpu(self):
        """Cloud Run with GPU and node_selector."""
        ok, output = _validate_blueprint([
            _node("gpu-service", "cloud_run", {
                "image": "us-docker.pkg.dev/cloudrun/container/hello",
                "service_account": "test@proj.iam.gserviceaccount.com",
                "gpu": "1",
                "node_selector": {"accelerator": "nvidia-l4"},
                "cpu": "4",
                "memory": "16Gi",
            }),
        ])
        assert ok, output

    def test_cloud_run_probes(self):
        """Cloud Run with liveness (http), startup (tcp), readiness (grpc) probes."""
        ok, output = _validate_blueprint([
            _node("probed-service", "cloud_run", {
                "image": "us-docker.pkg.dev/cloudrun/container/hello",
                "service_account": "test@proj.iam.gserviceaccount.com",
                "liveness_probe": {
                    "http_get": {"path": "/healthz", "port": 8080},
                    "initial_delay_seconds": 5,
                    "period_seconds": 15,
                    "timeout_seconds": 3,
                    "failure_threshold": 3,
                },
                "startup_probe": {
                    "tcp_socket": {"port": 8080},
                    "initial_delay_seconds": 0,
                    "period_seconds": 5,
                    "timeout_seconds": 2,
                    "failure_threshold": 12,
                },
                "readiness_probe": {
                    "grpc": {"port": 8080, "service": "health.v1"},
                    "timeout_seconds": 1,
                    "period_seconds": 10,
                    "failure_threshold": 3,
                    "success_threshold": 2,
                },
            }),
        ])
        assert ok, output

    def test_cloud_run_volumes(self):
        """Cloud Run with cloud_sql_instance, gcs, empty_dir, and secret volumes."""
        ok, output = _validate_blueprint([
            _node("vol-service", "cloud_run", {
                "image": "us-docker.pkg.dev/cloudrun/container/hello",
                "service_account": "test@proj.iam.gserviceaccount.com",
                "volumes": [
                    {
                        "name": "cloudsql",
                        "cloud_sql_instance": {
                            "instances": ["test-project:us-central1:my-db"],
                        },
                    },
                    {
                        "name": "gcs-data",
                        "gcs": {
                            "bucket": "my-data-bucket",
                            "read_only": True,
                        },
                    },
                    {
                        "name": "scratch",
                        "empty_dir": {
                            "medium": "MEMORY",
                            "size_limit": "256Mi",
                        },
                    },
                    {
                        "name": "app-secret",
                        "secret": {
                            "secret": "my-api-key",
                            "default_mode": 292,
                            "items": [
                                {"version": "latest", "path": "api-key.txt"},
                            ],
                        },
                    },
                ],
                "volume_mounts": [
                    {"name": "gcs-data", "mount_path": "/data"},
                    {"name": "scratch", "mount_path": "/tmp/scratch"},
                    {"name": "app-secret", "mount_path": "/secrets"},
                ],
            }),
        ])
        assert ok, output

    def test_cloud_run_service_fields(self):
        """Cloud Run with description, launch_stage, ingress, labels, annotations.

        NOTE: annotation keys containing dots (e.g. 'run.googleapis.com/cpu-throttling')
        are a known template bug — the template renders them unquoted, causing Terraform
        to interpret dots as attribute access. The test uses simple keys to validate the
        annotation rendering path works; a separate xfail test covers the dots bug.
        """
        ok, output = _validate_blueprint([
            _node("fancy-service", "cloud_run", {
                "image": "us-docker.pkg.dev/cloudrun/container/hello",
                "service_account": "test@proj.iam.gserviceaccount.com",
                "description": "A fully loaded test service",
                "launch_stage": "GA",
                "ingress": "INGRESS_TRAFFIC_INTERNAL_ONLY",
                "labels": {"team": "platform", "cost-center": "infra"},
                "annotations": {"cpu-throttling": "false"},
            }),
        ])
        assert ok, output

    @pytest.mark.xfail(reason="TEMPLATE BUG: annotation keys with dots rendered unquoted in cloud_run.tf.j2")
    def test_cloud_run_annotations_dotted_keys(self):
        """Cloud Run annotations with dotted keys — exposes template quoting bug."""
        ok, output = _validate_blueprint([
            _node("dotted-service", "cloud_run", {
                "image": "us-docker.pkg.dev/cloudrun/container/hello",
                "service_account": "test@proj.iam.gserviceaccount.com",
                "annotations": {"run.googleapis.com/cpu-throttling": "false"},
            }),
        ])
        assert ok, output

    # ── Cloud Run Job ────────────────────────────────────────────────

    def test_cloud_run_job_gpu_encryption(self):
        """Cloud Run Job with GPU and encryption_key."""
        ok, output = _validate_blueprint([
            _node("gpu-job", "cloud_run_job", {
                "image": "us-docker.pkg.dev/cloudrun/container/job",
                "service_account": "test@proj.iam.gserviceaccount.com",
                "gpu": "1",
                "node_selector": {"accelerator": "nvidia-l4"},
                "encryption_key": "projects/test/locations/us/keyRings/kr/cryptoKeys/key",
                "cpu": "4",
                "memory": "16Gi",
            }),
        ])
        assert ok, output

    # ── Cloud Function ───────────────────────────────────────────────

    def test_cloud_function_build_config(self):
        """Cloud Function with build_config (docker_repository, worker_pool, env vars)."""
        ok, output = _validate_blueprint([
            _node("build-func", "cloud_function", {
                "runtime": "python312",
                "entry_point": "handler",
                "service_account": "test@proj.iam.gserviceaccount.com",
                "source_bucket": "my-source-bucket",
                "source_object": "source.zip",
                "build_config": {
                    "docker_repository": "projects/test/locations/us-central1/repositories/my-repo",
                    "worker_pool": "projects/test/locations/us-central1/workerPools/my-pool",
                    "environment_variables": {
                        "GOPROXY": "off",
                        "PIP_INDEX_URL": "https://pypi.org/simple",
                    },
                },
            }),
        ])
        assert ok, output

    def test_cloud_function_description_kms(self):
        """Cloud Function with description and kms_key_name."""
        ok, output = _validate_blueprint([
            _node("secure-func", "cloud_function", {
                "runtime": "nodejs20",
                "entry_point": "helloWorld",
                "service_account": "test@proj.iam.gserviceaccount.com",
                "source_bucket": "my-source-bucket",
                "source_object": "source.zip",
                "description": "A CMEK-protected function",
                "kms_key_name": "projects/test/locations/us/keyRings/kr/cryptoKeys/key",
            }),
        ])
        assert ok, output

    # ── Cloud SQL ────────────────────────────────────────────────────

    @pytest.mark.xfail(reason="TEMPLATE BUG: cloud_sql.tf.j2 renders require_ssl which is removed in google provider >= 6.x, and missing authorized_networks block")
    def test_cloud_sql_authorized_networks(self):
        """Cloud SQL with ip_configuration.authorized_networks.

        Exposes two template bugs:
        1. require_ssl rendered unconditionally (removed in google provider >= 6.x)
        2. authorized_networks not rendered in ip_configuration block
        """
        ok, output = _validate_blueprint([
            _node("auth-db", "cloud_sql", {
                "database_version": "POSTGRES_15",
                "tier": "db-f1-micro",
                "ip_configuration": {
                    "ipv4_enabled": True,
                    "require_ssl": False,
                    "authorized_networks": [
                        {"name": "office", "value": "203.0.113.0/24"},
                        {"name": "vpn", "value": "198.51.100.0/24"},
                    ],
                },
            }),
        ])
        assert ok, output

    def test_cloud_sql_labels_edition_location(self):
        """Cloud SQL with user_labels, edition, and location_preference."""
        ok, output = _validate_blueprint([
            _node("labeled-db", "cloud_sql", {
                "database_version": "POSTGRES_15",
                "tier": "db-custom-2-7680",
                "edition": "ENTERPRISE",
                "user_labels": {"team": "data", "env": "dev"},
                "location_preference": {"zone": "us-central1-a"},
            }),
        ])
        assert ok, output

    # ── Firestore ────────────────────────────────────────────────────

    def test_firestore_edition_cmek_tags(self):
        """Firestore with database_edition, cmek_config, and tags."""
        ok, output = _validate_blueprint([
            _node("secure-fs", "firestore", {
                "location_id": "nam5",
                "database_edition": "ENTERPRISE",
                "cmek_config": {
                    "kms_key_name": "projects/test/locations/us/keyRings/kr/cryptoKeys/key",
                },
                "tags": {"env": "production", "compliance": "pci"},
            }),
        ])
        assert ok, output

    # ── VPC Connector ────────────────────────────────────────────────

    @pytest.mark.xfail(reason="TEMPLATE BUG: vpc_connector.tf.j2 renders both throughput and instances unconditionally — they conflict in google provider")
    def test_vpc_connector(self):
        """VPC Connector standalone — exercises vpc_connector.tf.j2.

        Exposes template bug: min/max_throughput and min/max_instances are mutually
        exclusive in the google provider, but the template renders all four.
        """
        ok, output = _validate_blueprint([
            _node("my-vpc", "vpc", {"auto_create_subnetworks": False}),
            _node("my-connector", "vpc_connector", {
                "region": "us-central1",
                "network": "my-vpc",
                "ip_cidr_range": "10.8.0.0/28",
                "min_throughput": 200,
                "max_throughput": 300,
                "machine_type": "e2-micro",
                "min_instances": 2,
                "max_instances": 3,
            }, depends_on=["my-vpc"]),
        ])
        assert ok, output

    # ── Cloud DNS ────────────────────────────────────────────────────

    def test_cloud_dns(self):
        """Cloud DNS standalone — exercises cloud_dns.tf.j2."""
        ok, output = _validate_blueprint([
            _node("my-zone", "cloud_dns", {
                "dns_name": "example.com.",
                "visibility": "public",
                "description": "Test DNS zone",
                "dnssec_enabled": True,
                "records": [
                    {
                        "name": "@",
                        "type": "A",
                        "ttl": 300,
                        "rrdatas": ["1.2.3.4"],
                    },
                    {
                        "name": "www",
                        "type": "CNAME",
                        "ttl": 300,
                        "rrdatas": ["example.com."],
                    },
                ],
            }),
        ])
        assert ok, output

    # ── Bigtable ─────────────────────────────────────────────────────

    def test_bigtable_display_name(self):
        """Bigtable with display_name set."""
        ok, output = _validate_blueprint([
            _node("my-bt", "bigtable", {
                "instance_id": "my-bigtable-inst",
                "display_name": "My Bigtable Instance",
                "deletion_protection": False,
                "cluster": {
                    "cluster_id": "my-bt-c1",
                    "zone": "us-central1-a",
                    "num_nodes": 1,
                    "storage_type": "SSD",
                },
            }),
        ])
        assert ok, output

    # ── Cloud Tasks Queue ────────────────────────────────────────────

    def test_cloud_task_queue(self):
        """Cloud Tasks Queue standalone — exercises cloud_task_queue.tf.j2."""
        ok, output = _validate_blueprint([
            _node("my-queue", "cloud_task_queue", {
                "location": "us-central1",
                "rate_limits": {
                    "max_dispatches_per_second": 100,
                    "max_concurrent_dispatches": 10,
                },
                "retry_config": {
                    "max_attempts": 5,
                    "min_backoff": "1s",
                    "max_backoff": "60s",
                    "max_doublings": 4,
                },
            }),
        ])
        assert ok, output

    # ── PubSub Schema ────────────────────────────────────────────────

    def test_pubsub_schema(self):
        """PubSub Schema standalone — exercises pubsub_schema.tf.j2."""
        ok, output = _validate_blueprint([
            _node("my-schema", "pubsub_schema", {
                "type": "AVRO",
                "definition": '{"type": "record", "name": "Event", "fields": [{"name": "id", "type": "string"}]}',
            }),
        ])
        assert ok, output
