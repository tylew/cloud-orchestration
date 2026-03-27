# Phase 1: MCP Server + Agent Workflow + Dev Insight Board - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-26
**Phase:** 01-mcp-server-agent-workflow-dev-insight-board
**Areas discussed:** MCP tool design, Auto-provisioning behavior, Dev insight board layout, Agent workflow guardrails

---

## MCP Tool Design

### Tool Grouping

| Option | Description | Selected |
|--------|-------------|----------|
| Domain-grouped tools | Group by domain (~15-20 tools), matching AGT-01 through AGT-07 | ✓ |
| 1:1 endpoint mapping | One MCP tool per API endpoint (~57 tools) | |
| Workflow-oriented tools | Fewer coarser tools organized by workflow step (~8-10 tools) | |

**User's choice:** Domain-grouped tools
**Notes:** None

### Backend Connection

| Option | Description | Selected |
|--------|-------------|----------|
| Direct Python import | MCP server imports handler functions directly | |
| HTTP client to running API | Separate process calling FastAPI over HTTP | ✓ |
| Hybrid approach | Direct imports for reads, HTTP for mutations | |

**User's choice:** HTTP client to running API
**Notes:** None

### Error Surfacing

| Option | Description | Selected |
|--------|-------------|----------|
| Structured error objects | Return { success: false, error_type, message, details } | |
| Plain text error messages | Human-readable error strings | |
| MCP isError flag + structured content | Use MCP protocol's built-in isError + structured JSON | ✓ |

**User's choice:** MCP isError flag + structured content
**Notes:** None

### Transport

| Option | Description | Selected |
|--------|-------------|----------|
| stdio (local) first | Start with stdio transport for local dev | ✓ |
| SSE (remote) first | Start with SSE transport for remote access | |
| Both from day one | Support both transports | |

**User's choice:** stdio (local) first
**Notes:** None

---

## Auto-Provisioning Behavior

### Timing

| Option | Description | Selected |
|--------|-------------|----------|
| On node add (eager) | Immediately create supporting resources when compute node added | ✓ |
| On deploy (lazy) | Create at deploy time during Terraform generation | |
| On validate (middle ground) | Auto-provision when blueprint validation runs | |

**User's choice:** On node add (eager)
**Notes:** None

### Visibility

| Option | Description | Selected |
|--------|-------------|----------|
| Full nodes | Regular BaseNode entries in blueprint | |
| Hidden/implicit | Generated during TF output, not visible as nodes | |
| Tagged nodes | Regular nodes with auto_provisioned: true flag | ✓ |

**User's choice:** Tagged nodes
**Notes:** None

### IAM Mapping

| Option | Description | Selected |
|--------|-------------|----------|
| Hardcoded mapping table | Python dict mapping (ActionType, NodeType) → IAM role | |
| Config-driven mapping | YAML/JSON config file for role mappings | |
| Registry-integrated | Extend ComponentDefinition with iam_roles field | ✓ |

**User's choice:** Registry-integrated
**Notes:** None

### Feedback

| Option | Description | Selected |
|--------|-------------|----------|
| Return created nodes in response | Add-node response includes list of auto-created nodes | ✓ |
| Silent creation | No notification, agent discovers by listing | |
| Separate notification tool | A get_pending_changes tool | |

**User's choice:** Return created nodes in response
**Notes:** None

### Override

| Option | Description | Selected |
|--------|-------------|----------|
| Allow with warning | Agent can delete/modify but gets breakage warnings | ✓ |
| Block deletion | Cannot delete while parent compute node exists | |
| Allow freely | No special handling | |

**User's choice:** Allow with warning
**Notes:** None

### Networking

| Option | Description | Selected |
|--------|-------------|----------|
| Shared VPC + subnet, per-service connector | One VPC/subnet per project, per-service connectors | |
| Everything shared | One of each shared by all compute nodes | |
| Everything per-service | Each compute node gets its own stack | |

**User's choice:** Other — networking only when private data access is needed. Public resources don't need VPC.
**Notes:** User clarified that compute nodes talking to public resources (Firestore, public APIs) don't need networking. Only private data resources (Cloud SQL, Bigtable) trigger VPC/subnet/connector creation. This matches actual GCP behavior.

### Configurability

| Option | Description | Selected |
|--------|-------------|----------|
| Always-on, no config | Auto-provisioning always runs | ✓ |
| Opt-out per node | Default on, disable per node | |
| Global toggle | Project-level setting | |

**User's choice:** Always-on, no config
**Notes:** None

---

## Dev Insight Board Layout

### Primary Use Case

| Option | Description | Selected |
|--------|-------------|----------|
| Watch agent work live | Real-time activity feed is primary | |
| Debug infrastructure state | Resource details/dashboard is primary | |
| Both equally | Split layout with both views | ✓ |

**User's choice:** Both equally
**Notes:** None

### Frontend Reuse

| Option | Description | Selected |
|--------|-------------|----------|
| New standalone page | New /insight route with own layout | ✓ |
| Modify WorkspaceScreen | Strip down existing screen | |
| Separate app | Independent React app | |

**User's choice:** New standalone page
**Notes:** None

### Resource Detail Level

| Option | Description | Selected |
|--------|-------------|----------|
| Type + name + status indicators | Icon, name, validation/deploy status, auto-provisioned tag | ✓ |
| Minimal list | Just names grouped by category | |
| Rich cards | Cards with config summary and dependencies inline | |

**User's choice:** Type + name + status indicators
**Notes:** None

### Deploy Logs

| Option | Description | Selected |
|--------|-------------|----------|
| Collapsible log panel | Bottom panel like browser dev tools | ✓ |
| Dedicated log page | Separate /insight/logs route | |
| Inline in activity feed | Log lines in activity feed | |

**User's choice:** Collapsible log panel
**Notes:** None

---

## Agent Workflow Guardrails

### Concurrency

| Option | Description | Selected |
|--------|-------------|----------|
| Server-side guards with clear errors | Surface existing API guards as structured MCP errors | ✓ |
| Client-side queue | MCP server queues and serializes requests | |
| Let it fail | No special handling | |

**User's choice:** Server-side guards with clear errors
**Notes:** None

### Discovery

| Option | Description | Selected |
|--------|-------------|----------|
| Status tool with actionable hints | get_project_status returns state + available actions | ✓ |
| Separate capabilities tool | list_available_actions tool | |
| No discovery tool | Agent uses tool descriptions only | |

**User's choice:** Status tool with actionable hints
**Notes:** None

### Validation Enforcement

| Option | Description | Selected |
|--------|-------------|----------|
| Validate on every mutation, block deploy on errors | Auto-validate, block deploy. Matches existing backend. | ✓ |
| Validate on demand only | Agent explicitly calls validate | |
| Warn but don't block | Validation runs but deploy proceeds | |

**User's choice:** Validate on every mutation, block deploy on errors
**Notes:** None

### Session State

| Option | Description | Selected |
|--------|-------------|----------|
| Stateless with context in tool params | Every call includes project_ref_id and env | ✓ |
| Lightweight session | Remember current project/env after selection | |
| Full session with undo | Track all operations, support undo | |

**User's choice:** Stateless with context in tool params
**Notes:** None

---

## Claude's Discretion

- MCP tool naming conventions
- Internal HTTP client implementation details
- Dev insight board component architecture
- Activity feed data model
- Debug endpoint response formats
- Tailwind styling and layout breakpoints

## Deferred Ideas

None — discussion stayed within phase scope
