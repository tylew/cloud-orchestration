# Phase 1: MCP Server + Agent Workflow + Dev Insight Board - Research

**Researched:** 2026-03-26
**Domain:** MCP server implementation, auto-provisioning intelligence, real-time dashboard
**Confidence:** HIGH

## Summary

Phase 1 builds three interconnected components on top of the existing FastAPI backend: (1) an MCP server that wraps the 57 existing API endpoints as agent-callable tools, (2) auto-provisioning intelligence that creates service accounts and networking resources automatically when compute nodes are added, and (3) a read-only developer insight board that subscribes to Firestore for real-time visibility.

The existing codebase is well-structured for this. All 16 API handler modules follow consistent patterns (FastAPI routers with `Depends()` auth injection), the 22 node types have complete Pydantic models and Terraform templates, and the deploy pipeline is fully wired. The MCP server can call handler logic directly (bypassing HTTP) since auth is bypassable via `AUTH_DISABLED=true`. The auto-provisioning layer sits between the MCP tool calls and the existing node CRUD operations, inserting supporting nodes automatically. The frontend is a new React app (or simplified view in the existing app) consuming Firestore real-time subscriptions.

**Primary recommendation:** Use the official `mcp` Python SDK (v1.26.0) with `FastMCP` to build a stdio-based MCP server in `packages/mcp/`. Tools should call the existing handler/store functions directly rather than making HTTP requests to the API. Auto-provisioning logic belongs in a new `packages/core/auto_provision.py` module that the MCP tools invoke after node creation.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AGT-01 | MCP tools for project lifecycle (list, get state, select env) | Existing `projects.py` handler has `list_projects`, `get_project`, env selection; wrap as MCP tools |
| AGT-02 | MCP tools for node CRUD (add, configure, delete, list with validation) | Existing `nodes.py` handler has full CRUD with inline validation; wrap directly |
| AGT-03 | MCP tools for secret management | Existing `secrets.py` handler has complete CRUD + versions; wrap directly |
| AGT-04 | MCP tools for code file management | Existing `code_files.py` handler has read/write/delete/list; wrap directly |
| AGT-05 | MCP tools for container builds | Existing `builds.py` handler has trigger + status + batch; wrap directly |
| AGT-06 | MCP tools for deploy operations | Existing `projects.py` has deploy endpoint, `deploy.py` has log streaming + status; wrap directly |
| AGT-07 | MCP tools for blueprint operations | Existing `blueprints.py` has get/save/validate, `terraform.py` has generate/preview; wrap directly |
| AGT-08 | Auto-create service account when compute node added | New logic: intercept node creation, generate SA node with appropriate roles |
| AGT-09 | Auto-create VPC/subnet/connector when compute needs private DB access | New logic: detect Cloud SQL/Bigtable deps, create networking stack |
| AGT-10 | IAM role bindings auto-inferred from dependency graph | New logic: ActionType + target NodeType -> GCP IAM role mapping table |
| AGT-11 | Read-only dashboard with Firestore real-time subscriptions | New React views consuming existing Firestore data (project doc, validation, deploys) |
| AGT-12 | Debug endpoints for raw state inspection | New FastAPI endpoints exposing raw Firestore docs and compiled TF |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `mcp` | 1.26.0 | MCP server SDK | Official Python SDK from modelcontextprotocol; `FastMCP` class auto-generates tool schemas from type hints |
| `fastapi` | >=0.115 | REST API (existing) | Already in use; debug endpoints added here |
| `pydantic` | >=2.0 | Schema validation (existing) | Already in use for all node configs |
| `react` | ^19.0.0 | Frontend (existing) | Already in use |
| `firebase` | ^12.11.0 | Firestore real-time subscriptions (existing) | Already in use for project doc listening |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `zustand` | ^5.0.0 | Frontend state management (existing) | New stores for insight board panels |
| `sse-starlette` | >=2.0 | SSE streaming (existing) | Deploy log streaming in insight board |
| `tailwindcss` | ^4.0.0 | Styling (existing) | Insight board UI |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `mcp` FastMCP | Raw JSON-RPC implementation | FastMCP handles tool schema generation, input validation, transport; no reason to hand-roll |
| stdio transport | SSE/HTTP transport | stdio is simpler for Claude Desktop/CLI integration; SSE adds network complexity for no benefit in dev workflow |
| Direct function calls | HTTP calls to own API | Direct calls avoid network overhead, auth bypass complexity, and error serialization; the MCP server runs in the same Python process context |

**Installation:**
```bash
pip install "mcp>=1.26.0"
```

## Architecture Patterns

### Recommended Project Structure
```
packages/
  mcp/
    __init__.py
    server.py           # FastMCP instance, tool registration
    tools/
      __init__.py
      projects.py       # AGT-01: project lifecycle tools
      nodes.py          # AGT-02: node CRUD tools
      secrets.py        # AGT-03: secret management tools
      code_files.py     # AGT-04: code file tools
      builds.py         # AGT-05: container build tools
      deploy.py         # AGT-06: deploy tools
      blueprint.py      # AGT-07: blueprint + terraform tools
  core/
    auto_provision.py   # AGT-08, AGT-09, AGT-10: auto-provisioning intelligence
    iam_mappings.py     # AGT-10: ActionType x NodeType -> IAM role table
  api/
    handlers/
      debug.py          # AGT-12: debug endpoints
apps/
  web/
    src/
      screens/
        InsightBoard.tsx        # AGT-11: main dashboard screen
      components/
        insight/
          ProjectStatePanel.tsx   # Project state summary
          ResourceListPanel.tsx   # Resource list with types
          ValidationPanel.tsx     # Per-node validation output
          TerraformPanel.tsx      # Terraform preview
          DeployPanel.tsx         # Deploy status + logs
          ActivityFeed.tsx        # Activity feed
      stores/
        insight-store.ts          # Zustand store for insight board state
```

### Pattern 1: MCP Tool Wrapping Existing Handlers
**What:** Each MCP tool calls existing store/handler functions directly, not via HTTP
**When to use:** For all AGT-01 through AGT-07 tools
**Example:**
```python
# Source: MCP Python SDK official docs + project codebase patterns
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("gcp-orchestration")

@mcp.tool()
async def list_projects() -> str:
    """List all projects for the current user."""
    from packages.platform.store import projects as project_store
    projects = project_store.list_projects(get_tenant_id())
    return format_projects(projects)

@mcp.tool()
async def add_node(
    project_ref_id: str,
    env_name: str,
    name: str,
    node_type: str,
    config: dict | None = None,
) -> str:
    """Add a new resource node to the blueprint.

    Args:
        project_ref_id: The project reference ID
        env_name: Environment name (e.g. 'dev')
        name: Node name in kebab-case
        node_type: Resource type (cloud_run, cloud_sql, firestore, etc.)
        config: Optional type-specific configuration
    """
    from packages.core.auto_provision import auto_provision_for_node

    # Create the node via existing store logic
    result = _create_node(project_ref_id, env_name, name, node_type, config)

    # Auto-provision supporting resources (AGT-08, AGT-09)
    auto_result = auto_provision_for_node(
        get_tenant_id(), project_ref_id, env_name, result["node"]
    )

    return format_node_result(result, auto_result)
```

### Pattern 2: Auto-Provisioning Intelligence
**What:** When a compute node is created, automatically create service account and networking nodes
**When to use:** AGT-08 and AGT-09
**Example:**
```python
# packages/core/auto_provision.py
from packages.core.schemas.enums import NodeType, COMPUTE_TYPES

PRIVATE_ACCESS_TYPES = {NodeType.CLOUD_SQL, NodeType.BIGTABLE}

def auto_provision_for_node(
    tenant_id: str,
    project_ref_id: str,
    env_name: str,
    node_data: dict,
) -> dict:
    """Create supporting resources when a compute node is added."""
    created = []
    node_type = NodeType(node_data["type"])

    if node_type not in COMPUTE_TYPES:
        return {"created": created}

    # AGT-08: Auto-create service account
    sa_node = _create_service_account(tenant_id, project_ref_id, env_name, node_data)
    created.append(sa_node)

    # AGT-09: Auto-create networking if private DB deps exist
    existing_nodes = blueprint_store.list_nodes(tenant_id, project_ref_id, env_name)
    needs_private = _needs_private_access(node_data, existing_nodes)
    if needs_private:
        net_nodes = _create_networking_stack(tenant_id, project_ref_id, env_name, existing_nodes)
        created.extend(net_nodes)

    # AGT-10: Auto-infer IAM roles
    iam_roles = _infer_iam_roles(node_data, existing_nodes)
    _update_sa_roles(tenant_id, project_ref_id, env_name, sa_node["slug"], iam_roles)

    return {"created": created}
```

### Pattern 3: IAM Role Inference from Dependency Graph
**What:** Map ActionType + target NodeType to GCP IAM roles
**When to use:** AGT-10
**Example:**
```python
# packages/core/iam_mappings.py
IAM_ROLE_MAP: dict[tuple[str, str], str] = {
    # (ActionType, target NodeType) -> GCP IAM role
    ("Read", "cloud_sql"): "roles/cloudsql.client",
    ("Write", "cloud_sql"): "roles/cloudsql.client",
    ("Read", "firestore"): "roles/datastore.user",
    ("Write", "firestore"): "roles/datastore.user",
    ("Read", "bigquery"): "roles/bigquery.dataViewer",
    ("Write", "bigquery"): "roles/bigquery.dataEditor",
    ("Read", "bigtable"): "roles/bigtable.reader",
    ("Write", "bigtable"): "roles/bigtable.user",
    ("Read", "gcs_bucket"): "roles/storage.objectViewer",
    ("Write", "gcs_bucket"): "roles/storage.objectAdmin",
    ("Invoke", "cloud_run"): "roles/run.invoker",
    ("Invoke", "cloud_function"): "roles/cloudfunctions.invoker",
    ("Emit", "pubsub_topic"): "roles/pubsub.publisher",
    ("Enqueue", "cloud_task_queue"): "roles/cloudtasks.enqueuer",
}
```

### Pattern 4: Tenant Context for MCP Server
**What:** MCP server needs a way to identify which tenant it's operating as, since there's no HTTP request to extract auth from
**When to use:** All MCP tools
**Example:**
```python
# The MCP server runs with AUTH_DISABLED=true and pre-configured tenant context
import os

def get_tenant_id() -> str:
    """Get tenant ID for MCP operations. Uses DEV_TENANT_ID env var."""
    return os.environ.get("DEV_TENANT_ID", "dev-local")

def get_owner_uid() -> str:
    """Get the project owner UID. For the target project, this is tyler's UID."""
    return os.environ.get("DEV_TENANT_ID", "yBi9vPkZ5HXNw7zyfSr7zltjojC2")
```

### Anti-Patterns to Avoid
- **HTTP self-calls from MCP server:** Do not have the MCP server make HTTP requests to the FastAPI server. Call the store/handler functions directly. This avoids auth complexity, network overhead, and error format translation.
- **Reimplementing validation:** The existing `validate_blueprint` and `validate_blueprint_by_slug` already handle all cross-node validation. MCP tools should run these after mutations, not build their own validation.
- **Monolithic tool definitions:** Each tool should be a focused operation. Agents work best with many small tools rather than few large tools with complex parameters.
- **Printing to stdout in stdio MCP server:** This corrupts JSON-RPC messages. Use `logging` with stderr handler or the MCP SDK's built-in logging.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| MCP protocol | Custom JSON-RPC server | `mcp` SDK with `FastMCP` | Protocol compliance, tool schema generation, transport handling, input validation |
| IAM role resolution | Custom role lookup per service | Static mapping table in `iam_mappings.py` | The ActionType x NodeType matrix is finite and well-known; a table is correct and testable |
| Blueprint validation | Custom validation in MCP tools | Existing `validate_blueprint()` | Already handles 15+ validation rules including cross-node refs, DAG cycles, required fields |
| Terraform generation | Custom TF output | Existing `generate_terraform()` | Already has 18 Jinja2 templates, topological sort, reference resolution |
| Real-time subscriptions | Custom WebSocket server | Firebase Firestore `onSnapshot` | Already proven in existing WorkspaceScreen; data model already in Firestore |
| Node slug generation | Custom ID scheme | Existing `_generate_slug()` in nodes handler | Type-prefixed slugs already implemented |

**Key insight:** This phase is primarily a wiring exercise. 90% of the business logic exists. The MCP server is a thin adapter layer, auto-provisioning is a small orchestration layer on top of existing CRUD, and the insight board consumes existing Firestore data.

## Common Pitfalls

### Pitfall 1: MCP Server stdout corruption (stdio transport)
**What goes wrong:** Any `print()` statement or stdout logging in the MCP server process corrupts JSON-RPC messages, causing silent tool failures.
**Why it happens:** stdio transport uses stdout for JSON-RPC protocol messages. Any non-protocol output breaks the message framing.
**How to avoid:** Configure all logging to stderr. Never use `print()`. Use `logging.getLogger()` with a stderr handler. The MCP SDK configures this by default.
**Warning signs:** Tools work in testing but fail when connected to Claude Desktop/CLI.

### Pitfall 2: Auto-provisioning creates duplicate resources
**What goes wrong:** Adding a second compute node creates a second VPC, subnet, and connector when one already exists.
**Why it happens:** The auto-provisioning logic doesn't check for existing networking resources.
**How to avoid:** Before creating networking nodes, check if VPC/subnet/connector already exist in the blueprint. Reuse existing ones. Only create if none exist.
**Warning signs:** Multiple VPC nodes in the blueprint after adding multiple compute nodes.

### Pitfall 3: IAM role accumulation without cleanup
**What goes wrong:** Deleting a dependency edge doesn't remove the corresponding IAM role from the service account.
**Why it happens:** IAM roles are added when edges are created but never cleaned up.
**How to avoid:** When a node's `depends_on` or `internalGraph` changes, recompute the full IAM role set from the current dependency graph and replace (not append) the service account's roles.
**Warning signs:** Service accounts accumulate roles beyond what's needed.

### Pitfall 4: Circular dependency between auto-provisioned nodes
**What goes wrong:** Auto-provisioning adds nodes with `depends_on` references that create cycles.
**Why it happens:** Incorrect dependency wiring (e.g., compute depends on SA, SA depends on compute).
**How to avoid:** Follow strict dependency ordering: VPC -> Subnet -> VPC Connector -> Compute Node; Service Account is independent (compute references SA, not vice versa).
**Warning signs:** DAG validation errors after auto-provisioning.

### Pitfall 5: MCP tool return format
**What goes wrong:** Agent gets raw Python dicts/objects instead of readable text. Or error tracebacks leak into tool output.
**Why it happens:** MCP tools must return strings (or MCP content types). Returning dicts doesn't work.
**How to avoid:** Every tool should format its output as a human-readable string. Catch exceptions and return error descriptions, not stack traces.
**Warning signs:** Agent asks "what does this mean?" about tool output, or cannot parse results.

### Pitfall 6: Networking auto-provision triggers on non-private resources
**What goes wrong:** VPC/subnet/connector created when compute node depends on Firestore or Pub/Sub (which don't need VPC access).
**Why it happens:** Overly broad "needs private access" check.
**How to avoid:** Only Cloud SQL and Bigtable require VPC access for private IP connections. Firestore, BigQuery, Pub/Sub, GCS all use public Google APIs and don't need VPC connectors.
**Warning signs:** Unnecessary networking resources in blueprints.

## Code Examples

### MCP Server Entry Point
```python
# packages/mcp/server.py
# Source: MCP Python SDK docs (https://modelcontextprotocol.io/docs/develop/build-server)
import logging
import sys

from mcp.server.fastmcp import FastMCP

# Configure logging to stderr (critical for stdio transport)
logging.basicConfig(stream=sys.stderr, level=logging.INFO)

mcp = FastMCP(
    "gcp-orchestration",
    description="GCP infrastructure orchestration platform",
)

# Import tool modules to register them
from packages.mcp.tools import projects, nodes, secrets, code_files, builds, deploy, blueprint  # noqa: E402, F401

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

### Claude Desktop Configuration
```json
{
  "mcpServers": {
    "gcp-orchestration": {
      "command": "python",
      "args": ["-m", "packages.mcp.server"],
      "cwd": "/path/to/gcp-orchestration",
      "env": {
        "AUTH_DISABLED": "true",
        "ENVIRONMENT": "dev",
        "DEV_TENANT_ID": "yBi9vPkZ5HXNw7zyfSr7zltjojC2",
        "DEV_USER_EMAIL": "tyler@pl4m.com",
        "DEV_USER_DISPLAY_NAME": "Tyler",
        "GCP_PROJECT_ID": "pl4m-host-dev",
        "FIRESTORE_DATABASE": "(default)"
      }
    }
  }
```

### Auto-Provision Networking Stack
```python
# packages/core/auto_provision.py
def _create_networking_stack(
    tenant_id: str, project_ref_id: str, env_name: str,
    existing_nodes: list[dict],
) -> list[dict]:
    """Create VPC + Subnet + VPC Connector if not already present."""
    created = []
    node_types = {n.get("type") for n in existing_nodes}

    # Check if networking already exists
    if "vpc" not in node_types:
        vpc = _create_node(tenant_id, project_ref_id, env_name, {
            "name": "default-vpc",
            "type": "vpc",
            "config": {"auto_create_subnetworks": False},
        })
        created.append(vpc)

    if "subnet" not in node_types:
        subnet = _create_node(tenant_id, project_ref_id, env_name, {
            "name": "default-subnet",
            "type": "subnet",
            "depends_on": ["default-vpc"],
            "config": {
                "ip_cidr_range": "10.8.0.0/28",
                "region": "us-central1",
                "network": "node:default-vpc.self_link",
            },
        })
        created.append(subnet)

    if "vpc_connector" not in node_types:
        connector = _create_node(tenant_id, project_ref_id, env_name, {
            "name": "default-connector",
            "type": "vpc_connector",
            "depends_on": ["default-subnet"],
            "config": {
                "region": "us-central1",
                "network": "node:default-vpc.self_link",
                "ip_cidr_range": "10.8.0.0/28",
            },
        })
        created.append(connector)

    return created
```

### Insight Board Firestore Subscription
```typescript
// apps/web/src/screens/InsightBoard.tsx
// Source: Existing WorkspaceScreen.tsx pattern
import { useEffect, useState } from 'react'
import { doc, collection, onSnapshot } from 'firebase/firestore'
import { db } from '@/lib/firebase'

function useProjectDoc(tenantId: string, projectRefId: string) {
  const [project, setProject] = useState<any>(null)
  useEffect(() => {
    const ref = doc(db, 'tenants', tenantId, 'projects', projectRefId)
    return onSnapshot(ref, (snap) => {
      if (snap.exists()) setProject({ ...snap.data(), id: snap.id })
    })
  }, [tenantId, projectRefId])
  return project
}

function useValidation(tenantId: string, projectRefId: string, env: string) {
  const [validation, setValidation] = useState<any>(null)
  useEffect(() => {
    const ref = doc(
      db, 'tenants', tenantId, 'projects', projectRefId,
      'blueprints', env, 'validation', 'current'
    )
    return onSnapshot(ref, (snap) => {
      if (snap.exists()) setValidation(snap.data())
    })
  }, [tenantId, projectRefId, env])
  return validation
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom JSON-RPC MCP impl | `mcp` SDK with `FastMCP` | MCP SDK 1.0 (late 2024) | Auto schema generation, transport handling, input validation |
| VPC Connector for Cloud Run | Direct VPC Egress (GA) | Cloud Run v2 (2024) | Potentially eliminates need for VPC Connector; but VPC Connector still works and is simpler for auto-provisioning |
| Firebase Realtime DB | Firestore | Already using Firestore | Real-time listeners via `onSnapshot` work well for dashboard |

**Deprecated/outdated:**
- MCP SSE transport: Being phased out in favor of "Streamable HTTP" transport. For this project, stdio transport is the right choice since the agent (Claude) runs locally.

## Open Questions

1. **VPC Connector vs Direct VPC Egress**
   - What we know: Cloud Run v2 supports Direct VPC Egress (GA) which eliminates the need for a VPC Connector. The existing `CloudRunConfig` has both `vpc_access` (connector-based) and `vpc_access_direct` fields.
   - What's unclear: Whether Direct VPC Egress is simpler to auto-provision than the VPC Connector approach.
   - Recommendation: Use VPC Connector for auto-provisioning (AGT-09). It's the simpler, well-tested path. The `vpc_access_direct` option can be exposed as an advanced configuration later.

2. **Insight Board as separate app or route in existing app**
   - What we know: The existing `apps/web/` has 3 screens. The insight board is read-only, distinct from the existing workspace.
   - What's unclear: Whether to add it as a new route in `apps/web/` or create a separate app.
   - Recommendation: Add as a new route in `apps/web/` (e.g., `/insight/:projectRefId`). Reuses existing Firebase setup, Zustand patterns, and Tailwind config. No need for a separate build pipeline.

3. **MCP Server process lifecycle**
   - What we know: stdio transport means the MCP server is a child process of the agent client. It needs access to the same env vars as the FastAPI server.
   - What's unclear: Whether the MCP server should import FastAPI app or just the underlying store/core modules.
   - Recommendation: Import store/core modules directly. Do not import the FastAPI app. The MCP server has no need for HTTP routing, middleware, or CORS.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (already configured) |
| Config file | `packages/pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `cd packages && python -m pytest tests/ -x -q` |
| Full suite command | `cd packages && python -m pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AGT-01 | Project lifecycle MCP tools | unit | `cd packages && python -m pytest tests/test_mcp_projects.py -x` | Wave 0 |
| AGT-02 | Node CRUD MCP tools | unit | `cd packages && python -m pytest tests/test_mcp_nodes.py -x` | Wave 0 |
| AGT-03 | Secret management MCP tools | integration | `cd packages && python -m pytest tests/test_mcp_secrets.py -x` | Wave 0 |
| AGT-04 | Code file MCP tools | integration | `cd packages && python -m pytest tests/test_mcp_code_files.py -x` | Wave 0 |
| AGT-05 | Build trigger MCP tools | integration | `cd packages && python -m pytest tests/test_mcp_builds.py -x` | Wave 0 |
| AGT-06 | Deploy MCP tools | integration | `cd packages && python -m pytest tests/test_mcp_deploy.py -x` | Wave 0 |
| AGT-07 | Blueprint + TF MCP tools | unit | `cd packages && python -m pytest tests/test_mcp_blueprint.py -x` | Wave 0 |
| AGT-08 | Auto-create service account | unit | `cd packages && python -m pytest tests/test_auto_provision.py::test_sa_auto_create -x` | Wave 0 |
| AGT-09 | Auto-create networking | unit | `cd packages && python -m pytest tests/test_auto_provision.py::test_networking_auto_create -x` | Wave 0 |
| AGT-10 | IAM role inference | unit | `cd packages && python -m pytest tests/test_iam_mappings.py -x` | Wave 0 |
| AGT-11 | Insight board UI | manual-only | Manual: load page, verify Firestore panels update | N/A |
| AGT-12 | Debug endpoints | unit | `cd packages && python -m pytest tests/test_debug_endpoints.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd packages && python -m pytest tests/ -x -q`
- **Per wave merge:** `cd packages && python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `packages/tests/test_mcp_projects.py` -- covers AGT-01
- [ ] `packages/tests/test_mcp_nodes.py` -- covers AGT-02
- [ ] `packages/tests/test_auto_provision.py` -- covers AGT-08, AGT-09
- [ ] `packages/tests/test_iam_mappings.py` -- covers AGT-10
- [ ] `packages/tests/test_debug_endpoints.py` -- covers AGT-12
- [ ] MCP SDK install: `pip install "mcp>=1.26.0"` -- add to pyproject.toml dependencies

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | MCP server, all backend | TBD (check at plan time) | 3.12+ | -- |
| Node.js 20 | Frontend insight board | TBD (check at plan time) | 20+ | -- |
| Firestore | Data storage, real-time subs | Yes (existing, configured) | -- | -- |
| `mcp` PyPI package | MCP server | Yes (1.26.0 on PyPI) | 1.26.0 | -- |
| Docker | Container builds | TBD | -- | Skip build testing |
| gcloud CLI | GCP operations | TBD | -- | Skip deploy testing |

**Missing dependencies with no fallback:**
- None identified -- all core dependencies are existing or available on PyPI

**Missing dependencies with fallback:**
- Docker/gcloud: Can develop and test MCP tools, auto-provisioning, and insight board without them. Only needed for end-to-end deploy testing.

## Sources

### Primary (HIGH confidence)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) - FastMCP API, transport options, tool definition patterns
- [MCP Official Docs](https://modelcontextprotocol.io/docs/develop/build-server) - Server build guide, stdio transport, logging requirements
- [PyPI mcp package](https://pypi.org/project/mcp/) - Version 1.26.0 confirmed current
- Project codebase - All 16 API handlers, 22 node types, Pydantic models, Terraform templates examined directly

### Secondary (MEDIUM confidence)
- [GCP IAM Roles Docs](https://docs.google.com/sql/docs/mysql/iam-roles) - Cloud SQL, Cloud Run, Firestore, BigQuery IAM role mappings
- [Cloud Run IAM Roles](https://docs.google.com/run/docs/reference/iam/roles) - Run invoker role

### Tertiary (LOW confidence)
- Cloud Run Direct VPC Egress GA status -- needs verification against current GCP docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - MCP SDK is well-documented, existing codebase is thoroughly examined
- Architecture: HIGH - Pattern is straightforward wrapper over existing code with one new orchestration layer
- Auto-provisioning: MEDIUM - IAM role mappings need GCP docs verification; networking auto-provision logic is new
- Pitfalls: HIGH - Based on direct MCP SDK docs warnings and common dependency graph patterns

**Research date:** 2026-03-26
**Valid until:** 2026-04-26 (MCP SDK is fast-moving; re-check version before implementation)
