# Phase 1: MCP Server + Agent Workflow + Dev Insight Board - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver three interconnected capabilities:
1. **MCP Server** — A stdio-based MCP tool server that wraps existing backend functionality as domain-grouped agent-callable tools, using direct Python imports to call store/service functions (not HTTP self-calls)
2. **Auto-provisioning intelligence** — Automatic creation of supporting resources (service accounts, VPC/subnet/connector) when compute nodes are added, with IAM role inference from dependency graph edges
3. **Dev insight board** — A read-only frontend dashboard with real-time Firestore subscriptions showing agent activity and infrastructure state side by side

All operations target the existing provisioned project ("My Test Project", ref: gtPIQyFrVTkEDZEm5gHc) under tyler@pl4m.com with AUTH_DISABLED=true.

</domain>

<decisions>
## Implementation Decisions

### MCP Tool Design
- **D-01:** Tools grouped by domain (~15-20 tools), not 1:1 with endpoints. Groups: project, nodes, blueprint, secrets, code, build, deploy, status. Maps to AGT-01 through AGT-07.
- **D-02:** MCP server uses direct Python imports to call store/service/core functions (same process). Research identified HTTP self-calls as an anti-pattern — adds latency, deployment complexity, and circular dependency. The MCP server IS the backend, not a client of it.
- **D-03:** Errors surfaced using MCP protocol's built-in `isError` flag on tool results, plus structured JSON content with error_type, message, and details.
- **D-04:** stdio transport first (local dev). Agent runs MCP server as a subprocess. SSE/remote transport deferred.
- **D-05:** Every tool call includes project_ref_id and env as parameters. Fully stateless — no server-side session.

### Auto-Provisioning Behavior
- **D-06:** Auto-provisioning is eager — triggers on node add. When a compute node is added, its service account is immediately auto-created and wired as a dependency.
- **D-07:** Auto-provisioned resources appear as regular BaseNode entries with an `auto_provisioned: true` tag. Visually distinct in the insight board.
- **D-08:** IAM role mappings are registry-integrated — extend ComponentDefinition in registry.py with an `iam_roles` field mapping ActionType to GCP IAM role strings.
- **D-09:** The add-node tool response includes a list of auto-created nodes (e.g., "Also created: sa-my-service"). Agent knows immediately what was provisioned.
- **D-10:** Auto-provisioned nodes can be deleted/modified by the agent, but the tool response warns about potential breakage.
- **D-11:** Networking auto-provisioning only kicks in when a compute node has a dependency on a private data resource (Cloud SQL, Bigtable). Public resources (Firestore, public APIs) don't trigger VPC/subnet/connector creation.
- **D-12:** When networking is needed: shared VPC + subnet per project, per-service VPC connector. Matches GCP best practices for Cloud Run.
- **D-13:** Auto-provisioning is always-on, no configuration toggle. This is core platform intelligence.

### Dev Insight Board
- **D-14:** Split layout — activity feed AND resource state side by side. Both are primary views.
- **D-15:** New standalone `/insight` route with its own layout. Reuses UI primitives (button, tabs, etc.) but new layout components. Existing WorkspaceScreen untouched.
- **D-16:** Resource list shows: icon by type, name, validation status (checkmark/warning), deploy status (deployed/pending/modified), auto-provisioned tag. Clickable for details.
- **D-17:** Deploy logs in a collapsible bottom panel (like browser dev tools). Shows streaming logs when a deploy is active. Collapsed by default. Uses existing SSE endpoint.
- **D-18:** All data via Firestore real-time subscriptions (onSnapshot). No polling.

### Agent Workflow Guardrails
- **D-19:** Server-side concurrency guards with clear structured errors. The API already has these (409 for in-progress ops). MCP tools surface them as actionable errors: "Deploy blocked: build b-123 in progress."
- **D-20:** A `get_project_status` tool returns current state AND available actions with hints. E.g., "Blueprint has 2 validation errors. Fix errors before deploying."
- **D-21:** Validation runs on every node mutation (add/update/delete) and deploy is blocked on validation errors. Matches existing backend behavior.

### Claude's Discretion
- MCP tool naming conventions (snake_case, verb_noun, etc.)
- Internal HTTP client implementation details (connection pooling, timeouts, retries)
- Dev insight board component architecture (how to structure React components)
- Activity feed data model and polling/subscription strategy
- Debug endpoint response formats (AGT-12)
- Specific Tailwind styling and layout breakpoints for the insight board

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Backend API
- `packages/api/main.py` — FastAPI app factory, all 16 router mounts, CORS config
- `packages/api/handlers/` — All 16 handler modules (the endpoints MCP tools will wrap)
- `packages/api/middleware.py` — Body size middleware

### Core Domain
- `packages/core/schemas/base.py` — Envelope, BaseNode, GlobalConfig, IamBlock models
- `packages/core/schemas/enums.py` — NodeType, ActionType, Protocol, OutputType enums
- `packages/core/registry.py` — REGISTRY dict, ComponentDefinition dataclass (extend for IAM roles)
- `packages/core/validation.py` — Validation engine, ValidationIssue dataclass
- `packages/core/dag.py` — BlueprintDAG for dependency graph operations

### Platform Services
- `packages/platform/auth/firebase.py` — CurrentUser, get_current_user(), dev bypass
- `packages/platform/auth/authz.py` — ProjectAccess, require_project_access()
- `packages/platform/store/client.py` — Firestore client singleton, path helpers
- `packages/platform/deploy_orchestrator.py` — Deploy pipeline (_run_deploy)
- `packages/platform/deploy_service.py` — Deploy snapshots, modified flag computation
- `packages/platform/streaming/deploy_logs.py` — SSE streaming for deploy logs

### Frontend
- `apps/web/src/lib/firebase.ts` — Firebase SDK init (reuse in insight board)
- `apps/web/src/lib/api-client.ts` — API client pattern
- `apps/web/src/stores/` — Zustand store patterns
- `apps/web/src/components/ui/` — Reusable UI primitives

### Infrastructure
- `packages/core/terraform/generator.py` — Terraform generation (for TF preview tool)
- `packages/core/terraform/templates/` — Jinja2 templates (understand what TF output looks like)

### Planning Artifacts
- `.planning/phases/01-mcp-server-agent-workflow-dev-insight-board/01-RESEARCH.md` — Technical research on MCP implementation, auto-provisioning, and dev insight board
- `.planning/phases/01-mcp-server-agent-workflow-dev-insight-board/01-UI-SPEC.md` — UI design contract for the dev insight board

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **16 API handler modules** (`packages/api/handlers/`): Complete CRUD for all operations. MCP tools wrap these via HTTP.
- **Pydantic models** (`packages/core/schemas/`): Envelope, BaseNode, 22 config models. Define the data contracts.
- **Component registry** (`packages/core/registry.py`): REGISTRY dict maps NodeType → ComponentDefinition. Extend for IAM roles.
- **BlueprintDAG** (`packages/core/dag.py`): Topological sort, cycle detection. Use for auto-provisioning dependency analysis.
- **Validation engine** (`packages/core/validation.py`): ValidationIssue dataclass. Already runs on every node mutation.
- **SSE deploy logs** (`packages/platform/streaming/deploy_logs.py`): Already implemented. Insight board consumes this.
- **UI primitives** (`apps/web/src/components/ui/`): button, dialog, input, select, tabs, table — reuse in insight board.
- **Zustand stores** (`apps/web/src/stores/`): auth-store, blueprint-store, project-store patterns to follow.
- **Firebase integration** (`apps/web/src/lib/firebase.ts`): Already initialized with Firestore.

### Established Patterns
- **FastAPI Depends() injection**: Auth and project access are injected via dependencies. MCP server bypasses this by using AUTH_DISABLED=true.
- **Firestore path structure**: `tenants/{uid}/projects/{ref_id}/blueprints/{env}/nodes/{slug}` — insight board subscribes to these paths.
- **Activity log**: Already exists in Firestore at `tenants/{uid}/projects/{ref_id}/activity/{doc_id}` — insight board subscribes to this.
- **Node slug generation**: Deterministic slugs from node type + name. MCP tools use existing slug logic.

### Integration Points
- **MCP server → FastAPI API**: HTTP client (httpx) calls to localhost:8080/api/* endpoints
- **Insight board → Firestore**: onSnapshot subscriptions to project doc, blueprint nodes, validation, activity
- **Insight board → SSE endpoint**: EventSource connection for deploy log streaming
- **Auto-provisioning → Node CRUD**: Extends the node add handler to auto-create supporting nodes
- **IAM inference → Terraform generator**: New IAM bindings flow through existing TF generation pipeline

</code_context>

<specifics>
## Specific Ideas

- Networking auto-provisioning should respect that many GCP resources (Firestore, public APIs) don't need VPC access. Only private resources (Cloud SQL, Bigtable with private endpoints) trigger networking creation.
- The insight board serves as a "watch the agent work" experience — both activity feed and resource state are equally important.
- The MCP server is a thin HTTP client, not a reimplementation of backend logic.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-mcp-server-agent-workflow-dev-insight-board*
*Context gathered: 2026-03-26*
