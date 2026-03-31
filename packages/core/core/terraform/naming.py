"""GCP resource naming — derives deterministic names from node identity."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.schemas.base import BaseNode
    from core.schemas.enums import NodeType

from core.registry import REGISTRY


def resolve_gcp_name(
    node: BaseNode,
    env: str,
    registry: dict | None = None,
) -> str:
    """Resolve the GCP-safe resource name for *node* in *env*.

    Looks up the ``gcp_name_template`` from the registry for the node's type
    and substitutes ``{rid}``, ``{env}``, and ``{name}`` placeholders.
    Returns the empty string when no template is defined (child/virtual types).
    """
    reg = registry or REGISTRY
    defn = reg.get(node.type)
    if defn is None:
        return ""
    template = defn.gcp_name_template
    if not template:
        return ""
    return (
        template
        .replace("{rid}", node.resource_id)
        .replace("{env}", env)
        .replace("{name}", node.name)
    )
