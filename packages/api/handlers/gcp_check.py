"""GCP resource existence checks — GCS bucket validation."""

from __future__ import annotations

import json
import logging
import subprocess

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)


class CheckBucketRequest(BaseModel):
    bucket_name: str


class CheckResult(BaseModel):
    exists: bool
    message: str


def _gcloud_access_token() -> str | None:
    try:
        result = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _check_bucket(bucket_name: str) -> CheckResult:
    token = _gcloud_access_token()
    if not token:
        return CheckResult(exists=False, message="GCP auth expired — run: gcloud auth login")

    # SDK check
    try:
        from google.cloud import storage
        from google.oauth2.credentials import Credentials

        client = storage.Client(credentials=Credentials(token=token))
        bucket = client.bucket(bucket_name)
        if bucket.exists():
            return CheckResult(exists=True, message=f"Bucket '{bucket_name}' already exists")
        return CheckResult(exists=False, message=f"Bucket '{bucket_name}' available")
    except ImportError:
        pass
    except Exception as exc:
        msg = str(exc)
        if "403" in msg:
            return CheckResult(exists=True, message=f"Bucket '{bucket_name}' exists (no access)")

    # gcloud CLI fallback
    try:
        result = subprocess.run(
            ["gcloud", "storage", "buckets", "describe",
             f"gs://{bucket_name}", "--format=value(name)"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return CheckResult(exists=True, message=f"Bucket '{bucket_name}' already exists")
        stderr = result.stderr
        if "BucketNotFoundException" in stderr or "NOT_FOUND" in stderr or "not found" in stderr.lower():
            return CheckResult(exists=False, message=f"Bucket '{bucket_name}' available")
        if "AccessDeniedException" in stderr:
            return CheckResult(exists=True, message=f"Bucket '{bucket_name}' exists (no access)")
    except Exception:
        pass

    return CheckResult(exists=False, message="Cannot verify — run: gcloud auth login")


@router.get("/gcp/zones")
async def list_zones():
    """List available GCP zones/regions."""
    try:
        result = subprocess.run(
            ["gcloud", "compute", "zones", "list", "--format=json(name,region)"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            zones = json.loads(result.stdout)
            # Extract unique regions and all zones
            regions = sorted({z["region"].split("/")[-1] for z in zones if "region" in z})
            zone_names = sorted([z["name"] for z in zones])
            return {"regions": regions, "zones": zone_names}
    except Exception as exc:
        logger.warning("list-zones error: %s", exc)

    # Fallback: static list of common regions
    return {
        "regions": [
            "us-central1", "us-east1", "us-east4", "us-west1", "us-west2", "us-west3", "us-west4",
            "europe-west1", "europe-west2", "europe-west3", "europe-west4", "europe-west6",
            "asia-east1", "asia-east2", "asia-northeast1", "asia-northeast2", "asia-northeast3",
            "asia-south1", "asia-southeast1", "asia-southeast2",
            "australia-southeast1", "northamerica-northeast1", "southamerica-east1",
        ],
        "zones": [],
    }


@router.post("/gcp/check-bucket")
async def check_bucket(req: CheckBucketRequest) -> CheckResult:
    if not req.bucket_name or not req.bucket_name.strip():
        return CheckResult(exists=False, message="Bucket name is empty")
    return _check_bucket(req.bucket_name)
