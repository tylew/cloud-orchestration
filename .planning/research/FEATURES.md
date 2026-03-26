# Feature Landscape

**Domain:** Multi-tenant GCP infrastructure orchestration platform (visual IaC with Terraform generation)
**Researched:** 2026-03-26
**Confidence:** HIGH (based on existing codebase analysis, GCP documentation, and IaC platform patterns)

---

## Table Stakes

Features that must be fully designed for the platform to function coherently. Missing any of these creates gaps that compound into architectural debt or user-facing failures.

### 1. Networking Architecture

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Shared VPC with tenant subnet isolation | Tenants need private connectivity between services (Cloud Run to Cloud SQL) without per-tenant VPC overhead. GCP best practice is host-project Shared VPC with per-tenant subnets. | High | Host project owns the VPC; tenant service projects attach as service projects. Current VPC/subnet nodes exist but no host-project orchestration. |
| Private Service Connect for managed services | Cloud SQL, Memorystore, etc. require private IP connectivity. PSC is the GCP-recommended path, replacing legacy VPC peering for managed services. | High | Cloud SQL config already has `ip_configuration.private_network` field but no automated provisioning of the PSA range or PSC endpoint. |
| VPC Connector auto-wiring for serverless | Cloud Run and Cloud Functions need VPC Connectors to reach private resources. This is the bridge between serverless compute and VPC-connected data stores. | Medium | VPC Connector node type exists. Design must specify auto-wiring: when a compute node depends on a private data node, a VPC Connector is implicitly required. |
| IP address management (IPAM) | Tenants cannot pick overlapping CIDR ranges. The platform must allocate non-overlapping subnets from a master CIDR block. | Medium | No IPAM logic exists. Design must specify allocation strategy (e.g., /24 per tenant from a /16 supernet). |
| DNS and service discovery | Compute nodes need to resolve database endpoints by name, not IP. Cloud DNS private zones scoped to tenant VPC segments. | Medium | Cloud SQL `connection_name` is the GCP-native discovery mechanism for SQL; Firestore uses project-scoped defaults. Design should clarify when DNS is needed vs. when GCP-native discovery suffices. |

### 2. Deploy Orchestration

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Dependency-ordered resource deployment | Resources must deploy in topological order: SA before compute, VPC before subnet before connector before compute. | Low | Already implemented via `BlueprintDAG.topological_sort()` and `parallel_batches()`. Design spec should formalize the ordering contract and document parallel batch semantics. |
| Incremental deploy semantics | After first deploy, only changed resources should be reapplied. Need to clarify: does the platform filter TF generation or always generate all TF and let Terraform's own state comparison handle diffs? | Medium | `compute_modified_flags()` exists for config hash change detection. Terraform natively diffs state vs. config. Design must decide: always generate full TF (simpler, Terraform handles diff) vs. selective generation (complex, fragile). Recommendation: always generate full TF. |
| Deploy gating between environments | Cannot deploy staging until dev is deployed. Prevents promoting untested infrastructure. | Low | Already implemented in deploy handler. Design spec should formalize gating rules and edge cases (can you skip staging? can you redeploy dev after staging?). |
| Deploy status lifecycle | Every deploy must have observable state: pending, generating, building, applying, ready, failed. Failed deploys must be retryable. | Low | Already implemented via Firestore deploy records with step tracking. Design should specify idempotency guarantees and retry semantics. |
| Rollback strategy | When deploy fails mid-apply, infrastructure is in partial state. Platform needs a defined recovery path. | Medium | Terraform's own state handles partial applies -- re-running `plan + apply` converges to desired state. Design should specify: no explicit rollback mechanism. Instead, re-deploy the last known-good blueprint (which the deploy snapshot system already tracks). |
| Concurrent deploy prevention | Only one deploy per environment at a time. Concurrent deploys to the same TF state cause corruption. | Medium | Not currently enforced with locking. Design must specify: check for in-progress deploys before starting a new one, or use Terraform state locking via GCS backend (which already exists in `BackendConfig`). |
| Cloud Build lifecycle management | Each deploy runs a Cloud Build job. Design must cover: timeout configuration, log streaming (SSE exists), stale build cleanup, and build cost management. | Medium | Build submission, polling, and SSE log streaming exist. Design should specify timeout defaults and what happens when a build is stuck. |

### 3. IAM Design

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Auto-inferred IAM from dependency graph | When Cloud Run depends on Cloud SQL, auto-grant `roles/cloudsql.client` to the compute SA. The dependency graph IS the IAM intent. | High | `iam_scope` and `iam_terraform_resource` exist in `ComponentDefinition`. `invoker_bindings` and `accessor_bindings` exist on nodes. `ACTION_VALID_TARGETS` maps actions to valid node types. Design must specify the complete inference table: `{source_type, action_type, target_type} -> {IAM role, binding scope}`. |
| Dedicated service account per compute node | Each compute node gets its own SA with only the permissions it needs. No shared SAs across services. Least privilege by default. | Medium | Service account node type exists. Validation already requires `service_account` on compute configs. Design must specify: auto-create SA node when compute node is added (implicit) vs. require explicit SA node (current behavior). |
| Cross-project IAM for Shared VPC | In Shared VPC, the host project grants `compute.networkUser` to service project SAs. Platform must orchestrate IAM bindings across project boundaries. | High | Not currently designed. The TF generator currently targets a single project. Cross-project bindings require generating TF that applies to the host project, not just the tenant project. |
| User-overridable IAM permissions | Auto-inferred permissions are defaults. Users can add/remove specific roles via `iam.roles[]` on nodes. | Low | Field exists on `IamBlock`. Design should clarify merge semantics: inferred roles UNION user roles (additive only) vs. user roles REPLACE inferred (full control). Recommend: additive with explicit deny list. |

### 4. Database Lifecycle

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Database instance provisioning | Cloud SQL, Firestore, BigQuery, Bigtable instances created via Terraform with full config (tier, version, networking, backups). | Low | Already implemented via TF templates for all 4 database types. `CloudSqlConfig`, `FirestoreConfig`, `BigQueryConfig`, `BigtableConfig` all have rich Pydantic models. |
| Child resource provisioning | Databases within Cloud SQL instances, BigQuery tables within datasets, Firestore collections within databases. | Medium | Child node types exist: `cloud_sql_database`, `bigquery_table`, `firestore_collection`, `cloud_sql_table`. BQ tables and SQL databases generate TF. Firestore collections generate TTL policies. SQL tables are documentation-only (no TF, per D-09). |
| Connection string / endpoint injection | Compute nodes that depend on data nodes need connection info injected as env vars at runtime. Cloud SQL connection name, Firestore project ID, BigQuery dataset ID, bucket name. | Medium | `inputs`/`outputs` exist on nodes. `resolve_node_ref()` handles TF-level references. Design must specify the full injection contract: which env vars are set for each dependency type, and how they flow through TF outputs to Cloud Run env vars. |
| Schema management boundary | Clarify what the platform manages (instance + database + table definitions) vs. what it documents (SQL DDL for migrations). | Medium | Cloud SQL tables have `SqlColumn` definitions but no TF generation (documentation-only). Design must make this boundary explicit: platform provisions infrastructure, external tools handle schema migrations (Flyway, Alembic, etc.). |
| Backup and recovery defaults | Cloud SQL backups, PITR, retention. Users expect sensible production-ready defaults with override capability. | Low | `SqlBackupConfiguration` exists with defaults (enabled, PITR enabled, 7-day retention, 03:00 start). Design should document these as opinionated defaults and what users can change. |

### 5. Environment Management

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Environment creation with GCP project provisioning | Each env maps to a separate GCP project. Creating an env provisions the project, enables APIs, creates folder hierarchy. | Low | Already implemented with background tasks, status tracking, and real-time Firestore updates. Design should specify the full provisioning checklist and what differs between dev (initial) and subsequent envs (staging/prod). |
| Blueprint promotion with value stripping | Copy blueprint from source env to target env, stripping env-specific values (secrets, env var values). Structure travels; configuration is env-specific. | Medium | Already implemented in `promote.py`. Design must specify exactly what gets stripped, what gets transformed (project_id, region in GlobalConfig), and what gets preserved (node structure, dependencies). |
| Environment-specific configuration overlays | Same blueprint structure, different config per env: smaller instances in dev, HA in prod, different secrets, different scaling. | High | NOT currently designed. This is a significant gap. Current promotion strips env var values but doesn't support env-specific sizing/tier overrides. Design must specify: per-env config overlays (e.g., `cloud_sql.tier: db-f1-micro` in dev, `db-n1-standard-2` in prod) or environment profiles. |
| Environment count constraint | Free tier limits to 3 environments. Platform enforces at env creation. | Low | Already enforced (max 3 in `add_environment`). Design should specify whether this is configurable per billing plan/tier. |

### 6. Billing and Cost Management

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Per-tenant GCP cost tracking | Each tenant's GCP projects incur costs. Platform must track costs and attribute to correct tenant. GCP billing export to BigQuery is the standard mechanism. | High | Not implemented. Design must specify: billing export destination (host project BigQuery dataset), query pattern to aggregate by project/folder, sync frequency, cost attribution labels. GCP billing exports have 24-48 hour delay. |
| Stripe metered billing integration | Tenants are billed for GCP usage via Stripe. Platform reads GCP costs and reports usage events to Stripe meters. | High | Not implemented. Design must specify: Stripe meter event schema, usage reporting frequency, billing cycle alignment with GCP export lag, markup calculation, and Stripe subscription/meter lifecycle. |
| Quota enforcement (resource limits) | Free tier: 1-3 compute nodes per project. Paid tiers: higher limits. Enforce at blueprint save time, not just project creation. | Medium | Basic project quota exists in `tenant_store`. Design must extend to: per-project node count limits, per-type limits (max Cloud SQL instances), compute resource caps (CPU/memory), and storage limits. |

### 7. Platform Security

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Tenant isolation audit | Verify that no tenant can access another's GCP projects, Firestore data, or deploy pipelines. Document the isolation boundary. | Low | Already enforced via `tenant_id` path scoping in Firestore and GCP project/folder isolation. Design should document the complete isolation matrix and verify there are no cross-tenant data paths. |
| Platform service account least privilege | The platform's own SA (Cloud Build submitter, project creator) must have only the permissions it needs, scoped to the tenants folder hierarchy. | Medium | Partially defined in `infra/host/`. Design must specify exact IAM roles at org level (project creator), folder level (folder admin on tenants folder), and project level (Cloud Build runner, storage admin). |
| Secret lifecycle management | Tenant secrets stored in Secret Manager within tenant's GCP project. Secrets injectable into compute nodes at deploy time. | Medium | Secret Manager node type exists. Secrets store module exists. Design must specify full lifecycle: create secret TF resource -> user sets value via API/console -> compute node references secret -> TF generates secret accessor + env var injection. |

---

## Differentiators

Features that set the platform apart from manually writing Terraform or using generic IaC orchestration tools (Spacelift, env0, Terraform Cloud). Not required for basic functionality, but provide significant competitive value.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Visual dependency graph with auto-wired IAM | Users draw connections between nodes; platform infers IAM, networking, and env var injection. No other tool does visual-to-IAM inference from a node graph. | High | Partially exists (dependency graph, IAM fields, action validation). Full auto-inference from the visual graph is the core differentiator. |
| Infrastructure drift detection with visual diff | Show users what changed in live infrastructure vs. blueprint. Highlight drifted resources in the editor. Run `terraform plan -refresh-only` periodically or on-demand. | High | `compute_modified_flags()` compares config hashes but only against last deploy snapshot, not live infra. True drift detection requires running TF plan against live state, which means a Cloud Build job just for plan. |
| Per-node deploy status in visual editor | Each node shows deploy state: never-deployed, deployed, modified-since-deploy, deploy-failed. Users see at a glance what needs attention. | Medium | `node_deploy_status` doc and deploy snapshots exist. Design should specify the full node state machine and visual indicator mapping. |
| Blueprint versioning with rollback | Track every blueprint save with full snapshot. Allow reverting to any previous version. Compare versions side-by-side. | Medium | Activity log with change summaries exists. Full versioning would require storing complete envelope snapshots per save, not just diffs. |
| Intelligent production-ready defaults | When adding a Cloud SQL node, pre-fill: backups enabled, SSL required, insights on, deletion protection on. Reduce the "what do I configure?" burden. | Low | Pydantic model defaults already provide this partially. Design should specify "opinionated defaults" per node type that represent GCP best practices. |
| Resource cost annotations in editor | Show per-node estimated monthly cost as users design. See cost impact in real-time, not after deploy. | Medium | Requires GCP pricing data. Static lookup tables for common SKUs (Cloud Run per-request, Cloud SQL per-hour by tier) is simpler than pricing API integration. |
| Promotion preview with diff | Before promoting dev to staging, show what changes: new nodes, removed nodes, config differences. Users review before accepting. | Medium | Promotion exists but is blind (no preview). Design should specify a preview endpoint returning the delta between source and target blueprints. |
| Terraform plan preview with approval | Before deploying, run `terraform plan` and show execution plan. User approves before `apply`. Two-step deploy: plan then apply. | Medium | TF generation and Cloud Build exist. Design should specify: plan-only Cloud Build step, output parsing, approval flow, and plan-to-apply workflow. |

---

## Anti-Features

Features to explicitly NOT design for now. Each would derail the core platform design without proportional value.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Multi-cloud support (AWS, Azure) | Entire value prop is GCP abstraction. Multi-cloud 10x's design surface: every node type, TF template, IAM rule needs per-cloud variants. | Stay GCP-only. The constraint is a feature. |
| Custom Terraform modules | Letting users bring TF modules breaks the abstraction. Platform generates TF; users never see it. Modules have arbitrary complexity that cannot be validated. | Expose configuration knobs on node types. If users need something custom, add a new node type to the registry. |
| SQL schema migration execution | Executing DDL migrations (ALTER TABLE) is out of scope. Terraform cannot safely manage SQL schema drift -- this requires purpose-built migration tooling. | Document schemas in blueprint for code generation. `cloud_sql_table` nodes are documentation-only (per D-09). Recommend Flyway, Alembic, or similar for runtime migrations. |
| Kubernetes / GKE workloads | GKE adds enormous complexity: namespaces, RBAC, service mesh, pod scheduling, Helm charts. Would double the design surface. | Cloud Run covers containerized workloads. Cloud Functions covers event-driven. These serve the target audience (developers who don't want to manage infra). |
| CI/CD pipeline builder | Platform deploys infrastructure, not application code (except container image builds). Full CI/CD pipeline design is a separate product. | Container builds for compute nodes exist. Application-level CI/CD is the user's responsibility (GitHub Actions, Cloud Build triggers, etc.). |
| Real-time infrastructure monitoring | Dashboards, alerts, metrics, log aggregation. This is Cloud Monitoring/Logging's job, not the platform's. | Link to GCP Console for monitoring. Surface deploy status and basic health checks, not operational metrics. |
| Self-hosted deployment | Running the platform outside GCP. The platform IS GCP infrastructure orchestrating GCP. | Platform is SaaS on GCP. Self-hosting is not a use case. |
| Terraform state manipulation UI | `terraform import`, `state mv`, `state rm` via UI. State manipulation is dangerous and requires expert knowledge. | Platform owns the TF state lifecycle completely. State corruption requires support intervention. Users never touch state. |
| Custom IAM role definitions | GCP has 1000+ predefined roles. Custom roles add complexity for marginal benefit. | Use predefined GCP roles only. Map dependency types to the most appropriate predefined role. |
| Cross-environment VPC peering | Connecting dev to staging VPCs. Environments should be isolated by design. | Environments are intentionally isolated in separate GCP projects. Cross-env communication is an anti-pattern. |
| Real-time collaborative editing (CRDTs) | Multi-cursor editing with conflict resolution requires CRDT implementation -- massive complexity for a niche use case. | Single-writer with presence awareness (cursor tracking already exists in Firestore). Lock or warn on concurrent edits. |

---

## Feature Dependencies

```
Networking Architecture
  VPC Connector auto-wiring ──> Shared VPC host project design
  Private Service Connect ──> Shared VPC host project design
  IP address management ──> Shared VPC host project design
  DNS / service discovery ──> Shared VPC design + Database provisioning

Deploy Orchestration
  Incremental deploy ──> Deploy status tracking (exists)
  Rollback strategy ──> Deploy snapshots (exists) + Blueprint save history
  Concurrent deploy prevention ──> Deploy status tracking (exists)

IAM Design
  Auto-inferred IAM ──> Dependency graph (exists) + SA per compute node
  Cross-project IAM ──> Shared VPC design + Auto-inferred IAM
  User-overridable IAM ──> Auto-inferred IAM (must define base before overrides)

Database Lifecycle
  Connection string injection ──> Database provisioning (exists) + IAM (SA needs access roles)
  Schema management boundary ──> Database instance provisioning (exists)

Environment Management
  Blueprint promotion ──> Environment creation (exists)
  Env-specific config overlays ──> Blueprint promotion + Env creation
  Promotion preview ──> Blueprint promotion (exists)

Billing
  Stripe metered billing ──> Per-tenant GCP cost tracking (BigQuery export)
  Quota enforcement ──> Tenant management (partially exists)

Differentiators
  Drift detection ──> Deploy snapshots (exists) + TF state access via Cloud Build
  TF plan preview ──> Deploy orchestration + Cloud Build
  Per-node deploy status ──> Deploy snapshots (exists)
  Cost annotations ──> Resource pricing catalog (static or API)
```

---

## MVP Design Specification Priority

The design spec milestone should prioritize in this order based on dependency chains and implementation blocking:

### Priority 1: Must-Design First (blocks all implementation)

1. **Networking architecture** -- Shared VPC vs isolated, IPAM, VPC Connector auto-wiring, Private Service Connect. Every deploy that involves private connectivity depends on this being designed correctly. Currently the biggest unknown.
2. **Deploy orchestration** -- Incremental deploy semantics (full TF regen vs selective), rollback strategy, concurrent deploy prevention, Cloud Build lifecycle. This is the core action loop of the platform.
3. **IAM inference model** -- The complete mapping table: `{dependency edge type} -> {IAM role(s), binding scope}`. This is the core "magic" of the platform. Without it, auto-inferred IAM cannot be implemented.
4. **Database lifecycle** -- Connection string injection contract, schema management boundaries (what platform manages vs. documents), backup defaults. Defines how compute-to-data edges actually work at runtime.

### Priority 2: Should-Design (depends on Priority 1, enables core workflows)

5. **Environment-specific configuration** -- How config varies across envs (dev vs prod sizing). Without this, promotion from dev to prod produces identical infrastructure, which is never what users want.
6. **Resource lifecycle per node type** -- Document create/update/delete/immutable semantics for all 22 node types. Required for correctness of incremental deploys and drift detection.
7. **Billing pass-through** -- Stripe meter events, GCP billing export, cost attribution. Required for revenue but not for technical function.

### Priority 3: Can Defer (design in parallel with implementation)

8. **Drift detection** -- How and when to check live state against blueprint. Valuable but not blocking core deploy flow.
9. **Terraform plan preview** -- Two-step deploy (plan + approve + apply). Enhancement to existing deploy flow.
10. **Blueprint versioning** -- Activity log suffices for now; full snapshot versioning is a future enhancement.
11. **Cost estimation** -- Requires pricing data integration; complex and changes frequently. Nice-to-have.

---

## Sources

- GCP VPC best practices: [Google Cloud Architecture Center](https://cloud.google.com/architecture/best-practices-vpc-design)
- GCP Shared VPC multi-tenant design: [OneUptime - Multi-Tenancy on GCP](https://oneuptime.com/blog/post/2026-02-17-how-to-design-shared-infrastructure-multi-tenancy-with-tenant-isolation-on-gcp/view)
- GCP Network Planning Guide: [Networks.tools](https://networks.tools/learn/article/gcp-network-planning-guide)
- Terraform drift detection: [HashiCorp Developer](https://developer.hashicorp.com/terraform/tutorials/state/resource-drift)
- Terraform orchestration patterns: [Spacelift](https://spacelift.io/blog/terraform-orchestration)
- Terraform drift remediation: [Scalr Learning Center](https://scalr.com/learning-center/terraform-drift-detection-how-to-prevent-and-remediate/)
- Stripe usage-based billing: [Stripe Documentation](https://docs.stripe.com/billing/subscriptions/usage-based)
- Stripe metered billing implementation: [Stripe Pay-as-you-go Guide](https://docs.stripe.com/billing/subscriptions/usage-based/implementation-guide)
- IaC orchestration patterns 2025: [Firefly Academy](https://www.firefly.ai/academy/beyond-provisioning-a-2025-guide-to-infrastructure-orchestration-with-iac-and-gitops)
- Cloud deployment strategies: [Octopus Deploy](https://octopus.com/devops/cloud-deployment/)
- Existing codebase: `packages/core/` (schemas, registry, DAG, validation, TF generator), `packages/platform/` (deploy orchestrator, deploy service, store modules, GCP SDK wrappers), `packages/api/handlers/` (provision, promote, deploy, terraform)

---

*Feature landscape research: 2026-03-26*
