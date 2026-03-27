"""GCP Orchestration MCP server — agent-callable tools for infrastructure management."""

import logging
import sys

from mcp.server.fastmcp import FastMCP

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
log = logging.getLogger(__name__)

mcp = FastMCP(
    "gcp-orchestration",
    description="GCP infrastructure orchestration platform — manage projects, resources, secrets, builds, and deploys",
)

# Tool modules register themselves when imported
from packages.mcp.tools import projects, blueprint  # noqa: E402, F401

if __name__ == "__main__":
    mcp.run(transport="stdio")
