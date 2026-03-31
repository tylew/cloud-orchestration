"""Node reference resolution and topological sort for Terraform generation."""

import re
from collections import defaultdict

from core.schemas.base import BaseNode, Envelope
from core.registry import REGISTRY


def resolve_node_ref(ref: str, nodes: dict[str, BaseNode]) -> str:
    """Resolve 'node:vpc-main.self_link' -> 'google_compute_network.vpc-main.self_link'."""
    match = re.match(r"^node:([^.]+)\.(.+)$", ref)
    if not match:
        return ref

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

    tf_name = node_name
    return f"{defn.terraform_resource}.{tf_name}.{attribute}"


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
