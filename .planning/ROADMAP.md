# Roadmap: GCP Orchestration Platform — Agent Engine

## Overview

Ship the platform as an agent-first infrastructure orchestration engine. The MCP server is the primary interface — an AI agent can provision projects, configure resources, manage secrets, build containers, wire networking/IAM, and deploy across environments through tool calls. The frontend is a read-only dev insight board that subscribes to Firestore for real-time visibility into what the agent is doing. No user-facing UX — just developer observability.

**Target user:** Tyler (tyler@pl4m.com, UID: yBi9vPkZ5HXNw7zyfSr7zltjojC2)
**Target project:** "My Test Project" (ref: gtPIQyFrVTkEDZEm5gHc, internal: my-test-project-c79ccd56, GCP: dev-my-test-project-c79ccd56, provision: ready)

## Phases

- [ ] **Phase 1: MCP Server + Agent Workflow + Dev Insight Board** — Build MCP server exposing platform operations as tools, implement auto-provisioning intelligence (SA, networking, IAM inference), strip frontend to read-only Firestore-subscribed debug dashboard

## Phase Details

### Phase 1: MCP Server + Agent Workflow + Dev Insight Board
**Goal**: An agent can execute the full infrastructure lifecycle through MCP tools — create resources, configure them, wire dependencies, set secrets, build containers, deploy — while a developer watches in real-time via a stripped-down Firestore-subscribed dashboard
**Depends on**: Nothing (uses existing backend API)
**Requirements**: AGT-01 through AGT-12
**Success Criteria** (what must be TRUE):
  1. MCP server exposes tools for: project operations, node CRUD, blueprint management, secret management, code file management, container builds, deploy, and status queries
  2. Agent can add a compute node and the platform auto-creates its service account, auto-wires VPC connector if private DB access is needed
  3. IAM role bindings are auto-inferred from dependency graph edges and generated as Terraform
  4. Networking resources (VPC, subnet, connector) are auto-created when compute nodes need private access to data resources
  5. Agent can execute a full workflow: add nodes → configure → set secrets → push code → build → deploy → verify status
  6. Frontend is a read-only dev insight board showing: project state, resource list, validation output, Terraform preview, deploy logs, and activity feed — all via Firestore real-time subscriptions
  7. All operations work against the existing provisioned project (gtPIQyFrVTkEDZEm5gHc) under tyler@pl4m.com
  8. Edge cases handled: validation errors surface to agent, deploy failures are queryable, concurrent operation guards work
**Plans:** 6 plans

Plans:
- [x] 01-01-PLAN.md — MCP server scaffold + project/blueprint tools (AGT-01, AGT-07)
- [x] 01-02-PLAN.md — IAM mappings + auto-provisioning intelligence (AGT-08, AGT-09, AGT-10)
- [x] 01-03-PLAN.md — Debug endpoints + insight board scaffold (AGT-12, AGT-11 scaffold)
- [x] 01-04-PLAN.md — MCP node CRUD tools with auto-provisioning (AGT-02)
- [x] 01-05-PLAN.md — MCP operational tools: secrets, code, builds, deploy (AGT-03-06)
- [x] 01-06-PLAN.md — Dev Insight Board panels (AGT-11 complete)

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. MCP Server + Agent Workflow + Dev Insight Board | 1/6 | In progress | - |

### Phase 2: Implement cloud_dns node type

**Goal:** Add cloud_dns as the 23rd node type — enum, Pydantic config model, registry entry, Terraform template, validation rules — following the exact registration pattern of existing node types
**Requirements**: DNS-01 through DNS-06
**Depends on:** Phase 1
**Plans:** 1/1 plans complete

Plans:
- [x] 02-01-PLAN.md — Cloud DNS node type: schema, registration, Terraform template, and tests (DNS-01 through DNS-06)

### Phase 3: Terraform output surfacing and post-deploy user action guidance

**Goal:** Surface structured Terraform output values (URLs, IPs, connection strings) after deploys complete, stored in Firestore and accessible via a dedicated MCP tool. Only external-facing outputs are surfaced. Post-deploy guidance deferred.
**Requirements**: OUT-01 through OUT-06
**Depends on:** Phase 2
**Plans:** 2 plans

Plans:
- [ ] 03-01-PLAN.md — TF output block generation in generator.py with external-facing classification (OUT-01, OUT-02)
- [ ] 03-02-PLAN.md — Cloud Build step, deploy orchestrator integration, Firestore storage, and MCP tool (OUT-03, OUT-04, OUT-05, OUT-06)
