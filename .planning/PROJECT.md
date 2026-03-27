# GCP Orchestration Platform

## What This Is

A platform that abstracts GCP infrastructure for developers. Users visually design their cloud architecture as a node graph (Cloud Run, Cloud Functions, Cloud SQL, Firestore, etc.), define dependencies and data contracts between services, and deploy with one click -- without touching GCP directly. The platform handles Terraform generation, Cloud Build submission, GCP project provisioning, and deployment orchestration. Eventually, MCP tools and AI agents will layer on top to assist with infrastructure configuration and service code generation grounded in the actual infrastructure state (DB schemas, IAM bindings, networking).

## Core Value

Users go from a visual architecture diagram to running, multi-environment GCP infrastructure without needing to understand Terraform, IAM, or GCP internals.

## Requirements

### Validated

- ✓ Firebase Auth with email/password and Google OAuth -- existing
- ✓ Role-based project access control (viewer/editor/admin) -- existing
- ✓ Multi-tenant isolation via Firebase UID as tenant_id -- existing
- ✓ Project CRUD with Firestore persistence -- existing
- ✓ Visual node graph editor for GCP resources (22 node types) -- existing
- ✓ Blueprint save/load with sharded Firestore subcollections -- existing
- ✓ Individual node CRUD with inline validation -- existing
- ✓ Cross-node reference validation and dependency graph -- existing
- ✓ Component registry mapping NodeType to ComponentDefinition -- existing
- ✓ Terraform HCL generation from blueprints via Jinja2 templates -- existing
- ✓ GCP project provisioning (folder hierarchy, project creation, API enablement) -- existing
- ✓ Per-environment GCP projects (dev/staging/prod as separate projects) -- existing
- ✓ Deploy pipeline: generate TF -> submit Cloud Build -> poll -> update status -- existing
- ✓ SSE streaming of Cloud Build logs during deploy -- existing
- ✓ Blueprint promotion between environments -- existing
- ✓ Secret Manager integration for tenant secrets -- existing
- ✓ Container build tracking -- existing
- ✓ GitHub repository integration -- existing
- ✓ Collaborator management with shared project index -- existing
- ✓ Real-time provisioning status via Firestore listeners -- existing
- ✓ Activity logging for blueprint changes -- existing

### Active

- [ ] Complete system design specification covering all platform subsystems
- [ ] Networking architecture design (Shared VPC vs isolated, tenant isolation with shared host infrastructure)
- [ ] Deploy ordering and incremental deploy design (diff-based minimal Terraform generation)
- [ ] Database management lifecycle (provisioning + schema management + service discovery/connection)
- [ ] Multi-environment lifecycle design (creation, divergence, promotion, drift management)
- [ ] IAM model design (auto-inferred from dependency graph + user overrides)
- [x] Resource lifecycle documentation for all 22+ node types — Validated in Phase 01: resource-node-specifications
- [ ] Billing pass-through design (Stripe metered billing for GCP cost tracking per tenant)
- [ ] Platform for future MCP tools and AI agent integration (infra-aware code generation, resource provisioning)

### Out of Scope

- MCP server implementation -- comes after platform business logic is solid
- AI agent code generation -- comes after MCP tools, needs stable infra ground truth
- Mobile app -- web-first platform
- Multi-cloud support -- GCP only by design constraint
- Self-hosted deployment -- platform runs on GCP, orchestrates GCP

## Context

**Existing codebase state:** The platform has a working foundation -- FastAPI backend with 16 router modules, React SPA frontend with Zustand state management, Firestore persistence, GCP project provisioning, Terraform generation, and Cloud Build deploys. The architecture is monorepo with `packages/` (Python backend) and `apps/web/` (React frontend).

**What's missing:** The existing code works for individual features but the full end-to-end system design hasn't been thought through holistically. Questions like "what exact order do resources deploy in?", "how does networking actually get configured for a tenant?", "what happens on the second deploy vs the first?", "how do database schemas flow through the system?" -- these need rigorous theoretical answers before the implementation can be coherent.

**Brownfield context:** This milestone is purely about design specification -- no code changes. The deliverable is a complete set of design documents that make implementation nearly mechanical.

**AI integration vision:** The platform is the foundation layer. Once business logic and resource lifecycle are fully specified and implemented, MCP tools will provide programmatic access to provisioning and resource linking. AI agents with access to infrastructure state (DB schemas, networking config, IAM bindings) will generate service code grounded in truth. This is Phase 2+ -- this milestone establishes the ground truth they'll need.

## Constraints

- **Tech stack**: Must stay on GCP (Cloud Run, Firestore, Cloud Build) -- the platform orchestrates GCP
- **Architecture**: Backend must remain stateless (FastAPI + Firestore) for Cloud Run scaling
- **Billing**: Stripe metered billing for pass-through GCP costs -- no alternative payment processors
- **Free tier limits**: 1-3 compute nodes per project to control costs
- **Existing users**: Cannot break current blueprint format -- migration path required if schema changes
- **Networking**: Host project likely owns shared infrastructure; tenants get isolated segments
- **Deliverable**: Complete specification -- every subsystem documented with data models, sequences, and edge cases

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Design-first milestone (no code) | Full system needs theoretical coherence before implementation can be effective | -- Pending |
| Pass-through billing via Stripe | Platform tracks GCP costs per tenant, bills what they use | -- Pending |
| IAM: auto-infer + user override | Dependency graph provides sensible defaults; users can tighten/override | -- Pending |
| Networking: research Shared VPC vs isolated | Host project may provision shared networking, tenants get isolated segments | -- Pending |
| Incremental deploys over full redeploy | After initial deploy, only changed resources should redeploy via blueprint diffing | -- Pending |
| MCP/AI deferred to post-platform | Platform business logic and lifecycle must be solid before agent layer | -- Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check -- still the right priority?
3. Audit Out of Scope -- reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-27 after Phase 01 completion*
