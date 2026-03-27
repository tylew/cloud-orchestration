"""Auto-provisioning orchestration for compute nodes.

When a compute node is added, this module automatically creates supporting
resources: service accounts, and (when needed) VPC/subnet/connector.
"""

from packages.core.schemas.enums import COMPUTE_TYPES, NodeType
from packages.core.iam_mappings import PRIVATE_ACCESS_TYPES


def auto_provision_for_node(
    node_data: dict, existing_nodes: list[dict]
) -> dict:
    """Auto-provision supporting resources for a node.

    Returns {"created": list[dict], "warnings": list[str]}.
    Only compute nodes trigger provisioning; all others return empty.
    """
    node_type = node_data.get("type", "")

    if node_type not in {t.value for t in COMPUTE_TYPES}:
        return {"created": [], "warnings": []}

    created: list[dict] = []
    warnings: list[str] = []
    compute_name = node_data["name"]

    # 1. Service account
    if _needs_service_account(compute_name, existing_nodes):
        sa_node = _create_sa_node(compute_name)
        created.append(sa_node)

    # Always add SA to depends_on
    sa_slug = f"sa-{compute_name}"
    if sa_slug not in node_data.get("depends_on", []):
        node_data.setdefault("depends_on", [])
        node_data["depends_on"].append(sa_slug)

    # 2. Networking (only if node depends on a private-access type)
    if _needs_private_access(node_data, existing_nodes):
        if not _has_existing_networking(existing_nodes):
            networking_nodes = _create_networking_stack()
            created.extend(networking_nodes)

        # Add connector dependency
        connector_slug = "default-connector"
        if connector_slug not in node_data["depends_on"]:
            node_data["depends_on"].append(connector_slug)

    return {"created": created, "warnings": warnings}


def _needs_service_account(
    compute_name: str, existing_nodes: list[dict]
) -> bool:
    """Check if a service account already exists for this compute node."""
    sa_name = f"sa-{compute_name}"
    return not any(
        n.get("name") == sa_name and n.get("type") == "service_account"
        for n in existing_nodes
    )


def _create_sa_node(compute_name: str) -> dict:
    """Create a service account node dict for a compute node."""
    return {
        "name": f"sa-{compute_name}",
        "type": "service_account",
        "slug": f"sa-{compute_name}",
        "config": {"account_id": f"sa-{compute_name}"},
        "depends_on": [],
        "auto_provisioned": True,
    }


def _needs_private_access(
    node_data: dict, existing_nodes: list[dict]
) -> bool:
    """Check if any dependency requires private network access."""
    depends_on = node_data.get("depends_on", [])
    node_type_by_name: dict[str, str] = {
        n["name"]: n["type"] for n in existing_nodes
    }
    for dep_name in depends_on:
        dep_type = node_type_by_name.get(dep_name)
        if dep_type and NodeType(dep_type) in PRIVATE_ACCESS_TYPES:
            return True
    return False


def _has_existing_networking(existing_nodes: list[dict]) -> bool:
    """Check if VPC/subnet/connector already exist."""
    existing_types = {n.get("type") for n in existing_nodes}
    return "vpc" in existing_types


def _create_networking_stack() -> list[dict]:
    """Create the default VPC + subnet + connector stack."""
    return [
        {
            "name": "default-vpc",
            "type": "vpc",
            "slug": "default-vpc",
            "config": {"auto_create_subnetworks": False},
            "depends_on": [],
            "auto_provisioned": True,
        },
        {
            "name": "default-subnet",
            "type": "subnet",
            "slug": "default-subnet",
            "config": {"ip_cidr_range": "10.8.0.0/28", "region": "us-central1"},
            "depends_on": ["default-vpc"],
            "auto_provisioned": True,
        },
        {
            "name": "default-connector",
            "type": "vpc_connector",
            "slug": "default-connector",
            "config": {"region": "us-central1", "ip_cidr_range": "10.8.0.0/28"},
            "depends_on": ["default-subnet"],
            "auto_provisioned": True,
        },
    ]
