"""Response formatting utilities for MCP tool output."""

import json
from typing import Any


def format_json_response(data: Any, indent: int = 2) -> str:
    """Format data as a JSON string for MCP tool responses."""
    return json.dumps(data, indent=indent, default=str)


def format_error(error_type: str, message: str, details: Any = None) -> str:
    """Format an error response as structured JSON for MCP isError flag."""
    error = {"error_type": error_type, "message": message}
    if details:
        error["details"] = details
    return json.dumps(error, indent=2, default=str)


def format_list(items: list[dict], fields: list[str], title: str = "") -> str:
    """Format a list of items as a human-readable string."""
    if not items:
        return f"No {title} found." if title else "No items found."
    lines = []
    if title:
        lines.append(f"## {title} ({len(items)})")
        lines.append("")
    for item in items:
        parts = [f"{f}: {item.get(f, 'N/A')}" for f in fields]
        lines.append("- " + " | ".join(parts))
    return "\n".join(lines)
