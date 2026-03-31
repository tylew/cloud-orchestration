"""Cross-storage-type field path resolution for schema contracts (Phase 2 -- GRAPH-03).

Resolves field references across Firestore collections/subcollections, Cloud SQL
tables, and BigQuery tables. Used by validation.py to catch broken field references
before deploy.
"""

from __future__ import annotations

import re

from packages.core.schemas.configs.firestore import FirestoreConfig, FirestoreCollection, FirestoreField
from packages.core.schemas.configs.cloud_sql import CloudSqlConfig
from packages.core.schemas.configs.bigquery import BigQueryConfig


def resolve_field_ref(node_type: str, config: dict, field_path: str) -> bool:
    """Check whether a field path resolves against the node's config schema.

    Args:
        node_type: Storage node type ("firestore", "cloud_sql", "bigquery").
        config: Raw config dict for the storage node.
        field_path: Dot-separated path, e.g. "users.email", "app_db.users.id",
                    or "users/{id}/orders.total" for Firestore subcollections.

    Returns:
        True if the field exists in the schema, False otherwise.
    """
    if node_type == "firestore":
        return _resolve_firestore(config, field_path)
    elif node_type == "cloud_sql":
        return _resolve_cloud_sql(config, field_path)
    elif node_type == "bigquery":
        return _resolve_bigquery(config, field_path)
    return False


def collect_storage_fields(node_type: str, config: dict) -> list[str]:
    """Return all available field paths for a storage node.

    Args:
        node_type: Storage node type ("firestore", "cloud_sql", "bigquery").
        config: Raw config dict for the storage node.

    Returns:
        List of dot-separated field paths.
    """
    if node_type == "firestore":
        return _collect_firestore(config)
    elif node_type == "cloud_sql":
        return _collect_cloud_sql(config)
    elif node_type == "bigquery":
        return _collect_bigquery(config)
    return []


# --- Firestore ---


def _resolve_firestore(config: dict, field_path: str) -> bool:
    """Resolve a Firestore field path like 'users.email' or 'users/{id}/orders.total'."""
    parsed = FirestoreConfig.model_validate(config)

    # Split on '/' to handle subcollection paths, stripping {id} segments
    segments = field_path.split("/")
    # Remove {id}-like segments (e.g., "{id}", "{userId}")
    segments = [s for s in segments if not re.match(r"^\{.*\}$", s)]

    if not segments:
        return False

    # The last segment should contain "collection.field"
    last = segments[-1]
    if "." not in last:
        return False

    dot_idx = last.index(".")
    last_collection_name = last[:dot_idx]
    field_name = last[dot_idx + 1:]

    # Build the collection path to walk
    collection_path = [s for s in segments[:-1]] + [last_collection_name]

    # Walk collections tree
    collection = _find_collection(parsed.collections, collection_path)
    if collection is None:
        return False

    return _field_exists(collection.fields, field_name)


def _find_collection(
    collections: list[FirestoreCollection], path: list[str]
) -> FirestoreCollection | None:
    """Walk collection/subcollection tree to find the target collection."""
    if not path:
        return None

    target_name = path[0]
    for coll in collections:
        if coll.path == target_name:
            if len(path) == 1:
                return coll
            # Walk into subcollections for remaining path
            return _find_collection(coll.subcollections, path[1:])
    return None


def _field_exists(fields: list[FirestoreField], name: str) -> bool:
    """Check if a field name exists, supporting dot-notation for map subfields."""
    parts = name.split(".", 1)
    for f in fields:
        if f.name == parts[0]:
            if len(parts) == 1:
                return True
            # Walk into subfields for map types
            if f.subfields:
                return _field_exists(f.subfields, parts[1])
            return False
    return False


def _collect_firestore(config: dict) -> list[str]:
    """Collect all field paths from Firestore config."""
    parsed = FirestoreConfig.model_validate(config)
    paths: list[str] = []
    for coll in parsed.collections:
        _collect_firestore_collection(coll, "", paths)
    return paths


def _collect_firestore_collection(
    coll: FirestoreCollection, prefix: str, paths: list[str]
) -> None:
    """Recursively collect field paths from a collection and its subcollections."""
    coll_prefix = f"{prefix}{coll.path}"
    _collect_firestore_fields(coll.fields, f"{coll_prefix}.", paths)

    for sub in coll.subcollections:
        _collect_firestore_collection(sub, f"{coll_prefix}/{{id}}/", paths)


def _collect_firestore_fields(
    fields: list[FirestoreField], prefix: str, paths: list[str]
) -> None:
    """Collect field paths, including nested map subfields."""
    for f in fields:
        full_path = f"{prefix}{f.name}"
        paths.append(full_path)
        if f.subfields:
            _collect_firestore_fields(f.subfields, f"{full_path}.", paths)


# --- Cloud SQL ---


def _resolve_cloud_sql(config: dict, field_path: str) -> bool:
    """Resolve a Cloud SQL field path like 'app_db.users.email'."""
    parsed = CloudSqlConfig.model_validate(config)
    parts = field_path.split(".")
    if len(parts) != 3:
        return False

    db_name, table_name, column_name = parts
    for db in parsed.databases:
        if db.name == db_name:
            for table in db.tables:
                if table.name == table_name:
                    return any(col.name == column_name for col in table.columns)
    return False


def _collect_cloud_sql(config: dict) -> list[str]:
    """Collect all column paths from Cloud SQL config."""
    parsed = CloudSqlConfig.model_validate(config)
    paths: list[str] = []
    for db in parsed.databases:
        for table in db.tables:
            for col in table.columns:
                paths.append(f"{db.name}.{table.name}.{col.name}")
    return paths


# --- BigQuery ---


def _resolve_bigquery(config: dict, field_path: str) -> bool:
    """Resolve a BigQuery field path like 'events.user_id' (table.column)."""
    parsed = BigQueryConfig.model_validate(config)
    parts = field_path.split(".")
    if len(parts) != 2:
        return False

    table_id, column_name = parts
    for table in parsed.tables:
        if table.table_id == table_id:
            return any(col.name == column_name for col in table.columns)
    return False


def _collect_bigquery(config: dict) -> list[str]:
    """Collect all column paths from BigQuery config."""
    parsed = BigQueryConfig.model_validate(config)
    paths: list[str] = []
    for table in parsed.tables:
        for col in table.columns:
            paths.append(f"{table.table_id}.{col.name}")
    return paths
