"""Dependency declaration and client code generation endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from packages.platform.auth.authz import require_project_access, ProjectAccess
from packages.platform.store import blueprints as blueprint_store
from packages.core.codegen.client_generator import generate_clients_py, generate_snippets

log = logging.getLogger(__name__)
router = APIRouter()


class GenerateClientsRequest(BaseModel):
    env_name: str
    node_name: str


class GenerateClientsResponse(BaseModel):
    clients_py: str
    snippets: dict  # keyed by dep node_name -> list of snippet dicts


def _extract_dependencies(workflow: dict) -> list[dict]:
    """Extract unified dependency list from a workflow definition."""
    dependencies = []
    for db_ref in workflow.get("db_refs", []):
        dep = {"ref_type": "db"}
        if isinstance(db_ref, dict):
            dep.update(db_ref)
        dependencies.append(dep)
    for invoke_ref in workflow.get("invoke_refs", []):
        dep = {"ref_type": "invoke"}
        if isinstance(invoke_ref, dict):
            dep.update(invoke_ref)
        dependencies.append(dep)
    for pubsub_ref in workflow.get("pubsub_refs", []):
        dep = {"ref_type": "pubsub"}
        if isinstance(pubsub_ref, dict):
            dep.update(pubsub_ref)
        dependencies.append(dep)
    return dependencies


def _get_node_workflow(blueprint: dict, node_name: str) -> tuple[list[dict], dict]:
    """Resolve a node's workflow and the full node list from a blueprint.

    Returns:
        Tuple of (all_nodes, workflow_dict).

    Raises:
        HTTPException if blueprint or node not found.
    """
    envelope = blueprint.get("envelope")
    if not envelope:
        raise HTTPException(404, "No blueprint found")
    nodes = envelope.get("nodes", [])
    source_node = next((n for n in nodes if n.get("name") == node_name), None)
    if not source_node:
        raise HTTPException(404, f"Node {node_name!r} not found")
    config = source_node.get("config", {})
    workflow = config.get("workflow", {}) or {}
    return nodes, workflow


@router.post("/dependencies/{project_ref_id}/generate-clients")
async def generate_clients(
    project_ref_id: str,
    body: GenerateClientsRequest,
    access: ProjectAccess = Depends(require_project_access("viewer")),
):
    """Generate clients.py and snippets from a node's declared dependencies."""
    owner_uid = access.owner_uid
    blueprint = blueprint_store.get_env_blueprint(owner_uid, project_ref_id, body.env_name)
    if not blueprint or not blueprint.get("envelope"):
        raise HTTPException(404, "No blueprint found")

    nodes, workflow = _get_node_workflow(blueprint, body.node_name)
    dependencies = _extract_dependencies(workflow)
    clients_py = generate_clients_py(dependencies, nodes)
    snippets = generate_snippets(dependencies, nodes)
    return GenerateClientsResponse(clients_py=clients_py, snippets=snippets)


@router.get("/dependencies/{project_ref_id}/{env_name}/{node_name}/snippets")
async def get_snippets(
    project_ref_id: str,
    env_name: str,
    node_name: str,
    access: ProjectAccess = Depends(require_project_access("viewer")),
):
    """Get contextual code snippets for a node's dependencies."""
    owner_uid = access.owner_uid
    blueprint = blueprint_store.get_env_blueprint(owner_uid, project_ref_id, env_name)
    if not blueprint or not blueprint.get("envelope"):
        raise HTTPException(404, "No blueprint found")

    nodes, workflow = _get_node_workflow(blueprint, node_name)
    dependencies = _extract_dependencies(workflow)
    snippets = generate_snippets(dependencies, nodes)
    return {"snippets": snippets}
