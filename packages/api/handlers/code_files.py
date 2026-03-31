"""REST endpoints for compute node code file management."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Body
from packages.platform.auth.authz import require_project_access, ProjectAccess
from packages.platform.gcp import storage as code_storage

log = logging.getLogger(__name__)

router = APIRouter()


@router.get("/projects/{project_ref_id}/envs/{env_name}/nodes/{node_name}/files")
async def list_node_files(
    project_ref_id: str,
    env_name: str,
    node_name: str,
    access: ProjectAccess = Depends(require_project_access("viewer")),
):
    """List all code files for a compute node."""
    files = code_storage.list_files(project_ref_id, env_name, node_name)
    return {"files": files}


@router.get("/projects/{project_ref_id}/envs/{env_name}/nodes/{node_name}/files/{file_path:path}")
async def read_node_file(
    project_ref_id: str,
    env_name: str,
    node_name: str,
    file_path: str,
    access: ProjectAccess = Depends(require_project_access("viewer")),
):
    """Read a single code file's content."""
    content = code_storage.read_file(project_ref_id, env_name, node_name, file_path)
    if content is None:
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    return {"path": file_path, "content": content}


@router.put("/projects/{project_ref_id}/envs/{env_name}/nodes/{node_name}/files/{file_path:path}")
async def write_node_file(
    project_ref_id: str,
    env_name: str,
    node_name: str,
    file_path: str,
    content: str = Body(..., media_type="text/plain"),
    access: ProjectAccess = Depends(require_project_access("editor")),
):
    """Write or overwrite a code file."""
    ok = code_storage.write_file(project_ref_id, env_name, node_name, file_path, content)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to write file")
    return {"path": file_path, "status": "saved"}


@router.delete("/projects/{project_ref_id}/envs/{env_name}/nodes/{node_name}/files/{file_path:path}")
async def delete_node_file(
    project_ref_id: str,
    env_name: str,
    node_name: str,
    file_path: str,
    access: ProjectAccess = Depends(require_project_access("editor")),
):
    """Delete a code file."""
    ok = code_storage.delete_file(project_ref_id, env_name, node_name, file_path)
    if not ok:
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    return {"path": file_path, "status": "deleted"}
