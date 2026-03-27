"""GCP Orchestration MCP server — agent-callable tools for infrastructure management."""

import logging
import sys

# Resolve namespace collision: when packages/ is on sys.path (e.g., pytest),
# 'mcp' resolves to packages/mcp/ instead of the installed mcp library.
# Fix by temporarily removing conflicting paths during import.
import os as _os

_this_dir = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
_saved = []
for _i, _p in enumerate(sys.path):
    if _os.path.abspath(_p) == _this_dir:
        _saved.append((_i, _p))

for _idx, (_i, _p) in enumerate(_saved):
    sys.path.pop(_i - _idx)

# Remove any cached 'mcp' module that points to our package
_cached_mcp = sys.modules.pop("mcp", None)

from mcp.server.fastmcp import FastMCP  # noqa: E402

# Restore sys.path and our mcp module reference
for _i, _p in _saved:
    sys.path.insert(_i, _p)
if _cached_mcp is not None:
    sys.modules.setdefault("mcp", _cached_mcp)

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
log = logging.getLogger(__name__)

mcp = FastMCP(
    "gcp-orchestration",
    instructions="GCP infrastructure orchestration platform — manage projects, resources, secrets, builds, and deploys",
)

# Tool modules register themselves when imported
from packages.mcp.tools import projects, blueprint, nodes, secrets, code_files, builds, deploy  # noqa: E402, F401

if __name__ == "__main__":
    mcp.run(transport="stdio")
