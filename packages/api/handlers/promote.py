"""Blueprint promotion endpoint."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from packages.platform.auth.authz import require_project_access, ProjectAccess
from packages.platform.store import blueprints as blueprint_store
from packages.platform.store.projects import get_env_entry

log = logging.getLogger(__name__)

router = APIRouter()


class PromoteRequest(BaseModel):
    source_env: str


@router.post("/projects/{project_ref_id}/envs/{target_env}/promote")
async def promote_blueprint(project_ref_id: str, target_env: str, req: PromoteRequest,
                            access: ProjectAccess = Depends(require_project_access("editor"))):
    """Promote blueprint from source env to target env, stripping env var values."""
    project = access.project
    owner_uid = access.owner_uid
    envs = project.get("environments", [])

    # Validate source env exists
    source_entry = get_env_entry(envs, req.source_env)
    if not source_entry:
        raise HTTPException(status_code=404, detail=f"Source environment '{req.source_env}' not found")

    # Validate target env exists
    target_entry = get_env_entry(envs, target_env)
    if not target_entry:
        raise HTTPException(status_code=404, detail=f"Target environment '{target_env}' not found")

    # Validate target is provisioned
    provision_status = target_entry.get("provision_status", "")
    if provision_status != "ready":
        raise HTTPException(status_code=422, detail=f"Target environment '{target_env}' is not provisioned (status: {provision_status})")

    try:
        result = blueprint_store.promote_blueprint(owner_uid, project_ref_id, req.source_env, target_env)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Log activity
    from packages.platform.store.projects import add_activity
    add_activity(
        owner_uid, project_ref_id,
        action="promote",
        env=target_env,
        user_email=access.user.email,
        user_display_name=access.user.display_name,
        details={"source_env": req.source_env, "nodes_copied": result["nodes_copied"]},
    )

    return result
