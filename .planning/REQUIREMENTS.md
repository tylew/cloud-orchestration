# Requirements: GCP Orchestration Platform — Agent Engine

**Defined:** 2026-03-27
**Core Value:** An AI agent can provision, configure, and deploy GCP infrastructure through MCP tools without human intervention, while a developer observes in real-time.

## v1 Requirements

### MCP Server

- [x] **AGT-01**: MCP server with tools for project lifecycle (list projects, get project state, select environment)
- [x] **AGT-02**: MCP tools for node CRUD (add node by type, configure node, delete node, list nodes with validation state)
- [x] **AGT-03**: MCP tools for secret management (create/update/delete secrets, list secrets with masked values)
- [x] **AGT-04**: MCP tools for code file management (read/write/delete files on compute nodes, list files)
- [x] **AGT-05**: MCP tools for container builds (trigger build, check build status, get build logs)
- [x] **AGT-06**: MCP tools for deploy operations (trigger deploy, check deploy status, get plan/apply output, stream logs)
- [x] **AGT-07**: MCP tools for blueprint-level operations (get full blueprint, validate blueprint, generate Terraform preview)

### Auto-Provisioning Intelligence

- [x] **AGT-08**: When a compute node is added, auto-create a service_account node and wire it as a dependency
- [x] **AGT-09**: When a compute node depends on a private data resource (Cloud SQL, etc.), auto-create VPC/subnet/connector nodes and wire networking
- [x] **AGT-10**: IAM role bindings auto-inferred from dependency graph edges (ActionType + target NodeType → GCP IAM role) and generated as Terraform

### Dev Insight Board (Frontend)

- [x] **AGT-11**: Read-only dashboard with real-time Firestore subscriptions showing: project state, resource list with types, validation output per node, Terraform compilation output, deploy status/logs, activity feed (scaffold in 01-03, panels in 01-06)
- [x] **AGT-12**: Debug endpoints exposed: raw project state, full validation output, compiled Terraform files, deploy history, node deploy status with modified flags

## Phase 2: Cloud DNS Node Type

### Cloud DNS

- [x] **DNS-01**: NodeType enum includes CLOUD_DNS with value "cloud_dns"
- [x] **DNS-02**: CloudDnsConfig Pydantic model validates zone configuration (dns_name, visibility, DNSSEC, records, labels)
- [x] **DNS-03**: REGISTRY entry with category="Network", terraform_resource="google_dns_managed_zone", default_outputs for name_servers and dns_name
- [x] **DNS-04**: Terraform template generates google_dns_managed_zone and google_dns_record_set resources with trailing dot handling
- [x] **DNS-05**: Cross-node references in DNS records (e.g., target="node:my-lb.ip_address") resolve via resolve_ref in template
- [x] **DNS-06**: Required field validation enforces dns_name on cloud_dns nodes; _NODE_TYPE_APIS maps to dns.googleapis.com

## Phase 3: Terraform Output Surfacing

### Terraform Outputs

- [x] **OUT-01**: Generate TF output blocks in dedicated outputs.tf wired to registry default_outputs
- [x] **OUT-02**: Only external-facing outputs surfaced; vpc/subnet/vpc_connector excluded via _INTERNAL_ONLY_TYPES
- [x] **OUT-03**: Cloud Build step after apply runs terraform output -json; JSON written to GCS results bucket
- [x] **OUT-04**: Parsed outputs stored on deploy record (terraform_outputs) and env_outputs/{env} doc with correct by_node grouping
- [x] **OUT-05**: New dedicated MCP tool get_deploy_outputs(project_ref_id, env_name) returns env outputs
- [x] **OUT-06**: Existing get_deploy_status response is NOT modified

## Phase 5: E2E User Acceptance Testing

### User Acceptance Testing

- [ ] **UAT-01**: Agent can configure resources (add cloud_dns node via MCP, update config, validate blueprint) end-to-end
- [ ] **UAT-02**: Agent can deploy infrastructure and query terraform outputs via get_deploy_outputs MCP tool
- [ ] **UAT-03**: Agent can modify existing blueprints (add/remove/update nodes), re-deploy, and verify changes reflected
- [ ] **UAT-04**: Agent can read build logs, deploy logs, deploy status, and output values through MCP tools

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
| AGT-01 | Phase 1 | Complete |
| AGT-02 | Phase 1 + Phase 4 (gap) | Complete (Phase 1), Pending (cloud_dns gap in Phase 4) |
| AGT-03 | Phase 1 | Complete |
| AGT-04 | Phase 1 | Complete |
| AGT-05 | Phase 1 | Complete |
| AGT-06 | Phase 1 | Complete (pre-existing list_deploys issue noted) |
| AGT-07 | Phase 1 | Complete |
| AGT-08 | Phase 1 | Complete |
| AGT-09 | Phase 1 | Complete |
| AGT-10 | Phase 1 | Complete |
| AGT-11 | Phase 1 + Phase 4 (gap) | Complete (code), Pending (cloud_dns label in Phase 4) |
| AGT-12 | Phase 1 | Complete |
| DNS-01 | Phase 2 | Complete |
| DNS-02 | Phase 2 | Complete |
| DNS-03 | Phase 2 | Complete |
| DNS-04 | Phase 2 | Complete |
| DNS-05 | Phase 2 | Complete |
| DNS-06 | Phase 2 | Complete |
| OUT-01 | Phase 3 | Complete |
| OUT-02 | Phase 3 | Complete |
| OUT-03 | Phase 3 | Complete |
| OUT-04 | Phase 3 + Phase 4 (gap) | Partial (flat OK, by_node parsing gap in Phase 4) |
| OUT-05 | Phase 3 | Complete |
| OUT-06 | Phase 3 | Complete |
| UAT-01 | Phase 5 | Pending |
| UAT-02 | Phase 5 | Pending |
| UAT-03 | Phase 5 | Pending |
| UAT-04 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 12 total (AGT-01 through AGT-12)
- Phase 2 requirements: 6 total (DNS-01 through DNS-06)
- Phase 3 requirements: 6 total (OUT-01 through OUT-06)
- Phase 5 requirements: 4 total (UAT-01 through UAT-04)
- Mapped to phases: 28
- Unmapped: 0

---
*Requirements defined: 2026-03-27*
*Phase 2 requirements added: 2026-03-27*
*Phase 3/5 requirements added: 2026-03-28*
