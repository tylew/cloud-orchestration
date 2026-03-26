"""GCP project bootstrap — Python port of infra/bootstrap.sh."""

import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass, field

import google.auth
import google.auth.transport.requests
from google.api_core import exceptions as gcp_exceptions
from google.cloud import storage
from google.cloud.billing_v1 import CloudBillingClient
from google.cloud.billing_v1.types import ProjectBillingInfo
from google.cloud.resourcemanager_v3 import (
    FoldersClient,
    Project,
    ProjectsClient,
)
from google.cloud.resourcemanager_v3.types import (
    CreateFolderRequest,
    CreateProjectRequest,
    Folder,
    GetProjectRequest,
    ListFoldersRequest,
)
from google.cloud.service_usage_v1 import ServiceUsageClient
from google.cloud.service_usage_v1.types import (
    BatchEnableServicesRequest,
    ListServicesRequest,
)

log = logging.getLogger(__name__)

BOOTSTRAP_APIS = [
    "storage.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "run.googleapis.com",
    "firestore.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "identitytoolkit.googleapis.com",
    "firebase.googleapis.com",
    "firebasedatabase.googleapis.com",
]


@dataclass
class BootstrapResult:
    project_id: str
    success: bool = True
    steps: list[dict] = field(default_factory=list)
    error: str | None = None


def generate_project_id(display_name: str, environment: str = "") -> str:
    """Generate a GCP-compliant project ID from a display name.

    Format: {slug}-{env}-{uuid8}
    GCP limit: 30 chars, min 6 chars.
    The display name can be any length — we truncate the slug portion.
    """
    env_tag = environment[:4] if environment else "pl4m"
    uid = uuid.uuid4().hex[:8]
    # slug-env-uid: need room for env tag + uid + 2 dashes
    prefix_len = 30 - len(env_tag) - 1 - 8 - 1
    slug = re.sub(r'[^a-z0-9-]', '-', display_name.lower())
    slug = re.sub(r'-+', '-', slug).strip('-')[:prefix_len]
    if slug:
        return f"{slug}-{env_tag}-{uid}"
    return f"p-{env_tag}-{uid}"


def generate_unique_project_id(display_name: str, max_retries: int = 5, environment: str = "") -> str:
    """Generate a unique GCP project ID, retrying on collision.

    Returns project_id string. TF state is stored in a shared host bucket,
    so no per-project bucket is needed.
    """
    for _ in range(max_retries):
        candidate = generate_project_id(display_name, environment)
        if validate_project_exists(candidate):
            log.info("Project %s already exists, retrying", candidate)
            continue
        return candidate
    return generate_project_id(display_name, environment)


def validate_project_exists(project_id: str) -> bool:
    try:
        client = ProjectsClient()
        client.get_project(name=f"projects/{project_id}")
        return True
    except gcp_exceptions.NotFound:
        return False
    except Exception as e:
        log.warning("Could not check project existence for %s: %s", project_id, e)
        return False


def check_billing_enabled(project_id: str) -> bool:
    try:
        client = CloudBillingClient()
        info = client.get_project_billing_info(name=f"projects/{project_id}")
        return info.billing_enabled
    except Exception as e:
        log.warning("Could not check billing for %s: %s", project_id, e)
        return False


def enable_apis(project_id: str, apis: list[str] | None = None) -> list[dict]:
    """Enable GCP APIs -- batched into a single SDK call (HARD-07)."""
    apis = apis or BOOTSTRAP_APIS
    try:
        client = ServiceUsageClient()
        operation = client.batch_enable_services(
            request=BatchEnableServicesRequest(
                parent=f"projects/{project_id}",
                service_ids=list(apis),
            )
        )
        operation.result()  # Wait for completion
        return [{"api": api, "success": True, "error": None} for api in apis]
    except Exception as e:
        log.warning("Batch enable failed for %s: %s — falling back to individual", project_id, e)
        # Fall back to individual calls to identify which failed
        results = []
        client = ServiceUsageClient()
        for api in apis:
            try:
                op = client.batch_enable_services(
                    request=BatchEnableServicesRequest(
                        parent=f"projects/{project_id}",
                        service_ids=[api],
                    )
                )
                op.result()
                results.append({"api": api, "success": True, "error": None})
            except Exception as ex:
                results.append({"api": api, "success": False, "error": str(ex)})
        return results


def create_tf_state_bucket(project_id: str, region: str) -> dict:
    bucket_name = f"{project_id}-tfstate"
    client = storage.Client(project=project_id)
    try:
        bucket = client.get_bucket(bucket_name)
        # Bucket exists — ensure protections are in place
        _protect_tf_state_bucket(bucket)
        return {"bucket": f"gs://{bucket_name}", "created": False, "message": "Already exists"}
    except gcp_exceptions.NotFound:
        pass  # Need to create it
    except Exception as e:
        return {"bucket": f"gs://{bucket_name}", "created": False, "error": str(e)}

    try:
        bucket = client.bucket(bucket_name)
        bucket.location = region
        bucket.iam_configuration.uniform_bucket_level_access_enabled = True
        bucket.iam_configuration.public_access_prevention = "enforced"
        bucket = client.create_bucket(bucket, project=project_id)
        _protect_tf_state_bucket(bucket)
        return {"bucket": f"gs://{bucket_name}", "created": True}
    except Exception as e:
        return {"bucket": f"gs://{bucket_name}", "created": False, "error": str(e)}


def _protect_tf_state_bucket(bucket):
    """Apply protections to a terraform state bucket: versioning + soft delete."""
    try:
        bucket.versioning_enabled = True
        bucket.soft_delete_policy.retention_duration_seconds = 7 * 24 * 60 * 60  # 7 days
        bucket.patch()
        log.info("Protections applied to %s (versioning + soft delete)", bucket.name)
    except Exception as e:
        log.warning("Failed to apply protections to %s: %s", bucket.name, e)


def _get_access_token() -> str:
    credentials, _ = google.auth.default()
    request = google.auth.transport.requests.Request()
    credentials.refresh(request)
    return credentials.token


def _firebase_api(method: str, url: str, token: str, body: dict | None = None) -> dict:
    """Call a Firebase/Identity Toolkit REST endpoint."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        log.error("Firebase API %s %s → %s: %s", method, url, e.code, error_body)
        return {"error": error_body, "status": e.code}


def add_firebase_to_project(project_id: str) -> dict:
    """Add Firebase to a GCP project and return the operation name."""
    token = _get_access_token()
    url = f"https://firebase.googleapis.com/v1beta1/projects/{project_id}:addFirebase"
    result = _firebase_api("POST", url, token)
    log.info("addFirebase result: %s", result)
    return result


def init_identity_platform(project_id: str) -> dict:
    """Initialize Identity Platform on a project."""
    token = _get_access_token()
    url = f"https://identitytoolkit.googleapis.com/v2/projects/{project_id}/identityPlatform:initializeAuth"
    return _firebase_api("POST", url, token, {})


def _get_project_number(project_id: str) -> str | None:
    """Get the numeric project number from a project ID."""
    try:
        client = ProjectsClient()
        project = client.get_project(name=f"projects/{project_id}")
        # project.name is "projects/<number>"
        return project.name.split("/")[-1]
    except Exception as e:
        log.warning("Could not get project number for %s: %s", project_id, e)
        return None


def _create_oauth_client(project_id: str, token: str) -> dict | None:
    """Try to create an OAuth client via the IAP brands/clients API.

    Only works for projects in a GCP Organization.
    Returns {"clientId": ..., "clientSecret": ...} or None.
    """
    project_number = _get_project_number(project_id)
    if not project_number:
        return None

    # Create or get the OAuth brand (consent screen)
    brand_url = f"https://iap.googleapis.com/v1/projects/{project_number}/brands"
    brands = _firebase_api("GET", brand_url, token)
    if "error" in brands:
        log.info("Cannot create OAuth brand (project may not be in an org): %s", brands)
        return None

    brand_list = brands.get("brands", [])
    if brand_list:
        brand_name = brand_list[0]["name"]
    else:
        brand_result = _firebase_api("POST", brand_url, token, {
            "applicationTitle": project_id,
            "supportEmail": "noreply@" + project_id + ".iam.gserviceaccount.com",
        })
        if "error" in brand_result:
            return None
        brand_name = brand_result["name"]

    # Create an OAuth client under this brand
    client_url = f"https://iap.googleapis.com/v1/{brand_name}/identityAwareProxyClients"
    client_result = _firebase_api("POST", client_url, token, {
        "displayName": "Firebase Auth",
    })
    if "error" in client_result:
        return None

    return {
        "clientId": client_result.get("name", "").split("/")[-1],
        "clientSecret": client_result.get("secret"),
    }


def enable_google_sign_in(project_id: str) -> dict:
    """Enable Google as an IdP on Identity Platform.

    Attempts to auto-create an OAuth client (works for org-backed projects).
    If that fails, returns a result indicating manual setup is needed via
    Firebase Console > Authentication > Sign-in method > Google.
    """
    token = _get_access_token()
    # Check if already configured
    check_url = f"https://identitytoolkit.googleapis.com/admin/v2/projects/{project_id}/defaultSupportedIdpConfigs/google.com"
    existing = _firebase_api("GET", check_url, token)
    if "error" not in existing:
        return {"already_configured": True, **existing}

    # Try to auto-create an OAuth client
    oauth = _create_oauth_client(project_id, token)
    if not oauth:
        log.warning(
            "Could not auto-create OAuth client for %s. "
            "Enable Google sign-in manually via Firebase Console.",
            project_id,
        )
        return {"needs_manual_setup": True, "message": "Enable Google sign-in via Firebase Console > Authentication > Sign-in method"}

    # Create the IdP config with the auto-created OAuth client
    create_url = f"https://identitytoolkit.googleapis.com/admin/v2/projects/{project_id}/defaultSupportedIdpConfigs?idpId=google.com"
    return _firebase_api("POST", create_url, token, {
        "enabled": True,
        "clientId": oauth["clientId"],
        "clientSecret": oauth["clientSecret"],
    })


def create_firebase_web_app(project_id: str, display_name: str) -> dict:
    """Create a Firebase web app and return its config (apiKey, authDomain, etc.)."""
    token = _get_access_token()

    # Check if a web app already exists
    list_url = f"https://firebase.googleapis.com/v1beta1/projects/{project_id}/webApps"
    apps = _firebase_api("GET", list_url, token)
    existing = apps.get("apps", [])
    if existing:
        app_id = existing[0]["appId"]
        log.info("Web app already exists: %s", app_id)
    else:
        # Create a new web app
        create_result = _firebase_api("POST", list_url, token, {"displayName": display_name})
        if "error" in create_result:
            return create_result
        # Poll for the app to be ready
        time.sleep(5)
        apps = _firebase_api("GET", list_url, token)
        existing = apps.get("apps", [])
        if not existing:
            return {"error": "Web app creation timed out"}
        app_id = existing[0]["appId"]

    # Get the config
    config_url = f"https://firebase.googleapis.com/v1beta1/projects/{project_id}/webApps/{app_id}/config"
    config = _firebase_api("GET", config_url, token)
    return config


def setup_firebase_auth(project_id: str, app_display_name: str = "Web App") -> dict:
    """Full Firebase Auth setup for a customer project. Returns the web app config."""
    steps = {}

    # 1. Add Firebase to the project
    fb_result = add_firebase_to_project(project_id)
    steps["add_firebase"] = "error" not in fb_result

    # 2. Initialize Identity Platform
    idp_result = init_identity_platform(project_id)
    steps["init_identity_platform"] = "error" not in idp_result

    # 3. Enable Google sign-in (auto-creates OAuth client for org-backed projects)
    google_result = enable_google_sign_in(project_id)
    steps["enable_google_signin"] = "error" not in google_result
    needs_manual_google = google_result.get("needs_manual_setup", False)

    # 4. Create web app and get config
    config = create_firebase_web_app(project_id, app_display_name)
    steps["create_web_app"] = "error" not in config

    return {
        "steps": steps,
        "firebase_config": config if "error" not in config else None,
        "needs_manual_google_signin": needs_manual_google,
        "success": all(steps.values()),
    }


def create_gcp_project(project_id: str, display_name: str,
                       billing_account: str | None = None,
                       folder_id: str | None = None) -> dict:
    """Create a GCP project, optionally inside a folder."""
    try:
        client = ProjectsClient()
        project = Project(
            project_id=project_id,
            display_name=display_name,
        )
        if folder_id:
            project.parent = f"folders/{folder_id}"

        operation = client.create_project(
            request=CreateProjectRequest(project=project)
        )
        operation.result()  # Wait for completion

        # Link billing if provided
        if billing_account:
            link_billing(project_id, billing_account)

        return {"created": True}
    except gcp_exceptions.AlreadyExists:
        return {"created": False, "skipped": True, "reason": "already_exists", "exists": True}
    except gcp_exceptions.PermissionDenied as e:
        log.info("Skipping project creation (permission denied): %s", e)
        exists = validate_project_exists(project_id)
        return {"created": False, "skipped": True, "reason": "no_org", "exists": exists}
    except Exception as e:
        error_msg = str(e).lower()
        if "already exists" in error_msg:
            return {"created": False, "skipped": True, "reason": "already_exists", "exists": True}
        if "organization" in error_msg or "parent" in error_msg or "permission" in error_msg:
            log.info("Skipping project creation (no org): %s", e)
            exists = validate_project_exists(project_id)
            return {"created": False, "skipped": True, "reason": "no_org", "exists": exists}
        return {"created": False, "skipped": False, "error": str(e)}


def ensure_tenant_folder(tenant_id: str, display_name: str, parent_folder_id: str) -> str:
    """Create a tenant folder under the tenants folder if it doesn't exist.

    Returns the folder ID (numeric) of the tenant folder.
    """
    client = FoldersClient()

    # Check if folder already exists
    try:
        request = ListFoldersRequest(parent=f"folders/{parent_folder_id}")
        for folder in client.list_folders(request=request):
            if folder.display_name == display_name:
                folder_id = folder.name.split("/")[-1]
                log.info("Tenant folder already exists: %s (ID: %s)", display_name, folder_id)
                return folder_id
    except Exception as e:
        log.warning("Could not list folders under %s: %s", parent_folder_id, e)

    # Create folder
    try:
        operation = client.create_folder(
            request=CreateFolderRequest(
                folder=Folder(
                    parent=f"folders/{parent_folder_id}",
                    display_name=display_name,
                )
            )
        )
        created_folder = operation.result()  # Wait for completion
        folder_id = created_folder.name.split("/")[-1]
        log.info("Created tenant folder: %s (ID: %s)", display_name, folder_id)
        return folder_id
    except Exception as e:
        raise RuntimeError(f"Failed to create tenant folder: {e}")


def link_billing(project_id: str, billing_account: str) -> dict:
    """Link a billing account to a project."""
    try:
        client = CloudBillingClient()
        client.update_project_billing_info(
            name=f"projects/{project_id}",
            project_billing_info=ProjectBillingInfo(
                billing_account_name=f"billingAccounts/{billing_account}",
            ),
        )
        return {"success": True, "error": None}
    except Exception as e:
        return {"success": False, "error": str(e)}


def verify_project_health(project_id: str) -> dict:
    """Check that APIs are enabled and tfstate bucket exists."""
    checks = []

    # Check each API
    try:
        client = ServiceUsageClient()
        request = ListServicesRequest(
            parent=f"projects/{project_id}",
            filter="state:ENABLED",
        )
        enabled_apis = set()
        for service in client.list_services(request=request):
            # service.config.name is like "storage.googleapis.com"
            enabled_apis.add(service.config.name)
    except Exception as e:
        log.warning("Could not list services for %s: %s", project_id, e)
        enabled_apis = set()

    for api in BOOTSTRAP_APIS:
        checks.append({"check": f"api:{api}", "ok": api in enabled_apis})

    # Check tfstate bucket
    bucket_name = f"{project_id}-tfstate"
    try:
        storage_client = storage.Client(project=project_id)
        storage_client.get_bucket(bucket_name)
        checks.append({"check": "tfstate_bucket", "ok": True})
    except Exception:
        checks.append({"check": "tfstate_bucket", "ok": False})

    healthy = all(c["ok"] for c in checks)
    return {"healthy": healthy, "checks": checks}


def terraform_init(project_id: str, region: str) -> dict:
    """Run terraform init with GCS backend config in a temp directory."""
    tf_bin = shutil.which("terraform")
    if not tf_bin:
        return {"success": False, "error": "terraform binary not found"}

    tmp_dir = tempfile.mkdtemp(prefix=f"tf-{project_id}-")
    try:
        # Write minimal provider + backend config
        provider_tf = f"""\
terraform {{
  required_version = ">= 1.5"
  backend "gcs" {{
    bucket = "{project_id}-tfstate"
    prefix = "terraform/state"
  }}
  required_providers {{
    google = {{
      source  = "hashicorp/google"
      version = "~> 5.0"
    }}
  }}
}}

provider "google" {{
  project = "{project_id}"
  region  = "{region}"
}}
"""
        with open(os.path.join(tmp_dir, "provider.tf"), "w") as f:
            f.write(provider_tf)

        r = subprocess.run(
            ["terraform", "init", f"-backend-config=bucket={project_id}-tfstate"],
            capture_output=True, text=True, check=False, timeout=120, cwd=tmp_dir,
        )
        if r.returncode != 0:
            return {"success": False, "error": r.stderr.strip(), "output": r.stdout.strip()}
        return {"success": True, "output": r.stdout.strip()}
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def bootstrap_project(project_id: str, region: str = "us-central1") -> BootstrapResult:
    result = BootstrapResult(project_id=project_id)

    # 1. Validate project
    if not validate_project_exists(project_id):
        result.success = False
        result.error = f"Project {project_id} does not exist or is not accessible"
        return result
    result.steps.append({"step": "validate_project", "success": True})

    # 2. Check billing
    billing = check_billing_enabled(project_id)
    result.steps.append({"step": "check_billing", "success": True, "billing_enabled": billing})

    # 3. Enable APIs
    api_results = enable_apis(project_id)
    failed_apis = [a for a in api_results if not a["success"]]
    result.steps.append({"step": "enable_apis", "success": len(failed_apis) == 0, "details": api_results})
    if failed_apis:
        result.success = False
        result.error = f"Failed to enable APIs: {', '.join(a['api'] for a in failed_apis)}"
        return result

    # 4. Create TF state bucket
    bucket_result = create_tf_state_bucket(project_id, region)
    result.steps.append({"step": "create_bucket", **bucket_result})
    if "error" in bucket_result:
        result.success = False
        result.error = bucket_result["error"]
        return result

    # 5. Setup Firebase Auth (Identity Platform + web app)
    firebase_result = setup_firebase_auth(project_id)
    result.steps.append({"step": "setup_firebase_auth", **firebase_result})
    if not firebase_result["success"]:
        log.warning("Firebase Auth setup had failures: %s", firebase_result["steps"])
        # Non-fatal — project is still usable without auth

    return result
