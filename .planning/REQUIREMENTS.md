# Requirements: GCP Orchestration Platform — System Design Specification

**Defined:** 2026-03-26
**Core Value:** Users go from a visual architecture diagram to running, multi-environment GCP infrastructure without needing to understand Terraform, IAM, or GCP internals.

## v1 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### Resource Lifecycle

- [ ] **RSLC-01**: Document create/update/delete behavior for all 22+ node types with per-type state machines
- [ ] **RSLC-02**: Identify mutable vs immutable fields per resource type (which changes trigger destroy-recreate)
- [ ] **RSLC-03**: Define default values and validation constraints for every config field per node type
- [ ] **RSLC-04**: Document Terraform resource mapping for each node type (resource name, required providers, data sources)
- [ ] **RSLC-05**: Specify inter-resource dependency rules (which types can depend on which, valid edge types)
- [ ] **RSLC-06**: Define resource naming conventions and slug generation rules per type
- [ ] **RSLC-07**: Classify each config field as structural (same across envs) vs environmental (varies per env)

### Deploy Engine

- [ ] **DPLY-01**: Design layered Terraform state architecture (network, data, IAM, compute, messaging layers per tenant env)
- [ ] **DPLY-02**: Specify change set computation algorithm (diff blueprint snapshots to determine which layers need apply)
- [ ] **DPLY-03**: Design concurrent deploy prevention (mutex/locking mechanism per tenant environment)
- [ ] **DPLY-04**: Document full initial deploy sequence (first deploy of a new environment, all layers)
- [ ] **DPLY-05**: Document incremental deploy sequence (subsequent deploys, only changed layers)
- [ ] **DPLY-06**: Design deploy status tracking with per-resource granularity and state machine
- [ ] **DPLY-07**: Specify Terraform plan output parsing for destroy-recreate warnings (pre-apply safety check)
- [ ] **DPLY-08**: Design rollback strategy (what can be rolled back, what cannot, recovery procedures)
- [ ] **DPLY-09**: Design deploy preview flow (show plan output to user before apply)
- [ ] **DPLY-10**: Specify Cloud Build job configuration per deploy layer (timeouts, machine type, service accounts)

### IAM Inference

- [ ] **IAM-01**: Define complete (ActionType, NodeType) -> GCP IAM Role mapping table for all valid edge combinations
- [ ] **IAM-02**: Specify IAM inference algorithm (how dependency graph edges produce IAM bindings)
- [ ] **IAM-03**: Design user override mechanism (additive bindings + ability to tighten/restrict inferred roles)
- [ ] **IAM-04**: Document IAM generation as Terraform using `google_project_iam_member` exclusively (additive, never authoritative)
- [ ] **IAM-05**: Specify service account creation and assignment strategy per compute node
- [ ] **IAM-06**: Design cross-project IAM bindings for resources that span environments

### Networking

- [ ] **NET-01**: Design network topology (Shared VPC vs isolated VPC, with research-backed recommendation and rationale)
- [ ] **NET-02**: Specify CIDR allocation and management strategy (automated, collision-free, Firestore-backed)
- [ ] **NET-03**: Design VPC Connector auto-wiring for Cloud Run -> private resources (Cloud SQL, Memorystore)
- [ ] **NET-04**: Specify Private Service Access / Private Service Connect configuration for managed services
- [ ] **NET-05**: Document network resource Terraform generation (VPC, subnets, connectors, firewall rules)
- [ ] **NET-06**: Evaluate Cloud Run Direct VPC Egress as alternative to VPC Connectors with recommendation

### Database Lifecycle

- [ ] **DBLC-01**: Design database instance provisioning via Terraform for each database type (Cloud SQL, Firestore, BigQuery, Bigtable)
- [ ] **DBLC-02**: Design schema management pipeline separation (instance via TF, schema DDL via Cloud Build migration steps)
- [ ] **DBLC-03**: Specify service discovery mechanism (how compute nodes find and connect to their databases at runtime)
- [ ] **DBLC-04**: Design connection injection strategy (connection strings, IAM-based auth, Cloud SQL Auth Proxy)
- [ ] **DBLC-05**: Document per-database-type schema definition format in the blueprint (tables, columns, indexes, types)
- [ ] **DBLC-06**: Design cross-environment schema promotion workflow (dev schema -> staging -> prod)

### Environment Management

- [ ] **ENVM-01**: Design environment creation workflow (GCP project creation, API enablement, initial provisioning sequence)
- [ ] **ENVM-02**: Specify blueprint promotion flow with env-specific config overlay mechanism
- [ ] **ENVM-03**: Design structural vs environmental field classification in component registry
- [ ] **ENVM-04**: Specify drift detection approach (planned blueprint state vs actual GCP state)
- [ ] **ENVM-05**: Design environment gating rules (dev must deploy before staging, staging before prod)
- [ ] **ENVM-06**: Document environment teardown/cleanup procedure (safe resource deletion order)

### Provisioning

- [ ] **PROV-01**: Design rate-limited provisioning queue (not fire-and-forget background tasks) to handle GCP API quotas
- [ ] **PROV-02**: Specify API enablement sequencing (which APIs must be enabled in which order, with propagation delays)
- [ ] **PROV-03**: Design provisioning status state machine with error recovery and retry logic
- [ ] **PROV-04**: Specify GCP folder hierarchy strategy for tenant organization
- [ ] **PROV-05**: Document IAM propagation delay handling (up to 7 minutes between grant and effective)

## v2 Requirements

Deferred to future milestone. Tracked but not in current roadmap.

### Billing

- **BILL-01**: Design GCP billing export to BigQuery per tenant project
- **BILL-02**: Design Stripe metered billing pipeline (BigQuery -> Stripe meter events)
- **BILL-03**: Specify cost attribution per tenant project with 24-48h export lag handling
- **BILL-04**: Design real-time cost estimation as supplement to lagged billing export
- **BILL-05**: Design usage dashboards per tenant

### Advanced Features

- **ADVF-01**: Design MCP server interface for programmatic resource provisioning and linking
- **ADVF-02**: Design AI agent integration with infrastructure-aware code generation
- **ADVF-03**: Design IAM drift detection and automated remediation
- **ADVF-04**: Design multi-region networking support
- **ADVF-05**: Design resource lifecycle hooks (pre-create, post-deploy validation)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Code implementation | This milestone is design specification only — no code changes |
| MCP server implementation | Deferred until platform business logic is implemented |
| AI agent code generation | Deferred until MCP tools provide ground truth access |
| Multi-cloud support | GCP only by design constraint |
| Mobile app | Web-first platform |
| Self-hosted deployment | Platform runs on GCP, orchestrates GCP |
| Real-time collaboration design | Already implemented via Firestore listeners |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| RSLC-01 | - | Pending |
| RSLC-02 | - | Pending |
| RSLC-03 | - | Pending |
| RSLC-04 | - | Pending |
| RSLC-05 | - | Pending |
| RSLC-06 | - | Pending |
| RSLC-07 | - | Pending |
| DPLY-01 | - | Pending |
| DPLY-02 | - | Pending |
| DPLY-03 | - | Pending |
| DPLY-04 | - | Pending |
| DPLY-05 | - | Pending |
| DPLY-06 | - | Pending |
| DPLY-07 | - | Pending |
| DPLY-08 | - | Pending |
| DPLY-09 | - | Pending |
| DPLY-10 | - | Pending |
| IAM-01 | - | Pending |
| IAM-02 | - | Pending |
| IAM-03 | - | Pending |
| IAM-04 | - | Pending |
| IAM-05 | - | Pending |
| IAM-06 | - | Pending |
| NET-01 | - | Pending |
| NET-02 | - | Pending |
| NET-03 | - | Pending |
| NET-04 | - | Pending |
| NET-05 | - | Pending |
| NET-06 | - | Pending |
| DBLC-01 | - | Pending |
| DBLC-02 | - | Pending |
| DBLC-03 | - | Pending |
| DBLC-04 | - | Pending |
| DBLC-05 | - | Pending |
| DBLC-06 | - | Pending |
| ENVM-01 | - | Pending |
| ENVM-02 | - | Pending |
| ENVM-03 | - | Pending |
| ENVM-04 | - | Pending |
| ENVM-05 | - | Pending |
| ENVM-06 | - | Pending |
| PROV-01 | - | Pending |
| PROV-02 | - | Pending |
| PROV-03 | - | Pending |
| PROV-04 | - | Pending |
| PROV-05 | - | Pending |

**Coverage:**
- v1 requirements: 45 total
- Mapped to phases: 0
- Unmapped: 45

---
*Requirements defined: 2026-03-26*
*Last updated: 2026-03-26 after initial definition*
