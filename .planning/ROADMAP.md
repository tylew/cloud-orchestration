# Roadmap: GCP Orchestration Platform - System Design Specification

## Overview

This milestone produces a complete design specification for the GCP Orchestration Platform -- no code, only documents. The 45 requirements span 7 subsystems that must be designed in dependency order: resource lifecycle grounds everything, deploy engine builds on resource knowledge, IAM inference needs both, networking and databases are deploy layers, environment management ties it all together, and provisioning handles the GCP project bootstrap. Each phase produces design documents with data models, sequence diagrams, decision rationale, and edge case analysis.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Resource Node Specifications** - Document lifecycle state machines, mutability rules, and validation constraints for all 22+ node types
- [ ] **Phase 2: Resource Dependency & Convention Rules** - Specify Terraform mappings, inter-resource dependency rules, naming conventions, and structural vs environmental field classification
- [ ] **Phase 3: Deploy State Architecture & Sequencing** - Design layered Terraform state, full initial deploy sequence, incremental deploy sequence, and Cloud Build job configuration
- [ ] **Phase 4: Deploy Change Detection & Safety** - Specify change set computation, concurrent deploy prevention, per-resource status tracking, and destroy-recreate safety checks
- [ ] **Phase 5: Deploy Rollback & Preview** - Design rollback strategy and deploy preview flow for user confirmation before apply
- [ ] **Phase 6: IAM Inference Engine** - Specify complete role mapping table, inference algorithm, user overrides, Terraform generation, service account strategy, and cross-project bindings
- [ ] **Phase 7: Networking Architecture** - Design network topology, CIDR allocation, VPC Connector auto-wiring, Private Service Access, Terraform generation, and Direct VPC Egress evaluation
- [ ] **Phase 8: Database Lifecycle** - Design instance provisioning, schema management pipeline, service discovery, connection injection, schema definition format, and cross-environment schema promotion
- [ ] **Phase 9: Environment Management** - Design environment creation workflow, blueprint promotion with config overlays, drift detection, environment gating, and teardown procedures
- [ ] **Phase 10: Provisioning Pipeline** - Design rate-limited provisioning queue, API enablement sequencing, provisioning state machine, folder hierarchy, and IAM propagation delay handling

## Phase Details

### Phase 1: Resource Node Specifications
**Goal**: Every node type in the platform has a complete, unambiguous lifecycle specification that downstream design phases can reference
**Depends on**: Nothing (first phase)
**Requirements**: RSLC-01, RSLC-02, RSLC-03
**Success Criteria** (what must be TRUE):
  1. All 22+ node types have documented create/update/delete state machines with explicit state transitions
  2. Every config field for every node type is classified as mutable (in-place update) or immutable (destroy-recreate)
  3. Every config field has documented default values and validation constraints (type, range, pattern, required/optional)
  4. A reviewer can look up any node type and determine exactly what happens on create, update, or delete without ambiguity
**Plans:** 3 plans
Plans:
- [ ] 01-01-PLAN.md -- Lifecycle archetypes + Compute, Security, External category specs
- [ ] 01-02-PLAN.md -- Data category specs (5 parent types + 4 child types)
- [ ] 01-03-PLAN.md -- Messaging + Network category specs

### Phase 2: Resource Dependency & Convention Rules
**Goal**: Cross-resource rules are fully specified so that deploy engine, IAM, and networking phases have a complete dependency model to build on
**Depends on**: Phase 1
**Requirements**: RSLC-04, RSLC-05, RSLC-06, RSLC-07
**Success Criteria** (what must be TRUE):
  1. Every node type has a documented Terraform resource mapping (resource name, required providers, data sources needed)
  2. All valid inter-resource dependency edges are enumerated with their edge types and semantics
  3. Resource naming conventions and slug generation rules are specified for every node type with collision avoidance rules
  4. Every config field across all node types is classified as structural (same across envs) or environmental (varies per env) with rationale
**Plans**: TBD

### Phase 3: Deploy State Architecture & Sequencing
**Goal**: The layered Terraform state model and deploy execution sequences are fully designed so that every deploy scenario (first deploy, incremental, multi-layer) has a deterministic, documented path
**Depends on**: Phase 2
**Requirements**: DPLY-01, DPLY-04, DPLY-05, DPLY-10
**Success Criteria** (what must be TRUE):
  1. Terraform state layers are defined (network, data, IAM, compute, messaging) with explicit rules for which resource types belong to which layer
  2. The full initial deploy sequence is documented as a step-by-step flow with layer ordering, inter-layer dependencies, and failure handling
  3. The incremental deploy sequence is documented showing how only changed layers are applied while respecting layer dependencies
  4. Cloud Build job configuration is specified per deploy layer (timeouts, machine type, service account, environment variables)
**Plans**: TBD

### Phase 4: Deploy Change Detection & Safety
**Goal**: The platform can determine exactly what changed between deploys and prevent dangerous concurrent or destructive operations
**Depends on**: Phase 3
**Requirements**: DPLY-02, DPLY-03, DPLY-06, DPLY-07
**Success Criteria** (what must be TRUE):
  1. The change set computation algorithm is specified: given two blueprint snapshots, the output is a set of affected layers with per-resource change types
  2. Concurrent deploy prevention mechanism is documented with locking semantics, timeout behavior, and deadlock avoidance
  3. Deploy status tracking is specified with a per-resource state machine (pending, applying, applied, failed, destroyed) and Firestore schema
  4. Terraform plan output parsing rules are documented for detecting destroy-recreate warnings, with a clear pre-apply safety gate flow
**Plans**: TBD

### Phase 5: Deploy Rollback & Preview
**Goal**: Users understand what will happen before a deploy applies, and the platform has documented recovery procedures when deploys go wrong
**Depends on**: Phase 4
**Requirements**: DPLY-08, DPLY-09
**Success Criteria** (what must be TRUE):
  1. Rollback strategy is documented: which resource types support rollback, which do not, and what manual recovery procedures exist for each case
  2. Deploy preview flow is designed end-to-end: user triggers preview, platform runs terraform plan, output is parsed and presented, user confirms or cancels
  3. Edge cases are addressed: partial failures (some layers applied, others failed), data-bearing resource rollback limitations, and state file recovery
**Plans**: TBD

### Phase 6: IAM Inference Engine
**Goal**: The platform can deterministically derive correct GCP IAM bindings from a blueprint's dependency graph, with user override capability
**Depends on**: Phase 2
**Requirements**: IAM-01, IAM-02, IAM-03, IAM-04, IAM-05, IAM-06
**Success Criteria** (what must be TRUE):
  1. The complete (ActionType, NodeType) to GCP IAM Role mapping table is documented for every valid edge combination in the system
  2. The inference algorithm is specified as a pure function: given a dependency graph, it outputs a deterministic set of IAM bindings
  3. User override mechanism is designed: additive bindings, restriction capability, and how overrides interact with inferred bindings
  4. IAM Terraform generation strategy is documented using google_project_iam_member (additive only) with service account creation per compute node
  5. Cross-project IAM binding rules are specified for resources that span environments
**Plans**: TBD

### Phase 7: Networking Architecture
**Goal**: Tenant network isolation model is fully designed with automated CIDR allocation and connectivity to managed services
**Depends on**: Phase 3
**Requirements**: NET-01, NET-02, NET-03, NET-04, NET-05, NET-06
**Success Criteria** (what must be TRUE):
  1. Network topology decision (Shared VPC vs isolated VPC) is documented with research-backed rationale, tradeoff analysis, and migration path
  2. CIDR allocation strategy is specified with automated assignment, collision prevention, and Firestore-backed tracking
  3. VPC Connector auto-wiring rules are documented for Cloud Run to private resource connectivity, alongside Direct VPC Egress evaluation with recommendation
  4. Private Service Access and Private Service Connect configuration is specified for managed services (Cloud SQL, Memorystore)
  5. Network resource Terraform generation is fully specified (VPC, subnets, connectors, firewall rules, NAT)
**Plans**: TBD

### Phase 8: Database Lifecycle
**Goal**: Database provisioning, schema management, and service discovery are designed as separate concerns with clear handoff points
**Depends on**: Phase 3, Phase 7
**Requirements**: DBLC-01, DBLC-02, DBLC-03, DBLC-04, DBLC-05, DBLC-06
**Success Criteria** (what must be TRUE):
  1. Instance provisioning via Terraform is specified for each database type (Cloud SQL, Firestore, BigQuery, Bigtable) with type-specific configuration
  2. Schema management pipeline is designed as a post-Terraform step using Cloud Build migration jobs, clearly separated from instance provisioning
  3. Service discovery mechanism is specified: how compute nodes find database connection details at runtime (env vars, Secret Manager, metadata)
  4. Connection injection strategy is documented per database type (connection strings, IAM-based auth, Cloud SQL Auth Proxy sidecar)
  5. Blueprint schema definition format is specified per database type (tables, columns, indexes, types) with validation rules
**Plans**: TBD

### Phase 9: Environment Management
**Goal**: Multi-environment lifecycle is fully designed from creation through promotion, drift detection, and teardown
**Depends on**: Phase 2, Phase 3
**Requirements**: ENVM-01, ENVM-02, ENVM-03, ENVM-04, ENVM-05, ENVM-06
**Success Criteria** (what must be TRUE):
  1. Environment creation workflow is documented end-to-end: GCP project creation, API enablement, initial resource provisioning, and readiness verification
  2. Blueprint promotion flow is designed with env-specific config overlay mechanism that respects structural vs environmental field classification
  3. Drift detection approach is specified: how planned blueprint state is compared against actual GCP state, and what actions are available when drift is found
  4. Environment gating rules are documented (deployment ordering constraints between dev/staging/prod) with override capability
  5. Environment teardown procedure is specified with safe resource deletion ordering and data preservation options
**Plans**: TBD

### Phase 10: Provisioning Pipeline
**Goal**: GCP project provisioning is designed as a reliable, rate-limited pipeline that handles API quotas and IAM propagation delays
**Depends on**: Phase 9
**Requirements**: PROV-01, PROV-02, PROV-03, PROV-04, PROV-05
**Success Criteria** (what must be TRUE):
  1. Rate-limited provisioning queue is designed with Firestore-backed job queue, concurrency controls, and backpressure handling for GCP API quotas
  2. API enablement sequencing is documented with dependency ordering, propagation delay handling, and verification steps
  3. Provisioning status state machine is specified with all states, transitions, error recovery paths, and retry logic with exponential backoff
  4. GCP folder hierarchy strategy is documented for tenant organization with naming conventions and permission inheritance
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8 -> 9 -> 10

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Resource Node Specifications | 0/3 | Planning complete | - |
| 2. Resource Dependency & Convention Rules | 0/TBD | Not started | - |
| 3. Deploy State Architecture & Sequencing | 0/TBD | Not started | - |
| 4. Deploy Change Detection & Safety | 0/TBD | Not started | - |
| 5. Deploy Rollback & Preview | 0/TBD | Not started | - |
| 6. IAM Inference Engine | 0/TBD | Not started | - |
| 7. Networking Architecture | 0/TBD | Not started | - |
| 8. Database Lifecycle | 0/TBD | Not started | - |
| 9. Environment Management | 0/TBD | Not started | - |
| 10. Provisioning Pipeline | 0/TBD | Not started | - |
