# Requirements: GCP Orchestration Platform — Agent Engine

**Defined:** 2026-03-27
**Core Value:** An AI agent can provision, configure, and deploy GCP infrastructure through MCP tools without human intervention, while a developer observes in real-time.

## v1 Requirements

### MCP Server

- [ ] **AGT-01**: MCP server with tools for project lifecycle (list projects, get project state, select environment)
- [x] **AGT-02**: MCP tools for node CRUD (add node by type, configure node, delete node, list nodes with validation state)
- [ ] **AGT-03**: MCP tools for secret management (create/update/delete secrets, list secrets with masked values)
- [ ] **AGT-04**: MCP tools for code file management (read/write/delete files on compute nodes, list files)
- [ ] **AGT-05**: MCP tools for container builds (trigger build, check build status, get build logs)
- [ ] **AGT-06**: MCP tools for deploy operations (trigger deploy, check deploy status, get plan/apply output, stream logs)
- [ ] **AGT-07**: MCP tools for blueprint-level operations (get full blueprint, validate blueprint, generate Terraform preview)

### Auto-Provisioning Intelligence

- [x] **AGT-08**: When a compute node is added, auto-create a service_account node and wire it as a dependency
- [x] **AGT-09**: When a compute node depends on a private data resource (Cloud SQL, etc.), auto-create VPC/subnet/connector nodes and wire networking
- [x] **AGT-10**: IAM role bindings auto-inferred from dependency graph edges (ActionType + target NodeType → GCP IAM role) and generated as Terraform

### Dev Insight Board (Frontend)

- [x] **AGT-11**: Read-only dashboard with real-time Firestore subscriptions showing: project state, resource list with types, validation output per node, Terraform compilation output, deploy status/logs, activity feed (scaffold in 01-03, panels in 01-06)
- [x] **AGT-12**: Debug endpoints exposed: raw project state, full validation output, compiled Terraform files, deploy history, node deploy status with modified flags

## Out of Scope

| Feature | Reason |
|---------|--------|
| User-facing UX for resource configuration | Agent is the primary user; dev board is observation only |
| Blueprint promotion UI | Agent handles env management via MCP tools |
| Drag-and-drop node editor | Replaced by MCP tool-based node management |
| Collaborator management UI | Not needed for single-agent workflow |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AGT-01 | Phase 1 | Pending |
| AGT-02 | Phase 1 | Complete |
| AGT-03 | Phase 1 | Pending |
| AGT-04 | Phase 1 | Pending |
| AGT-05 | Phase 1 | Pending |
| AGT-06 | Phase 1 | Pending |
| AGT-07 | Phase 1 | Pending |
| AGT-08 | Phase 1 | Complete |
| AGT-09 | Phase 1 | Complete |
| AGT-10 | Phase 1 | Complete |
| AGT-11 | Phase 1 | Scaffold complete (01-03), panels pending (01-06) |
| AGT-12 | Phase 1 | Complete (01-03) |

**Coverage:**
- v1 requirements: 12 total
- Mapped to phases: 12
- Unmapped: 0

---
*Requirements defined: 2026-03-27*
