"""IDE file CRUD endpoints routed through RepositoryProvider."""

import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from packages.platform.auth.authz import require_project_access, ProjectAccess
from packages.platform.github.repository import RepositoryProvider
from packages.platform.github.github_repo import GitHubRepositoryProvider

log = logging.getLogger(__name__)
router = APIRouter()

_provider: RepositoryProvider | None = None


def _get_provider() -> RepositoryProvider | None:
    """Return a GitHubRepositoryProvider singleton, or None if not configured."""
    global _provider
    if _provider is not None:
        return _provider

    app_id = os.environ.get("GITHUB_APP_ID", "")
    private_key = os.environ.get("GITHUB_APP_PRIVATE_KEY", "")
    installation_id = os.environ.get("GITHUB_APP_INSTALLATION_ID", "")

    if not all([app_id, private_key, installation_id]):
        return None

    _provider = GitHubRepositoryProvider(
        app_id=app_id,
        private_key=private_key,
        installation_id=installation_id,
    )
    return _provider


def _require_provider() -> RepositoryProvider:
    """Get provider or raise 503."""
    provider = _get_provider()
    if not provider:
        raise HTTPException(503, "Repository provider not configured")
    return provider


def _project_id(access: ProjectAccess) -> str:
    """Extract project_id from access context."""
    return access.project.get("project_id", "")


# ─── Repo provisioning ───────────────────────────────────────────────────


@router.post("/ide/{project_ref_id}/ensure-repo")
async def ensure_repo(
    project_ref_id: str,
    access: ProjectAccess = Depends(require_project_access("editor")),
):
    """Ensure GitHub repo exists for project. Idempotent."""
    provider = _require_provider()
    repo_name = await provider.ensure_repo(_project_id(access))
    return {"repo": repo_name}


# ─── File CRUD ────────────────────────────────────────────────────────────


@router.get("/ide/{project_ref_id}/{env_name}/{node_name}/files")
async def list_files(
    project_ref_id: str,
    env_name: str,
    node_name: str,
    access: ProjectAccess = Depends(require_project_access("viewer")),
):
    """List all files for a compute node."""
    provider = _require_provider()
    files = await provider.list_files(_project_id(access), env_name, node_name)
    return {"files": [{"path": f.path, "size": f.size, "updated_at": f.updated_at} for f in files]}


@router.get("/ide/{project_ref_id}/{env_name}/{node_name}/files/{file_path:path}")
async def read_file(
    project_ref_id: str,
    env_name: str,
    node_name: str,
    file_path: str,
    access: ProjectAccess = Depends(require_project_access("viewer")),
):
    """Read a single file's content."""
    provider = _require_provider()
    content = await provider.read_file(_project_id(access), env_name, node_name, file_path)
    if content is None:
        raise HTTPException(404, f"File not found: {file_path}")
    return {"path": file_path, "content": content}


class WriteFileBody(BaseModel):
    content: str


@router.put("/ide/{project_ref_id}/{env_name}/{node_name}/files/{file_path:path}")
async def write_file(
    project_ref_id: str,
    env_name: str,
    node_name: str,
    file_path: str,
    body: WriteFileBody,
    access: ProjectAccess = Depends(require_project_access("editor")),
):
    """Create or update a file."""
    provider = _require_provider()
    ok = await provider.write_file(_project_id(access), env_name, node_name, file_path, body.content)
    if not ok:
        raise HTTPException(500, "Failed to write file")
    return {"ok": True}


@router.delete("/ide/{project_ref_id}/{env_name}/{node_name}/files/{file_path:path}")
async def delete_file(
    project_ref_id: str,
    env_name: str,
    node_name: str,
    file_path: str,
    access: ProjectAccess = Depends(require_project_access("editor")),
):
    """Delete a file."""
    provider = _require_provider()
    ok = await provider.delete_file(_project_id(access), env_name, node_name, file_path)
    if not ok:
        raise HTTPException(404, f"File not found: {file_path}")
    return {"ok": True}


# ─── Snapshots ────────────────────────────────────────────────────────────


class SnapshotBody(BaseModel):
    message: str


@router.post("/ide/{project_ref_id}/{env_name}/{node_name}/snapshots")
async def save_snapshot(
    project_ref_id: str,
    env_name: str,
    node_name: str,
    body: SnapshotBody,
    access: ProjectAccess = Depends(require_project_access("editor")),
):
    """Create a snapshot of the current state."""
    provider = _require_provider()
    snapshot_id = await provider.save_snapshot(
        _project_id(access), env_name, node_name, body.message, access.user.email,
    )
    if not snapshot_id:
        raise HTTPException(500, "Failed to create snapshot")
    return {"snapshot_id": snapshot_id}


@router.get("/ide/{project_ref_id}/{env_name}/{node_name}/snapshots")
async def list_snapshots(
    project_ref_id: str,
    env_name: str,
    node_name: str,
    access: ProjectAccess = Depends(require_project_access("viewer")),
):
    """List all snapshots for a compute node."""
    provider = _require_provider()
    snapshots = await provider.list_snapshots(_project_id(access), env_name, node_name)
    return {"snapshots": [
        {"id": s.id, "message": s.message, "user_email": s.user_email,
         "created_at": s.created_at, "file_count": s.file_count}
        for s in snapshots
    ]}
