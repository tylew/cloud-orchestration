"""Blueprint validation, inference, and env-scoped CRUD handlers."""

import logging
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from packages.core.schemas.base import Envelope
from packages.core.validation import validate_blueprint
from packages.platform.auth.firebase import get_current_user, CurrentUser
from packages.platform.auth.authz import require_project_access, ProjectAccess
from packages.platform.store import blueprints as blueprint_store
from packages.platform.store import projects as project_store
from packages.platform.store import tenants as tenant_store

router = APIRouter()


def _serializable_errors(errors: list) -> list:
    """Strip non-JSON-serializable objects (like ValueError) from Pydantic error dicts."""
    clean = []
    for err in errors:
        e = dict(err)
        if 'ctx' in e:
            e['ctx'] = {k: str(v) for k, v in e['ctx'].items()}
        clean.append(e)
    return clean


log = logging.getLogger(__name__)


def parse_envelope(payload: dict) -> Envelope:
    """Parse and validate a raw blueprint payload into an Envelope.

    Single entry point for all blueprint parsing. Future migrations
    will be applied here before validation.
    """
    return Envelope.model_validate(payload)


@router.post("/blueprints/validate")
async def validate_blueprint_endpoint(payload: dict):
    try:
        envelope = parse_envelope(payload)
    except ValidationError as e:
        return {"valid": False, "schema_errors": _serializable_errors(e.errors()), "issues": []}

    issues = validate_blueprint(envelope)
    return {
        "valid": len([i for i in issues if i.severity == "error"]) == 0,
        "issues": [asdict(i) for i in issues],
    }


# ── Env-scoped Blueprint Endpoints ──────────────────────────

@router.put("/projects/{project_ref_id}/envs/{env_name}/blueprint")
async def save_env_blueprint(project_ref_id: str, env_name: str, payload: dict,
                             access: ProjectAccess = Depends(require_project_access("editor"))):
    try:
        parse_envelope(payload)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=_serializable_errors(e.errors()))

    tenant_store.ensure_tenant(access.user.tenant_id, access.user.email, access.user.display_name)
    result = blueprint_store.save_env_blueprint(access.owner_uid, project_ref_id, env_name, payload)

    # Skip logging no-op saves (nothing changed)
    if not result.get("is_noop"):
        changes = result.get("changes", {})
        details = {
            "node_count": result.get("node_count", 0),
            "nodes_added": changes.get("added", []),
            "nodes_removed": changes.get("removed", []),
            "nodes_modified": changes.get("modified", []),
        }
        project_store.add_activity(access.owner_uid, project_ref_id, "save", env_name,
                           access.user.email, access.user.display_name, details=details)

    return result


@router.get("/projects/{project_ref_id}/envs/{env_name}/blueprint")
async def get_env_blueprint(project_ref_id: str, env_name: str,
                            access: ProjectAccess = Depends(require_project_access("viewer"))):
    doc = blueprint_store.get_env_blueprint(access.owner_uid, project_ref_id, env_name)
    if not doc:
        return {"env": env_name, "envelope": None}
    return doc


@router.get("/projects/{project_ref_id}/activity")
async def get_activity(access: ProjectAccess = Depends(require_project_access("viewer"))):
    return project_store.list_activity(access.owner_uid, access.project["id"])
