import os

from fastapi import APIRouter, Depends
from pydantic import ValidationError

from packages.platform.auth.firebase import get_current_user, CurrentUser
from packages.core.registry import REGISTRY
from packages.core.schemas.base import Envelope
from packages.platform.store import tenants as tenant_store

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/config")
async def config():
    """Return public Firebase client config from env vars."""
    project_id = os.environ.get("GCP_PROJECT_ID", "")
    api_key = os.environ.get("FIREBASE_API_KEY", "")
    auth_disabled = os.environ.get("AUTH_DISABLED", "false").lower() == "true"
    return {
        "firebase": {
            "apiKey": api_key,
            "authDomain": f"{project_id}.firebaseapp.com",
            "projectId": project_id,
            "appId": os.environ.get("FIREBASE_APP_ID", ""),
            "messagingSenderId": os.environ.get("FIREBASE_MESSAGING_SENDER_ID", ""),
            "databaseURL": f"https://{project_id}-default-rtdb.firebaseio.com",
        },
        "authDisabled": auth_disabled,
    }


@router.get("/me")
async def me(user: CurrentUser = Depends(get_current_user)):
    tenant = tenant_store.get_tenant(user.tenant_id)
    return {
        "tenant_id": user.tenant_id,
        "email": user.email,
        "display_name": user.display_name,
        "is_admin": user.is_admin,
        "quota": tenant.get("quota", 0) if tenant else 0,
        "used_quota": tenant.get("used_quota", 0) if tenant else 0,
    }


@router.get("/schema/types")
async def schema_types():
    result = {}
    for node_type, defn in REGISTRY.items():
        result[node_type.value] = {
            "label": defn.label,
            "category": defn.category,
            "is_compute": defn.is_compute,
            "terraform_resource": defn.terraform_resource,
            "iam_scope": defn.iam_scope,
            "default_outputs": list(defn.default_outputs),
        }
    return result


@router.post("/schema/validate")
async def schema_validate(payload: dict):
    try:
        envelope = Envelope.model_validate(payload)
        return {"valid": True, "node_count": len(envelope.nodes)}
    except ValidationError as e:
        return {"valid": False, "errors": [{**err, 'ctx': {k: str(v) for k, v in err.get('ctx', {}).items()}} for err in e.errors()]}
