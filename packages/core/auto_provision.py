"""Auto-provisioning orchestration for compute nodes.

When a compute node is added, this module automatically creates supporting
resources: service accounts, and (when needed) VPC/subnet/connector.
"""

from packages.core.schemas.enums import COMPUTE_TYPES, NodeType
from packages.core.iam_mappings import PRIVATE_ACCESS_TYPES


def auto_provision_for_node(
    node_data: dict, existing_nodes: list[dict], region: str = "us-central1"
) -> dict:
    """Auto-provision supporting resources for a node.

    Returns {"created": list[dict], "warnings": list[str]}.
    Only compute nodes trigger provisioning; all others return empty.

    Args:
        node_data: The node being added.
        existing_nodes: All existing nodes in the blueprint.
        region: The project's region (from global config or env entry).
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
            networking_nodes = _create_networking_stack(region)
            created.extend(networking_nodes)

        # Add connector dependency and wire vpc_access on the compute node
        connector_slug = "default-connector"
        if connector_slug not in node_data["depends_on"]:
            node_data["depends_on"].append(connector_slug)

        # Wire vpc_access into the compute node's config
        config = node_data.get("config", {})
        if isinstance(config, dict) and "vpc_access" not in config:
            config["vpc_access"] = {
                "connector": "node:default-connector.id",
                "egress": "PRIVATE_RANGES_ONLY",
            }
            node_data["config"] = config

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
    # Build lookup by both name and slug
    node_type_lookup: dict[str, str] = {}
    for n in existing_nodes:
        node_type_lookup[n.get("name", "")] = n.get("type", "")
        node_type_lookup[n.get("slug", "")] = n.get("type", "")
    for dep in depends_on:
        dep_type = node_type_lookup.get(dep)
        if dep_type:
            try:
                if NodeType(dep_type) in PRIVATE_ACCESS_TYPES:
                    return True
            except ValueError:
                pass
    return False


def _has_existing_networking(existing_nodes: list[dict]) -> bool:
    """Check if VPC/subnet/connector already exist."""
    existing_types = {n.get("type") for n in existing_nodes}
    return "vpc" in existing_types


def _create_networking_stack(region: str = "us-central1") -> list[dict]:
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
            "config": {
                "ip_cidr_range": "10.8.0.0/28",
                "region": region,
                "network": "node:default-vpc.id",
            },
            "depends_on": ["default-vpc"],
            "auto_provisioned": True,
        },
        {
            "name": "default-connector",
            "type": "vpc_connector",
            "slug": "default-connector",
            "config": {
                "region": region,
                "ip_cidr_range": "10.9.0.0/28",  # Different CIDR from subnet
                "network": "node:default-vpc.id",
            },
            "depends_on": ["default-subnet"],
            "auto_provisioned": True,
        },
    ]
