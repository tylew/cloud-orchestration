"""Individual node CRUD with inline validation (D-02)."""

import logging
import random
import string
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from pydantic import BaseModel

from packages.core.schemas.base import BaseNode, Envelope
from packages.core.schemas.enums import NodeType
from packages.platform.auth.authz import require_project_access, ProjectAccess
from packages.platform.store import blueprints as blueprint_store
from packages.core.validation import validate_blueprint_by_slug

router = APIRouter()
log = logging.getLogger(__name__)

# Slug prefix map: type abbreviation (unique per type -- no collisions)
_SLUG_PREFIXES = {
    "cloud_run": "cr", "cloud_run_job": "cj", "cloud_function": "cf",
    "service_account": "sa", "vpc": "vp", "subnet": "sn",
    "vpc_connector": "vc", "secret_manager": "sm", "gcs_bucket": "gs",
    "cloud_sql": "sq", "firestore": "fs", "bigquery": "bq",
    "bigtable": "bt", "pubsub_schema": "ps", "pubsub_topic": "pt",
    "pubsub_subscription": "pb", "cloud_task_queue": "tq",
    "external_lb": "lb", "third_party_api": "tp",
    "firestore_collection": "fc", "bigquery_table": "bqt",
    "cloud_sql_database": "sd", "cloud_sql_table": "st",
    "cloud_dns": "dn",
}


def _dump_node(node: BaseNode) -> dict:
    """Serialize a BaseNode, handling the polymorphic config field correctly.

    BaseNode.model_dump() produces an empty config dict due to Pydantic's union
    type serialization (dict[str, Any] | BaseModel picks dict serializer).
    We fix this by dumping config separately.
    """
    data = node.model_dump(mode="json", by_alias=True)
    if isinstance(node.config, BaseModel):
        data["config"] = node.config.model_dump(mode="json")
    return data


def _generate_slug(node_type: str) -> str:
    """Generate a unique slug with type-based prefix and random suffix."""
    prefix = _SLUG_PREFIXES.get(node_type, "nd")
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{prefix}-{suffix}"


def _run_validation_and_persist(
    tenant_id: str, project_ref_id: str, env_name: str
) -> dict[str, dict]:
    """Load all nodes, run validation, persist results, return per-slug dict."""
    all_node_dicts = blueprint_store.list_nodes(tenant_id, project_ref_id, env_name)
    # Build a minimal envelope for validation
    envelope = Envelope.model_validate({
        "global": {"project_id": "validation", "region": "us-central1", "environment": "dev"},
        "nodes": all_node_dicts,
    })
    validation = validate_blueprint_by_slug(envelope)
    blueprint_store.save_validation_doc(tenant_id, project_ref_id, env_name, {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "nodes": validation,
    })
    return validation


@router.post("/projects/{project_ref_id}/envs/{env_name}/nodes")
async def create_node(
    project_ref_id: str,
    env_name: str,
    payload: dict,
    access: ProjectAccess = Depends(require_project_access("editor")),
):
    """Create a new node. Validates via Pydantic, generates slug, persists, runs validation."""
    # Generate slug if not provided
    node_type = payload.get("type", "")
    if not payload.get("slug"):
        payload["slug"] = _generate_slug(node_type)

    # Validate through Pydantic (strict -- rejects unknown types per D-05)
    try:
        node = BaseNode.model_validate(payload)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Check slug uniqueness
    existing = blueprint_store.get_node(access.user.tenant_id, project_ref_id, env_name, node.slug)
    if existing:
        raise HTTPException(status_code=409, detail=f"Node with slug '{node.slug}' already exists")

    # Persist
    node_data = _dump_node(node)
    blueprint_store.save_node(access.user.tenant_id, project_ref_id, env_name, node.slug, node_data)

    # Run validation on full blueprint and persist (D-03)
    validation = _run_validation_and_persist(access.user.tenant_id, project_ref_id, env_name)
    node_validation = validation.get(node.slug, {"errors": [], "warnings": []})

    return {
        "node": node_data,
        "validation": node_validation,
    }


@router.patch("/projects/{project_ref_id}/envs/{env_name}/nodes/{slug}")
async def update_node(
    project_ref_id: str,
    env_name: str,
    slug: str,
    payload: dict,
    access: ProjectAccess = Depends(require_project_access("editor")),
):
    """Update a node's config. Merges payload into existing node, re-validates."""
    existing = blueprint_store.get_node(access.user.tenant_id, project_ref_id, env_name, slug)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Node '{slug}' not found")

    # Merge: payload fields override existing
    merged = {**existing, **payload}
    merged["slug"] = slug  # Slug is immutable

    # Validate merged node through Pydantic
    try:
        node = BaseNode.model_validate(merged)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Persist
    node_data = _dump_node(node)
    blueprint_store.save_node(access.user.tenant_id, project_ref_id, env_name, slug, node_data)

    # Run validation and persist
    validation = _run_validation_and_persist(access.user.tenant_id, project_ref_id, env_name)
    node_validation = validation.get(slug, {"errors": [], "warnings": []})

    return {
        "node": node_data,
        "validation": node_validation,
    }


@router.delete("/projects/{project_ref_id}/envs/{env_name}/nodes/{slug}")
async def delete_node_endpoint(
    project_ref_id: str,
    env_name: str,
    slug: str,
    access: ProjectAccess = Depends(require_project_access("editor")),
):
    """Delete a node and cascade-delete children."""
    existing = blueprint_store.get_node(access.user.tenant_id, project_ref_id, env_name, slug)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Node '{slug}' not found")

    deleted_slugs = blueprint_store.delete_node(access.user.tenant_id, project_ref_id, env_name, slug)

    # Re-run validation after deletion
    validation = _run_validation_and_persist(access.user.tenant_id, project_ref_id, env_name)

    return {
        "deleted": deleted_slugs,
        "validation_updated": True,
    }


@router.get("/projects/{project_ref_id}/envs/{env_name}/nodes")
async def list_nodes_endpoint(
    project_ref_id: str,
    env_name: str,
    access: ProjectAccess = Depends(require_project_access("viewer")),
):
    """List all nodes for an environment with validation state."""
    nodes = blueprint_store.list_nodes(access.user.tenant_id, project_ref_id, env_name)
    validation_doc = blueprint_store.get_validation_doc(access.user.tenant_id, project_ref_id, env_name)
    validation = validation_doc.get("nodes", {}) if validation_doc else {}

    return {
        "nodes": nodes,
        "validation": validation,
    }
