# GCP Orchestration Platform

A platform that abstracts GCP infrastructure for developers. Users visually design cloud architecture as a node graph (Cloud Run, Cloud Functions, Cloud SQL, Firestore, etc.), define dependencies and data contracts between services, and deploy with one click — without touching GCP directly.

The platform handles Terraform generation, Cloud Build submission, GCP project provisioning, and deployment orchestration. MCP tools and AI agents layer on top to assist with infrastructure configuration and service code generation grounded in actual infrastructure state.

**Core Value:** Users go from a visual architecture diagram to running, multi-environment GCP infrastructure without needing to understand Terraform, IAM, or GCP internals. An agent and user work in tandem.

## Current State

### What Works (dev environment)
- **Backend API** — FastAPI with 18 handler modules covering projects, nodes, blueprints, Terraform generation, deploys, provisioning, secrets, code files, builds, and more
- **25 node types** — All Pydantic schemas audited against GCP Terraform provider v7.25.0 (~100 fields added in M001)
- **UUID-based resource identity** — Every BaseNode has a stable UUID id; depends_on and all refs use IDs; name is display-only (M002)
- **Typed reference contract** — RESOURCE_REFS declares 34 cross-resource reference fields across 12 node types; validate_refs() catches broken refs; DAG auto-infers dependency edges from refs (M002)
- **Registry-driven GCP naming** — Per-type gcp_name_source/template/immutable in ComponentDefinition; resolve_gcp_name() derives names consistently across all 22 templates (M002)
- **Blueprint-driven pipeline** — Users design node graphs → validation → Terraform generation (Jinja2 templates) → Cloud Build submission → deploy to tenant GCP projects
- **Terraform generation** — 230 tests pass (47 terraform validate). All node types generate valid HCL.
- **Core Explorer** — Standalone test UI with ref dropdowns filtered by target type, GCP name previews, immutable-name warnings, and inline rename (M002)
- **Package structure** — Monolith split into `packages/core/`, `packages/api/`, `packages/platform/` with independent pyproject.toml and test suites
- **Multi-tenant isolation** — Firebase Auth UID scopes all data under `tenants/{uid}/` in Firestore
- **Environment promotion** — dev → staging → prod with per-environment GCP projects
- **MCP server** — Tools for AI agents to interact with infrastructure state
- **Dev infra** — `pl4m-host-dev` GCP project with Terraform, Cloud Build, Firebase, Firestore all working

### What Needs Work
- **Service contracts** — Design spec at `docs/specs/service-contract.md` but implementation was reverted (needs to be wired into terraform generator and IAM pipelines)
- **Dead code archival** — Unused frontend components not yet archived (R006)
- **3 xfail terraform tests** — Dotted annotation keys, Cloud SQL authorized_networks, VPC connector
- **Cloud SQL/Firestore templates** — Don't render all new schema fields from M001 audit

### What Doesn't Exist Yet
- **Production GCP project** — no `pl4m-host-prod`, no Terraform applied
- **Production frontend** — current React app is functional but not polished for real users
- **Billing/payments** — Stripe metered billing for pass-through GCP costs not implemented
- **Custom domain** — no domain configured
- **Monitoring/alerting** — no observability stack
- **Product sales site** — Next.js app exists in `apps/product-sales-site/` but unclear completion state

### Tech Stack
- **Backend:** Python 3.12, FastAPI, Pydantic 2, Firestore, Google Cloud SDKs
- **Frontend:** React 19, Vite, TypeScript, Zustand, shadcn/ui, Tailwind CSS 4
- **Sales site:** Next.js 16, React 19, @xyflow/react, Framer Motion
- **Infra:** Terraform, Cloud Build, Docker, Firebase Hosting
- **Auth:** Firebase Auth (email/password + Google OAuth)
- **CI/CD:** Cloud Build (`cloudbuild.yaml`)

### Constraints
- Must stay on GCP — the platform orchestrates GCP
- Backend must remain stateless (FastAPI + Firestore) for Cloud Run scaling
- Stripe metered billing for pass-through GCP costs
- Free tier: 1-3 compute nodes per project
- Cannot break current blueprint format without migration path
