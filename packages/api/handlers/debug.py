"""Debug endpoints for raw state inspection (AGT-12)."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from packages.platform.auth.authz import require_project_access, ProjectAccess
from packages.platform.store import blueprints as blueprint_store
from packages.platform.store import projects as project_store
from packages.platform.store import deploys as deploy_store
from packages.core.terraform.generator import generate_terraform
from packages.core.schemas.base import Envelope

router = APIRouter(tags=["debug"])
log = logging.getLogger(__name__)


@router.get("/debug/{project_ref_id}/state")
async def get_project_state(
    project_ref_id: str,
    access: ProjectAccess = Depends(require_project_access("viewer")),
):
    """Return the raw project document from Firestore."""
    doc = project_store.get_project(access.owner_uid, project_ref_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Project not found")
    return doc


@router.get("/debug/{project_ref_id}/{env_name}/validation")
async def get_validation_state(
    project_ref_id: str,
    env_name: str,
    access: ProjectAccess = Depends(require_project_access("viewer")),
):
    """Return raw validation doc for an environment."""
    doc = blueprint_store.get_validation_doc(access.owner_uid, project_ref_id, env_name)
    if not doc:
        return {"valid": None, "issues": []}
    return doc


@router.get("/debug/{project_ref_id}/{env_name}/terraform")
async def get_terraform_output(
    project_ref_id: str,
    env_name: str,
    access: ProjectAccess = Depends(require_project_access("viewer")),
):
    """Compile and return Terraform HCL files for an environment."""
    bp = blueprint_store.get_env_blueprint(access.owner_uid, project_ref_id, env_name)
    if not bp or not bp.get("envelope"):
        return {"files": {}}

    try:
        envelope = Envelope.model_validate(bp["envelope"])
        files = generate_terraform(envelope)
    except Exception as e:
        log.warning("Terraform generation failed for %s/%s: %s", project_ref_id, env_name, e)
        return {"files": {}, "error": str(e)}

    return {"files": files}


@router.get("/debug/{project_ref_id}/deploys")
async def get_deploy_history(
    project_ref_id: str,
    access: ProjectAccess = Depends(require_project_access("viewer")),
):
    """List deploy records for a project."""
    deploys = deploy_store.list_deploys(access.owner_uid, project_ref_id)
    return {"deploys": deploys}


@router.get("/debug/{project_ref_id}/{env_name}/nodes/status")
async def get_nodes_deploy_status(
    project_ref_id: str,
    env_name: str,
    access: ProjectAccess = Depends(require_project_access("viewer")),
):
    """List all nodes with their deploy status for an environment."""
    nodes = blueprint_store.list_nodes(access.owner_uid, project_ref_id, env_name)
    status_doc = deploy_store.get_node_deploy_status_doc(access.owner_uid, project_ref_id, env_name)
    node_statuses = status_doc.get("nodes", {})

    result = []
    for node in nodes:
        slug = node.get("slug", node.get("name"))
        deploy_info = node_statuses.get(slug, {})
        result.append({
            "slug": slug,
            "name": node.get("name"),
            "type": node.get("type"),
            "deployed_version": deploy_info.get("deployed_version"),
            "deployed_at": deploy_info.get("deployed_at"),
            "current_modified": deploy_info.get("current_modified", False),
        })

    return {"nodes": result}
