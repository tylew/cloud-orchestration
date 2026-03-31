# Requirements

## Active

### R001: Terraform Spec Completeness
Every node type's Pydantic schema must cover the full set of user-configurable fields from the corresponding GCP Terraform provider resource. Templates must render all schema fields correctly.
- **Owner:** M1
- **Validation:** Audit report comparing each schema config against Terraform provider docs; all fields present and correctly typed

### R002: Deep DAG — Logical Data Flow
The DAG must model logical dependencies beyond infrastructure: which compute nodes consume which data collections, tables, topics, and buckets. This includes Firestore collection paths (named and template like `{{user_id}}`), BigQuery tables, Cloud SQL tables, PubSub topics, and GCS prefixes.
- **Owner:** M1
- **Validation:** A compute node referencing a Firestore collection surfaces that dependency in the DAG; validation catches broken references

### R003: Data Contracts — Schema Definitions Within Resources
Users/agents can define schemas within data nodes: Firestore collection fields and subcollections, BigQuery table schemas, Cloud SQL table columns. These become the contract that compute nodes reference.
- **Owner:** M1
- **Validation:** Firestore, BigQuery, and Cloud SQL schemas defined in node config; field references validated cross-node

### R004: Workflow Specs — Compute Node References Data Contracts
Compute nodes define workflows that reference specific data contracts (collections, tables, topics). These specs form the input for AI codegen agents.
- **Owner:** M1/M2
- **Validation:** A compute node's internal graph steps reference specific collections/fields; codegen produces code that uses those references

### R005: Dead Simple Test UI
A minimal functional UI sufficient for one developer to test backend functionality — create projects, add/configure nodes, view DAG, trigger validation and deploys. Not polished, just functional.
- **Owner:** M1
- **Validation:** Can complete a full workflow: create project → add nodes → define data contracts → configure compute workflows → validate → generate Terraform

### R006: Dead Code Archived
Unused frontend components, stale screens, and orphaned code moved to an archive directory to keep the working tree clean.
- **Owner:** M1
- **Validation:** No dead imports; archived code in `archive/` directory; app still builds and runs

### R007: Agent-Driven Codegen Pipeline
AI coding agents can read workflow specs + data contracts, generate implementation code, execute tests. The platform orchestrates this deterministically.
- **Owner:** M2
- **Validation:** Agent reads spec from API, generates working code with tests, platform tracks execution

### R008: Production Infrastructure
Production GCP project provisioned, Terraform applied, CI/CD pipeline deploying to prod, custom domain configured, monitoring and alerting in place.
- **Owner:** M3
- **Validation:** App accessible on production domain with HTTPS; monitoring dashboards active

### R009: Billing — Stripe Metered Billing
Pass-through GCP costs billed to users via Stripe metered billing. Free tier enforced (1-3 compute nodes per project).
- **Owner:** M4
- **Validation:** Stripe integration active; usage tracked per tenant; free tier limits enforced

### R010: Product Sales Site Live
Marketing/sales site deployed on custom domain with pricing, features, and sign-up flow.
- **Owner:** M4
- **Validation:** Sales site accessible on domain; links to app sign-up

## Deferred

*None yet.*

## Validated

*None yet.*

## Out of Scope

*None yet.*
