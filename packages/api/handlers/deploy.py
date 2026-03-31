"""Deploy handler -- SSE log stream and per-node deploy status endpoints."""

import os
import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from packages.platform.auth.firebase import get_current_user, CurrentUser
from packages.platform.auth.authz import require_project_access, ProjectAccess
from packages.platform.store import projects as project_store
from packages.platform.store import deploys as deploy_store
from packages.platform.store import blueprints as blueprint_store
from packages.platform import deploy_service
from packages.platform.streaming.deploy_logs import stream_build_logs

log = logging.getLogger(__name__)

router = APIRouter(tags=["deploy"])


@router.get("/projects/{project_ref_id}/deploys/{deploy_id}/logs/stream")
async def stream_deploy_logs(project_ref_id: str, deploy_id: str,
                             token: str = Query(..., description="Auth token for SSE (EventSource cannot send headers)")):
    """SSE endpoint that streams Cloud Build log entries for a deploy.

    Uses query param `token` for auth since EventSource API cannot set headers.
    """
    from sse_starlette.sse import EventSourceResponse

    # Validate token same as get_current_user but from query param
    _auth_disabled = (
        os.environ.get("AUTH_DISABLED", "false").lower() in ("true", "1", "yes")
        and os.environ.get("ENVIRONMENT", "").lower() in ("dev", "development", "local", "")
    )

    if _auth_disabled:
        from packages.platform.auth.firebase import _DEV_USER
        user = _DEV_USER
    else:
        from packages.platform.auth.firebase import _ensure_firebase
        _ensure_firebase()
        try:
            from firebase_admin import auth
            decoded = auth.verify_id_token(token)
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")
        uid = decoded.get("uid", "")
        user = CurrentUser(tenant_id=uid, email=decoded.get("email", ""),
                           display_name=decoded.get("name", ""))

    # Find project and verify access
    project, owner_uid = project_store.find_project_for_user(user.tenant_id, project_ref_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get deploy record
    deploy = deploy_store.get_deploy_status(owner_uid, deploy_id)
    if not deploy:
        raise HTTPException(status_code=404, detail="Deploy not found")

    build_id = deploy.get("build_id")
    if not build_id:
        raise HTTPException(status_code=404, detail="No build associated with this deploy yet")

    host_project_id = os.environ.get("GCP_PROJECT_ID", "pl4m-host")
    generator = stream_build_logs(host_project_id, build_id, owner_uid, deploy_id)

    return EventSourceResponse(generator)


@router.get("/projects/{project_ref_id}/node-deploy-status/{env_name}")
async def get_node_deploy_status(project_ref_id: str, env_name: str,
                                  access: ProjectAccess = Depends(require_project_access("viewer"))):
    """Return per-node deploy statuses and modified flags for an environment (per D-08/D-09/D-10)."""
    owner_uid = access.owner_uid

    nodes = deploy_service.get_node_deploy_statuses(owner_uid, project_ref_id, env_name)

    # Compute modified flags from current blueprint
    blueprint = blueprint_store.get_env_blueprint(owner_uid, project_ref_id, env_name)
    modified = {}
    if blueprint and blueprint.get("envelope"):
        modified = deploy_service.compute_modified_flags(owner_uid, project_ref_id, env_name, blueprint["envelope"])

    return {"nodes": nodes, "modified": modified}
