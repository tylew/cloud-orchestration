"""Node reference resolution and topological sort for Terraform generation."""

import re
from collections import defaultdict

from core.schemas.base import BaseNode, Envelope
from core.registry import REGISTRY


def resolve_node_ref(ref: str, nodes: dict[str, BaseNode]) -> str:
    """Resolve node references to Terraform resource references.

    Handles two formats:
    1. 'node:vpc-main.self_link' -> 'google_compute_network.vpc-main.self_link'
    2. 'my-vpc' (bare node name) -> 'google_compute_network.my-vpc.id'

    Bare strings that don't match any known node name are returned as-is.
    """
    # Format 1: explicit node:name.attribute
    match = re.match(r"^node:([^.]+)\.(.+)$", ref)
    if match:
        node_name, attribute = match.groups()
        node = nodes.get(node_name)
        if not node:
            return ref
        defn = REGISTRY.get(node.type)
        if not defn:
            return ref
        # Non-TF nodes (e.g. third_party_api): inline the config value as a quoted string
        if not defn.terraform_resource:
            config = node.config
            if hasattr(config, attribute):
                return f'"{getattr(config, attribute)}"'
            if isinstance(config, dict) and attribute in config:
                return f'"{config[attribute]}"'
            return ref
        return f"{defn.terraform_resource}.{node_name}.{attribute}"

    # Format 2: bare node name -> resource.name.id
    node = nodes.get(ref)
    if node:
        defn = REGISTRY.get(node.type)
        if defn and defn.terraform_resource:
            return f"{defn.terraform_resource}.{ref}.id"

    # Not a node reference — return as-is
    return ref


def topological_sort(nodes: list[BaseNode]) -> list[BaseNode]:
    """Sort nodes respecting depends_on ordering."""
    node_map = {n.name: n for n in nodes}
    in_degree: dict[str, int] = defaultdict(int)
    adj: dict[str, list[str]] = defaultdict(list)
    all_names = [n.name for n in nodes]

    for node in nodes:
        in_degree.setdefault(node.name, 0)
        for dep in node.depends_on:
            if dep in node_map:
                adj[dep].append(node.name)
                in_degree[node.name] += 1

    queue = [n for n in all_names if in_degree[n] == 0]
    result: list[str] = []

    while queue:
        current = queue.pop(0)
        result.append(current)
        for neighbor in adj[current]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # Append any remaining (cycle) nodes at end
    for name in all_names:
        if name not in result:
            result.append(name)

    return [node_map[name] for name in result]
