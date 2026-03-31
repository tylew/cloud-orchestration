"""Blueprint validation — required fields, naming, parent refs."""

from collections import defaultdict
from dataclasses import dataclass

from pydantic import BaseModel

from core.schemas.base import Envelope, BaseNode
from core.schemas.enums import CHILD_PARENT_MAP


@dataclass
class ValidationIssue:
    severity: str  # "error" | "warning"
    node: str | None
    message: str


@dataclass
class FieldRequirement:
    field_path: str  # dot-path into config, e.g. "image", "runtime"
    severity: str    # "error" or "warning"
    message: str


REQUIRED_FIELDS: dict[str, list[FieldRequirement]] = {
    # -- Compute types --
    "cloud_run": [
        FieldRequirement("image", "error", "Container image is required"),
        FieldRequirement("service_account", "error", "Service account is required"),
        FieldRequirement("cpu", "warning", "CPU not set (defaults to 1000m)"),
        FieldRequirement("memory", "warning", "Memory not set (defaults to 512Mi)"),
        FieldRequirement("port", "warning", "Port not set (defaults to 8080)"),
    ],
    "cloud_function": [
        FieldRequirement("runtime", "error", "Runtime is required"),
        FieldRequirement("entry_point", "error", "Entry point is required"),
        FieldRequirement("service_account", "error", "Service account is required"),
    ],
    "cloud_run_job": [
        FieldRequirement("image", "error", "Container image is required"),
        FieldRequirement("service_account", "error", "Service account is required"),
    ],
    # -- Database / storage types --
    "cloud_sql": [
        FieldRequirement("database_version", "error", "Database version is required"),
        FieldRequirement("tier", "error", "Machine tier is required"),
    ],
    "firestore": [
        FieldRequirement("location_id", "error", "Location is required"),
    ],
    "bigquery": [
        FieldRequirement("location", "warning", "Location not set (defaults to 'US')"),
    ],
    "gcs_bucket": [
        FieldRequirement("location", "error", "Location is required"),
    ],
    "bigtable": [
    ],
    # -- IAM / networking types --
    "service_account": [
    ],
    "vpc": [],  # VPC has sensible defaults (auto_create_subnetworks is explicit bool)
    "subnet": [
        FieldRequirement("ip_cidr_range", "error", "IP CIDR range is required"),
        FieldRequirement("region", "error", "Region is required"),
        FieldRequirement("network", "error", "Network reference is required"),
    ],
    "vpc_connector": [
        FieldRequirement("region", "error", "Region is required"),
        FieldRequirement("ip_cidr_range", "error", "IP CIDR range is required"),
        FieldRequirement("network", "error", "Network reference is required"),
    ],
    # -- Pub/Sub types --
    "pubsub_schema": [
        FieldRequirement("definition", "warning", "Schema definition not set"),
    ],
    "pubsub_topic": [],  # PubSub Topic has sensible defaults
    "pubsub_subscription": [
        FieldRequirement("topic", "error", "Topic reference is required"),
    ],
    # -- Misc infrastructure types --
    "cloud_task_queue": [
        FieldRequirement("location", "error", "Location is required"),
    ],
    "external_lb": [
        FieldRequirement("backend_service", "error", "Backend service reference is required"),
    ],
    "cloud_dns": [
        FieldRequirement("dns_name", "error", "DNS name (domain) is required"),
    ],
    # -- Child data node types (with real TF resources) --
    "bigquery_table": [
        FieldRequirement("parentRef", "error", "Parent reference is required"),
    ],
    "cloud_sql_database": [
        FieldRequirement("parentRef", "error", "Parent reference is required"),
    ],
}

GLOBAL_UNIQUE_TYPES = {"cloud_sql", "gcs_bucket"}


def _get_config_dict(node: BaseNode) -> dict:
    """Get config as a plain dict — config is always a BaseModel after validation."""
    return node.config.model_dump()


def validate_required_fields(nodes: list[BaseNode]) -> list[ValidationIssue]:
    """Check each node's config for required/warning fields per type."""
    issues: list[ValidationIssue] = []
    for node in nodes:
        reqs = REQUIRED_FIELDS.get(str(node.type), [])
        if not reqs:
            continue
        config = _get_config_dict(node)
        for req in reqs:
            value = config.get(req.field_path)
            if not value and value != 0 and value is not False:
                issues.append(ValidationIssue(req.severity, node.name, req.message))
    return issues


def validate_per_type_name_uniqueness(nodes: list[BaseNode]) -> list[ValidationIssue]:
    """Find duplicate names within each resource type (D-18)."""
    issues: list[ValidationIssue] = []
    by_type: dict[str, list[str]] = defaultdict(list)
    for node in nodes:
        by_type[str(node.type)].append(node.name)
    for node_type, names in by_type.items():
        seen: set[str] = set()
        for name in names:
            if name in seen:
                issues.append(ValidationIssue(
                    "error", name,
                    f"A {node_type} named \"{name}\" already exists",
                ))
            seen.add(name)
    return issues


def validate_global_uniqueness(nodes: list[BaseNode]) -> list[ValidationIssue]:
    """Warn about types whose names must be globally unique in GCP (D-19)."""
    issues: list[ValidationIssue] = []
    for node in nodes:
        if str(node.type) in GLOBAL_UNIQUE_TYPES:
            issues.append(ValidationIssue(
                "warning", node.name,
                f"{node.type} names must be globally unique in GCP",
            ))
    return issues


def validate_firestore_free_tier(nodes: list[BaseNode]) -> list[ValidationIssue]:
    """Warn when Firestore database_id is not '(default)' (D-14).
    
    NOTE: database_id was removed from FirestoreConfig as part of the
    resource_id naming abstraction. All Firestore databases now use the
    '(default)' name derived from gcp_name_template. This check is a no-op
    but retained for backward compatibility with blueprints that may still
    carry database_id in extra fields.
    """
    return []


def validate_parent_refs(nodes: list[BaseNode]) -> list[ValidationIssue]:
    """Validate child node parentRef points to existing parent of correct type (D-06)."""
    issues: list[ValidationIssue] = []
    slug_map = {n.slug: n for n in nodes if n.slug}
    for node in nodes:
        expected_parent = CHILD_PARENT_MAP.get(node.type)
        if expected_parent is None:
            continue  # Not a child type
        parent_ref = getattr(node.config, 'parentRef', None)
        if not parent_ref:
                continue  # Already caught by REQUIRED_FIELDS
        parent = slug_map.get(parent_ref)
        if parent is None:
            issues.append(ValidationIssue(
                "error", node.name,
                f"parentRef '{parent_ref}' references a non-existent node",
            ))
        elif parent.type != expected_parent:
            issues.append(ValidationIssue(
                "error", node.name,
                f"parentRef '{parent_ref}' points to {parent.type.value} "
                f"but expected {expected_parent.value}",
            ))
    return issues



def validate_blueprint_by_slug(envelope: Envelope) -> dict[str, dict]:
    """Run full validation and return results keyed by node slug (D-03).

    Returns: {
        "cr-a1b2c3": {"errors": [{"message": "..."}], "warnings": [...]},
        ...
    }
    """
    nodes = envelope.nodes

    # Reuse existing full validation (includes cross-node checks)
    all_issues = validate_blueprint(envelope)

    # Build name-to-slug lookup (fallback to name if no slug)
    name_to_slug: dict[str, str] = {}
    for n in nodes:
        name_to_slug[n.name] = n.slug or n.name

    # Initialize result with empty entries per node
    result: dict[str, dict] = {}
    for n in nodes:
        slug = n.slug or n.name
        result[slug] = {"errors": [], "warnings": []}

    # Group issues by slug
    for issue in all_issues:
        slug = name_to_slug.get(issue.node, issue.node or "__global__")
        if slug not in result:
            result[slug] = {"errors": [], "warnings": []}
        entry = {"message": issue.message}
        if issue.severity == "error":
            result[slug]["errors"].append(entry)
        else:
            result[slug]["warnings"].append(entry)

    return result


def validate_blueprint(envelope: Envelope) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    node_map: dict[str, BaseNode] = {n.name: n for n in envelope.nodes}

    # Unique node names
    seen_names: set[str] = set()
    for node in envelope.nodes:
        if node.name in seen_names:
            issues.append(ValidationIssue("error", node.name, f"Duplicate node name: {node.name!r}"))
        seen_names.add(node.name)

    # Required field validation per resource type (D-20, D-21)
    issues.extend(validate_required_fields(envelope.nodes))

    # Per-type name uniqueness (D-18)
    issues.extend(validate_per_type_name_uniqueness(envelope.nodes))

    # Global uniqueness warnings for SQL/GCS (D-19)
    issues.extend(validate_global_uniqueness(envelope.nodes))

    # Firestore free-tier database_id check (D-14)
    issues.extend(validate_firestore_free_tier(envelope.nodes))

    # Cross-node reference validation (D-06)
    issues.extend(validate_parent_refs(envelope.nodes))

    return issues
