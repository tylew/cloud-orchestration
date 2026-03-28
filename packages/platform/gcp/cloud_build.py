"""Cloud Build API wrapper for submitting terraform and container build jobs."""

import hashlib
import io
import logging
import os
import tarfile
import time
from datetime import datetime, timezone

from google.cloud import storage
from google.cloud.devtools import cloudbuild_v1

log = logging.getLogger(__name__)


def _get_cb_client() -> cloudbuild_v1.CloudBuildClient:
    return cloudbuild_v1.CloudBuildClient()


def _get_storage_client() -> storage.Client:
    return storage.Client()


def submit_terraform_build(
    host_project_id: str,
    target_project_id: str,
    env_name: str,
    tf_files: dict[str, str],
    tf_bucket: str,
    region: str,
    mode: str = "plan_and_apply",
    tenant_id: str = "",
    project_ref_id: str = "",
) -> dict:
    """Submit a Cloud Build job that runs terraform plan + apply.

    1. Create tarball of tf_files in memory
    2. Upload to gs://{CB_SOURCE_BUCKET}/{target_project_id}/{env_name}/{timestamp}.tar.gz
    3. Submit Cloud Build via google-cloud-build Python client
    4. Return {"build_id": "...", "log_url": "..."}
    """
    cb_source_bucket = os.environ.get("CB_SOURCE_BUCKET", f"{host_project_id}-cb-source")
    tf_builder_sa = os.environ.get("TF_BUILDER_SA", f"pl4m-tf-builder@{host_project_id}.iam.gserviceaccount.com")

    # Derive TF state prefix — supports shared bucket with tenant/project isolation
    tf_prefix = f"terraform/{env_name}"
    if tenant_id and project_ref_id:
        tf_prefix = f"{tenant_id}/{project_ref_id}/{env_name}"

    # Override variables.tf with defaults matching the hardcoded provider values
    tf_files["variables.tf"] = f"""\
variable "gcp_project_id" {{
  type    = string
  default = "{target_project_id}"
}}

variable "gcp_region" {{
  type    = string
  default = "{region}"
}}

variable "environment" {{
  type    = string
  default = "{env_name}"
}}

variable "tf_state_bucket" {{
  type    = string
  default = "{tf_bucket}"
}}

variable "cb_source_bucket" {{
  type    = string
  default = "{cb_source_bucket}"
}}
"""

    # Write provider.tf into the tf_files (always overwrite with hardcoded values)
    if True:
        tf_files["provider.tf"] = f"""\
terraform {{
  required_version = ">= 1.5"
  backend "gcs" {{
    bucket = "{tf_bucket}"
    prefix = "{tf_prefix}"
  }}
  required_providers {{
    google = {{
      source  = "hashicorp/google"
      version = "~> 5.0"
    }}
  }}
}}

provider "google" {{
  project = "{target_project_id}"
  region  = "{region}"
}}
"""

    # 1. Create tarball in memory
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for filename, content in tf_files.items():
            data = content.encode("utf-8")
            info = tarfile.TarInfo(name=filename)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    buf.seek(0)

    # 2. Upload to GCS
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    blob_path = f"{target_project_id}/{env_name}/{timestamp}.tar.gz"
    client = _get_storage_client()
    bucket = client.bucket(cb_source_bucket)
    blob = bucket.blob(blob_path)
    blob.upload_from_file(buf, content_type="application/gzip")
    log.info("Uploaded TF source to gs://%s/%s", cb_source_bucket, blob_path)

    # 3. Build the Cloud Build config
    if mode == "plan_only":
        tf_command = "terraform init -no-color && terraform plan -no-color | tee /workspace/plan.txt"
    else:
        tf_command = (
            "terraform init -no-color && "
            "terraform plan -out=tfplan -no-color | tee /workspace/plan.txt && "
            "terraform apply -auto-approve tfplan -no-color | tee /workspace/apply.txt"
        )

    # Build steps dynamically to support conditional terraform output capture
    steps = [
        cloudbuild_v1.BuildStep(
            name="hashicorp/terraform:1.7.5",
            entrypoint="sh",
            args=["-c", tf_command],
        ),
    ]

    # Capture terraform output JSON (plan_and_apply mode only) (D-03)
    if mode != "plan_only":
        steps.append(
            cloudbuild_v1.BuildStep(
                name="hashicorp/terraform:1.7.5",
                entrypoint="sh",
                args=["-c", "terraform output -json > /workspace/outputs.json 2>/dev/null || echo '{}' > /workspace/outputs.json"],
            )
        )

    # Copy results to GCS (includes outputs.json when available)
    steps.append(
        cloudbuild_v1.BuildStep(
            name="gcr.io/cloud-builders/gsutil",
            entrypoint="sh",
            args=[
                "-c",
                (
                    f"gsutil cp /workspace/plan.txt gs://{cb_source_bucket}/results/$BUILD_ID/plan.txt 2>/dev/null; "
                    f"gsutil cp /workspace/apply.txt gs://{cb_source_bucket}/results/$BUILD_ID/apply.txt 2>/dev/null; "
                    f"gsutil cp /workspace/outputs.json gs://{cb_source_bucket}/results/$BUILD_ID/outputs.json 2>/dev/null; "
                    "true"
                ),
            ],
        ),
    )

    build = cloudbuild_v1.Build(
        source=cloudbuild_v1.Source(
            storage_source=cloudbuild_v1.StorageSource(
                bucket=cb_source_bucket,
                object_=blob_path,
            )
        ),
        steps=steps,
        service_account=f"projects/{host_project_id}/serviceAccounts/{tf_builder_sa}",
        options=cloudbuild_v1.BuildOptions(
            logging=cloudbuild_v1.BuildOptions.LoggingMode.CLOUD_LOGGING_ONLY,
        ),
        timeout={"seconds": 1200},
    )

    # Submit
    cb_client = _get_cb_client()
    operation = cb_client.create_build(project_id=host_project_id, build=build)
    # The operation metadata contains the build
    build_result = operation.metadata.build
    build_id = build_result.id
    log_url = build_result.log_url

    log.info("Submitted Cloud Build %s for %s/%s", build_id, target_project_id, env_name)
    return {"build_id": build_id, "log_url": log_url}


def get_build_status(host_project_id: str, build_id: str) -> dict:
    """Poll Cloud Build API. Return {status, start_time, finish_time, steps}."""
    cb_client = _get_cb_client()
    build = cb_client.get_build(project_id=host_project_id, id=build_id)

    status_name = cloudbuild_v1.Build.Status(build.status).name

    result = {
        "status": status_name,
        "start_time": build.start_time.isoformat() if build.start_time else None,
        "finish_time": build.finish_time.isoformat() if build.finish_time else None,
        "steps": [],
    }
    for step in build.steps:
        result["steps"].append({
            "name": step.name,
            "status": cloudbuild_v1.Build.Status(step.status).name if step.status else "QUEUED",
        })
    return result


def get_build_plan_output(host_project_id: str, build_id: str) -> str | None:
    """Fetch the terraform plan output from GCS results bucket."""
    cb_source_bucket = os.environ.get("CB_SOURCE_BUCKET", f"{host_project_id}-cb-source")
    try:
        client = _get_storage_client()
        bucket = client.bucket(cb_source_bucket)
        blob = bucket.blob(f"results/{build_id}/plan.txt")
        return blob.download_as_text()
    except Exception:
        log.warning("Could not fetch plan output for build %s", build_id)
        return None


def get_build_apply_output(host_project_id: str, build_id: str) -> str | None:
    """Fetch the terraform apply output from GCS results bucket."""
    cb_source_bucket = os.environ.get("CB_SOURCE_BUCKET", f"{host_project_id}-cb-source")
    try:
        client = _get_storage_client()
        bucket = client.bucket(cb_source_bucket)
        blob = bucket.blob(f"results/{build_id}/apply.txt")
        return blob.download_as_text()
    except Exception:
        log.warning("Could not fetch apply output for build %s", build_id)
        return None


def get_build_terraform_output(host_project_id: str, build_id: str) -> dict | None:
    """Fetch the terraform output JSON from GCS results bucket (D-03)."""
    import json
    cb_source_bucket = os.environ.get("CB_SOURCE_BUCKET", f"{host_project_id}-cb-source")
    try:
        client = _get_storage_client()
        bucket = client.bucket(cb_source_bucket)
        blob = bucket.blob(f"results/{build_id}/outputs.json")
        raw = blob.download_as_text()
        return json.loads(raw)
    except Exception:
        log.warning("Could not fetch terraform output for build %s", build_id)
        return None


# ── Container Build Functions ─────────────────────────────────────


def compute_image_uri(target_project_id: str, region: str, node_name: str, tag: str = "latest") -> str:
    """Artifact Registry image URI. Format: {region}-docker.pkg.dev/{project}/{repo}/{image}:{tag}"""
    repo_name = "platform-builds"
    return f"{region}-docker.pkg.dev/{target_project_id}/{repo_name}/{node_name}:{tag}"


def compute_source_hash(files: dict[str, str]) -> str:
    """Deterministic SHA-256 hash of source files for dirty state detection (per D-07)."""
    hasher = hashlib.sha256()
    for filename in sorted(files.keys()):
        hasher.update(filename.encode())
        hasher.update(files[filename].encode())
    return hasher.hexdigest()[:12]


def submit_container_build(
    host_project_id: str,
    target_project_id: str,
    env_name: str,
    node_name: str,
    source_files: dict[str, str],
    image_uri: str,
) -> dict:
    """Submit Cloud Build to build Docker image and push to Artifact Registry (per D-01, D-02).
    Uses Cloud Build `images` field for automatic push -- no separate docker push step needed.
    Returns {"build_id": "...", "log_url": "..."}
    """
    cb_source_bucket = os.environ.get("CB_SOURCE_BUCKET", f"{host_project_id}-cb-source")
    tf_builder_sa = os.environ.get("TF_BUILDER_SA", f"pl4m-tf-builder@{host_project_id}.iam.gserviceaccount.com")

    # 1. Tarball (same pattern as submit_terraform_build)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for filename, content in source_files.items():
            data = content.encode("utf-8")
            info = tarfile.TarInfo(name=filename)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    buf.seek(0)

    # 2. Upload to GCS
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    blob_path = f"{target_project_id}/builds/{env_name}/{node_name}/{timestamp}.tar.gz"
    client = _get_storage_client()
    bucket = client.bucket(cb_source_bucket)
    blob = bucket.blob(blob_path)
    blob.upload_from_file(buf, content_type="application/gzip")
    log.info("Uploaded build source to gs://%s/%s", cb_source_bucket, blob_path)

    # 3. Cloud Build config with docker build + images field for auto-push
    build = cloudbuild_v1.Build(
        source=cloudbuild_v1.Source(
            storage_source=cloudbuild_v1.StorageSource(
                bucket=cb_source_bucket,
                object_=blob_path,
            )
        ),
        steps=[
            cloudbuild_v1.BuildStep(
                name="gcr.io/cloud-builders/docker",
                args=["build", "-t", image_uri, "."],
            ),
        ],
        images=[image_uri],  # Auto-push to AR after successful build
        service_account=f"projects/{host_project_id}/serviceAccounts/{tf_builder_sa}",
        options=cloudbuild_v1.BuildOptions(
            logging=cloudbuild_v1.BuildOptions.LoggingMode.CLOUD_LOGGING_ONLY,
        ),
        timeout={"seconds": 600},
    )

    cb_client = _get_cb_client()
    operation = cb_client.create_build(project_id=host_project_id, build=build)
    build_result = operation.metadata.build
    return {"build_id": build_result.id, "log_url": build_result.log_url}
