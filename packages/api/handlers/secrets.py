"""Secret management endpoints — env-scoped with Firestore reflection."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from packages.platform.auth.authz import require_project_access, ProjectAccess
from packages.platform.store import secrets as secret_store

log = logging.getLogger(__name__)
router = APIRouter()


@router.get("/projects/{project_ref_id}/envs/{env_name}/secrets")
async def list_secrets(
    project_ref_id: str, env_name: str,
    access: ProjectAccess = Depends(require_project_access("viewer")),
):
    secrets = secret_store.list_secrets(access.owner_uid, project_ref_id, env_name)
    return {"secrets": secrets}


@router.post("/projects/{project_ref_id}/envs/{env_name}/secrets")
async def create_secret(
    project_ref_id: str, env_name: str,
    payload: dict,
    access: ProjectAccess = Depends(require_project_access("editor")),
):
    secret_id = payload.get("secret_id", "").strip()
    value = payload.get("value", "")
    description = payload.get("description", "")

    if not secret_id:
        raise HTTPException(status_code=422, detail="secret_id is required")
    if not value:
        raise HTTPException(status_code=422, detail="value is required")

    project_id = access.project.get("project_id", "")
    try:
        result = secret_store.create_secret(
            access.owner_uid, project_ref_id, env_name,
            project_id, secret_id, value, description,
            access.user.email,
        )
        return result
    except Exception as e:
        log.warning("Failed to create secret %s: %s", secret_id, e)
        raise HTTPException(status_code=500, detail=f"Could not create secret: {e}")


@router.get("/projects/{project_ref_id}/envs/{env_name}/secrets/{secret_id}")
async def get_secret(
    project_ref_id: str, env_name: str, secret_id: str,
    access: ProjectAccess = Depends(require_project_access("viewer")),
):
    secret = secret_store.get_secret(access.owner_uid, project_ref_id, env_name, secret_id)
    if not secret:
        raise HTTPException(status_code=404, detail=f"Secret '{secret_id}' not found")
    versions = secret_store.list_versions(access.owner_uid, project_ref_id, env_name, secret_id)
    return {**secret, "versions": versions}


@router.put("/projects/{project_ref_id}/envs/{env_name}/secrets/{secret_id}")
async def add_version(
    project_ref_id: str, env_name: str, secret_id: str,
    payload: dict,
    access: ProjectAccess = Depends(require_project_access("editor")),
):
    value = payload.get("value", "")
    if not value:
        raise HTTPException(status_code=422, detail="value is required")

    project_id = access.project.get("project_id", "")
    try:
        result = secret_store.add_version(
            access.owner_uid, project_ref_id, env_name,
            project_id, secret_id, value,
            access.user.email,
        )
        return result
    except Exception as e:
        log.warning("Failed to add version for %s: %s", secret_id, e)
        raise HTTPException(status_code=500, detail=f"Could not add version: {e}")


@router.delete("/projects/{project_ref_id}/envs/{env_name}/secrets/{secret_id}")
async def delete_secret(
    project_ref_id: str, env_name: str, secret_id: str,
    access: ProjectAccess = Depends(require_project_access("admin")),
):
    project_id = access.project.get("project_id", "")
    try:
        result = secret_store.delete_secret(
            access.owner_uid, project_ref_id, env_name,
            project_id, secret_id,
        )
        return result
    except Exception as e:
        log.warning("Failed to delete secret %s: %s", secret_id, e)
        raise HTTPException(status_code=500, detail=f"Could not delete secret: {e}")


@router.delete("/projects/{project_ref_id}/envs/{env_name}/secrets/{secret_id}/versions/{version}")
async def destroy_version(
    project_ref_id: str, env_name: str, secret_id: str, version: str,
    access: ProjectAccess = Depends(require_project_access("editor")),
):
    project_id = access.project.get("project_id", "")
    try:
        result = secret_store.destroy_version(
            access.owner_uid, project_ref_id, env_name,
            project_id, secret_id, version,
            access.user.email,
        )
        return result
    except Exception as e:
        log.warning("Failed to destroy version %s/%s: %s", secret_id, version, e)
        raise HTTPException(status_code=500, detail=f"Could not destroy version: {e}")


@router.get("/projects/{project_ref_id}/envs/{env_name}/secrets/{secret_id}/versions")
async def list_versions(
    project_ref_id: str, env_name: str, secret_id: str,
    access: ProjectAccess = Depends(require_project_access("viewer")),
):
    versions = secret_store.list_versions(access.owner_uid, project_ref_id, env_name, secret_id)
    return {"versions": versions}
