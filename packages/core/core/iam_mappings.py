"""IAM role inference from ActionType x NodeType dependency edges."""

from core.schemas.enums import NodeType, COMPUTE_TYPES


# (ActionType_value, NodeType_value) -> GCP IAM role string
IAM_ROLE_MAP: dict[tuple[str, str], str] = {
    # Cloud SQL — single client role covers read + write
    ("Read", "cloud_sql"): "roles/cloudsql.client",
    ("Write", "cloud_sql"): "roles/cloudsql.client",
    # Firestore — datastore.user covers read + write
    ("Read", "firestore"): "roles/datastore.user",
    ("Write", "firestore"): "roles/datastore.user",
    # BigQuery — separate viewer vs editor
    ("Read", "bigquery"): "roles/bigquery.dataViewer",
    ("Write", "bigquery"): "roles/bigquery.dataEditor",
    # Bigtable — reader vs user (read+write)
    ("Read", "bigtable"): "roles/bigtable.reader",
    ("Write", "bigtable"): "roles/bigtable.user",
    # GCS — objectViewer vs objectAdmin
    ("Read", "gcs_bucket"): "roles/storage.objectViewer",
    ("Write", "gcs_bucket"): "roles/storage.objectAdmin",
    # Compute invocation
    ("Invoke", "cloud_run"): "roles/run.invoker",
    ("Invoke", "cloud_function"): "roles/cloudfunctions.invoker",
    # Messaging
    ("Emit", "pubsub_topic"): "roles/pubsub.publisher",
    ("Enqueue", "cloud_task_queue"): "roles/cloudtasks.enqueuer",
    # Secret Manager
    ("Read", "secret_manager"): "roles/secretmanager.secretAccessor",
    ("Write", "secret_manager"): "roles/secretmanager.secretVersionAdder",
}

# Node types that require private network access (VPC connector) per D-11.
PRIVATE_ACCESS_TYPES: set[NodeType] = {NodeType.CLOUD_SQL, NodeType.BIGTABLE}


def get_iam_role(action_type: str, target_node_type: str) -> str | None:
    """Look up the IAM role for a given action + target combination.

    Returns None if the combination is not recognized.
    """
    return IAM_ROLE_MAP.get((action_type, target_node_type))


def infer_iam_roles(node_data: dict, all_nodes: list[dict]) -> set[str]:
    """Infer required IAM roles from a node's dependency graph.

    Currently infers implicit Read roles from depends_on references.
    Will be extended to consume ServiceContract when implemented
    (see docs/specs/service-contract.md).
    """
    roles: set[str] = set()

    # Build name -> type lookup from all nodes
    node_type_by_name: dict[str, str] = {
        n["name"]: n["type"] for n in all_nodes
    }

    # Only compute nodes get IAM roles inferred
    if node_data.get("type") not in {t.value for t in COMPUTE_TYPES}:
        return roles

    # For depends_on refs, infer implicit Read role
    depends_on = node_data.get("depends_on", [])
    for dep_name in depends_on:
        target_type = node_type_by_name.get(dep_name)
        if target_type:
            role = get_iam_role("Read", target_type)
            if role:
                roles.add(role)

    return roles
