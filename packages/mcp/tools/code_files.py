"""Code file management MCP tools — read, write, list, delete compute node source files."""

import logging

from packages.mcp.server import mcp
from packages.mcp.tools.formatters import format_json_response, format_error

log = logging.getLogger(__name__)

# Module-level reference for lazy-loaded dependency (testable via patch)
code_storage = None


def _ensure_deps():
    """Lazy-load dependencies to avoid import-time GCP SDK initialization."""
    global code_storage
    if code_storage is None:
        from packages.platform.gcp import storage as _cs
        code_storage = _cs


# ── MCP Tool Definitions ─────────────────────────────────────


@mcp.tool()
def write_code_file(
    project_ref_id: str,
    env_name: str,
    node_slug: str,
    file_path: str,
    content: str,
) -> str:
    """Write or overwrite a code file for a compute node.

    Files are stored in GCS and used during container builds.

    Args:
        project_ref_id: The Firestore document ID of the project.
        env_name: The environment (e.g., "dev").
        node_slug: The slug of the compute node.
        file_path: Relative file path (e.g., "main.py", "Dockerfile").
        content: The file content to write.
    """
    try:
        _ensure_deps()
        ok = code_storage.write_file(project_ref_id, env_name, node_slug, file_path, content)
        if not ok:
            return format_error("write_failed", f"Failed to write file '{file_path}'")
        return format_json_response({
            "path": file_path,
            "status": "saved",
            "message": f"File '{file_path}' written to {node_slug}",
        })
    except Exception as e:
        log.error("write_code_file failed: %s", e)
        return format_error("write_code_file_error", str(e))


@mcp.tool()
def read_code_file(
    project_ref_id: str,
    env_name: str,
    node_slug: str,
    file_path: str,
) -> str:
    """Read a code file from a compute node.

    Args:
        project_ref_id: The Firestore document ID of the project.
        env_name: The environment (e.g., "dev").
        node_slug: The slug of the compute node.
        file_path: Relative file path to read (e.g., "main.py").
    """
    try:
        _ensure_deps()
        content = code_storage.read_file(project_ref_id, env_name, node_slug, file_path)
        if content is None:
            return format_error("not_found", f"File '{file_path}' not found on node '{node_slug}'")
        return format_json_response({
            "path": file_path,
            "content": content,
        })
    except Exception as e:
        log.error("read_code_file failed: %s", e)
        return format_error("read_code_file_error", str(e))


@mcp.tool()
def list_code_files(
    project_ref_id: str,
    env_name: str,
    node_slug: str,
) -> str:
    """List all code files for a compute node.

    Args:
        project_ref_id: The Firestore document ID of the project.
        env_name: The environment (e.g., "dev").
        node_slug: The slug of the compute node.
    """
    try:
        _ensure_deps()
        files = code_storage.list_files(project_ref_id, env_name, node_slug)
        return format_json_response({
            "node_slug": node_slug,
            "files": files,
            "file_count": len(files),
        })
    except Exception as e:
        log.error("list_code_files failed: %s", e)
        return format_error("list_code_files_error", str(e))


@mcp.tool()
def delete_code_file(
    project_ref_id: str,
    env_name: str,
    node_slug: str,
    file_path: str,
) -> str:
    """Delete a code file from a compute node.

    Args:
        project_ref_id: The Firestore document ID of the project.
        env_name: The environment (e.g., "dev").
        node_slug: The slug of the compute node.
        file_path: Relative file path to delete (e.g., "main.py").
    """
    try:
        _ensure_deps()
        ok = code_storage.delete_file(project_ref_id, env_name, node_slug, file_path)
        if not ok:
            return format_error("not_found", f"File '{file_path}' not found on node '{node_slug}'")
        return format_json_response({
            "path": file_path,
            "status": "deleted",
            "message": f"File '{file_path}' deleted from {node_slug}",
        })
    except Exception as e:
        log.error("delete_code_file failed: %s", e)
        return format_error("delete_code_file_error", str(e))
