# GCP Orchestration Platform

## What This Is

An agent-first infrastructure orchestration engine for GCP. An AI agent provisions projects, configures resources (Cloud Run, Cloud SQL, Firestore, Pub/Sub, etc.), manages secrets, builds containers, wires networking and IAM, and deploys across environments — all through MCP tool calls. The platform handles Terraform generation, Cloud Build submission, auto-provisioning of supporting resources (service accounts, VPC connectors), and deployment orchestration. A read-only dev insight board provides real-time visibility via Firestore subscriptions.

## Core Value

An agent can go from zero to running multi-environment GCP infrastructure through programmatic tool calls, with auto-inferred IAM, auto-wired networking, and zero manual GCP console interaction.

## Requirements

### Validated

- ✓ Firebase Auth with email/password and Google OAuth -- existing
- ✓ Role-based project access control (viewer/editor/admin) -- existing
- ✓ Multi-tenant isolation via Firebase UID as tenant_id -- existing
- ✓ Project CRUD with Firestore persistence -- existing
- ✓ 22 node types with Pydantic config models -- existing
- ✓ Blueprint save/load with sharded Firestore subcollections -- existing
- ✓ Individual node CRUD with inline validation -- existing
- ✓ Cross-node reference validation and dependency graph -- existing
- ✓ Component registry mapping NodeType to ComponentDefinition -- existing
- ✓ Terraform HCL generation from blueprints via 21 Jinja2 templates -- existing
- ✓ GCP project provisioning (folder hierarchy, project creation, API enablement) -- existing
- ✓ Per-environment GCP projects (dev/staging/prod as separate projects) -- existing
- ✓ Deploy pipeline: generate TF -> submit Cloud Build -> poll -> update status -- existing
- ✓ SSE streaming of Cloud Build logs during deploy -- existing
- ✓ Secret Manager integration (CRUD, version management, masked values) -- existing
- ✓ Container build orchestration (code gen, Docker build, Artifact Registry push) -- existing
- ✓ GitHub repository integration (per-project repos, branch-per-env, snapshots) -- existing
- ✓ Code file storage (GCS-backed read/write/delete for compute nodes) -- existing
- ✓ Compute code generation (Python + Dockerfile from internalGraph) -- existing
- ✓ Deploy snapshots with per-node versioning and dirty-state detection -- existing
- ✓ 57 functional API endpoints across 16 handler modules -- existing

### Active

- [ ] MCP server exposing platform operations as agent-callable tools
- [ ] Auto-provisioning: compute node → auto-create service account + wire dependencies
- [ ] Auto-networking: compute + private data → auto-create VPC/subnet/connector
- [ ] IAM inference: dependency graph edges → GCP IAM role bindings as Terraform
- [ ] Dev insight board: read-only Firestore-subscribed dashboard for observability

### Out of Scope

- User-facing UX for resource configuration -- agent is the primary user
- Drag-and-drop node editor -- replaced by MCP tool-based node management
- Blueprint promotion UI -- agent handles via tools
- Billing integration -- deferred until agent workflow is solid
- Multi-cloud support -- GCP only by design constraint

## Context

**Existing codebase state:** 57 functional API endpoints, full deploy pipeline, 22 resource types with Terraform templates, GCP project provisioning, secret management, container builds, GitHub integration. The backend is production-ready for human-driven workflows.

**Strategic pivot (2026-03-27):** Reframed from design-specification-only milestone to implementation-focused agent engine. The backend API already does everything needed — it just needs an MCP interface for agent access, auto-provisioning intelligence for supporting resources, and a stripped-down frontend for dev observability.

**Target project:** "My Test Project" (ref: gtPIQyFrVTkEDZEm5gHc) under tyler@pl4m.com is already provisioned with dev env ready (GCP project: dev-my-test-project-c79ccd56).

## Constraints

- **Tech stack**: Must stay on GCP (Cloud Run, Firestore, Cloud Build)
- **Architecture**: Backend must remain stateless (FastAPI + Firestore) for Cloud Run scaling
- **Existing API**: MCP tools should wrap existing API handlers, not reimplement
- **Auth**: MCP server operates as tyler@pl4m.com (dev mode with AUTH_DISABLED=true)
- **Frontend**: Read-only, no interactive UX — Firestore subscriptions only

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Agent-first, UI second | Agent is the primary consumer; human observes via dashboard | Active |
| MCP wraps existing API | 57 endpoints already work; MCP is a tool interface layer | Active |
| Auto-provision supporting resources | Agent shouldn't manually create SAs, VPCs — platform infers | Active |
| Dev insight board over full UI | No user UX needed yet; just real-time Firestore debug views | Active |
| Use existing provisioned project | Tyler's "My Test Project" is ready; no provisioning needed | Active |

## Evolution

This document evolves at phase transitions and milestone boundaries.

---
*Last updated: 2026-03-27 after strategic pivot to agent-first engine*
