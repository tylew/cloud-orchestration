# Domain Pitfalls

**Domain:** GCP Infrastructure Orchestration Platform - Design Specification
**Researched:** 2026-03-26

## Critical Pitfalls

Mistakes that cause rewrites, security incidents, or fundamental design failures.

### Pitfall 1: Terraform State as Source of Truth

**What goes wrong:** Treating Terraform state as the authoritative record of what's deployed. State can drift from reality (manual changes in console, failed partial applies, state corruption).

**Why it happens:** Terraform's model assumes it is the sole manager of resources. In a multi-tenant platform where things can go wrong mid-deploy, state diverges from reality.

**Consequences:** `terraform plan` shows phantom changes or misses real drift. `terraform apply` may try to recreate existing resources (causing downtime) or miss changes that need to be applied.

**Prevention:** Blueprint snapshot in Firestore is the source of truth for "intended state." Terraform state is an implementation detail of the execution engine. Periodically reconcile with Cloud Asset Inventory API for actual GCP state. Never expose TF state to users.

**Detection:** Deploy failures that produce "resource already exists" errors. Resources in GCP that don't match blueprint.

### Pitfall 2: IAM Binding Accumulation (Zombie Permissions)

**What goes wrong:** When a dependency edge is removed from the blueprint (Cloud Run no longer reads from Cloud SQL), the corresponding IAM binding is never revoked.

**Why it happens:** IAM bindings are additive. If the platform only adds bindings on deploy and never removes them, permissions accumulate over time.

**Consequences:** Security violation -- services retain access to resources they no longer need. Violates principle of least privilege. Audit failures.

**Prevention:** The IAM inference engine must compute DESIRED IAM state (all current edges) and diff against APPLIED IAM state (from last deploy snapshot). Removed edges = IAM bindings to revoke. Generated TF must include the complete set of bindings, not just new ones. Terraform's declarative model handles removal IF the binding was in TF state.

**Detection:** Compare blueprint edges against actual IAM policy. `gcloud projects get-iam-policy` shows all current bindings.

### Pitfall 3: Cloud SQL Destroy-Recreate on Config Changes

**What goes wrong:** Certain Cloud SQL configuration changes (e.g., changing `database_version`, instance name, or `disk_type`) force Terraform to destroy and recreate the instance.

**Why it happens:** These are immutable GCP API fields. Terraform has no choice but to destroy+recreate. This destroys all data.

**Consequences:** Complete data loss for the Cloud SQL instance. In production, this is catastrophic.

**Prevention:** The design MUST document which config fields are mutable vs immutable for every node type. Immutable fields should be locked after first deploy (blueprint validation rejects changes to them). Add `prevent_destroy` lifecycle rule to all data resources in generated TF. Show clear warnings in the UI when a change would trigger recreate.

**Detection:** `terraform plan` will show `# forces replacement` for these changes. The platform must parse plan output and surface this to users before apply.

### Pitfall 4: Shared VPC Subnet Exhaustion

**What goes wrong:** CIDR ranges allocated to tenant subnets overlap, or the host VPC runs out of IP space.

**Why it happens:** Manual or poorly automated CIDR allocation. No tracking of which ranges are assigned to which tenants.

**Consequences:** Network creation fails. If overlapping ranges somehow get created, routing breaks unpredictably.

**Prevention:** Centralized CIDR allocator in Firestore. Atomic allocation (check-and-set) to prevent race conditions. Use /24 subnets minimum (254 hosts) per tenant -- leaves room for Cloud SQL private IPs, VPC connectors, etc. Plan for a /16 host VPC giving 256 /24 tenant subnets.

**Detection:** `google_compute_subnetwork` creation fails with CIDR overlap errors.

### Pitfall 5: Billing Export Lag Leading to Cost Surprises

**What goes wrong:** GCP billing export to BigQuery has up to 24-hour lag. Users see charges from yesterday, not today.

**Why it happens:** GCP does not provide real-time billing data at resource granularity. Billing export is batch-processed.

**Consequences:** Users may exceed budgets before the platform can warn them. Stripe invoices may not reflect current period usage accurately.

**Prevention:** Design billing as "best-effort, eventually consistent." Set clear expectations in UI. Use Billing Budget API for real-time alerting (less granular but near-real-time). Consider daily billing roll-up with a 48-hour reconciliation window.

**Detection:** Users complain about unexpected charges. Stripe invoices don't match GCP billing dashboard.

## Moderate Pitfalls

### Pitfall 1: Cloud Build Concurrent Build Limits

**What goes wrong:** Multiple tenants deploy simultaneously, exceeding the default 10 concurrent Cloud Build limit per project.

**Prevention:** Implement a deploy queue in Firestore. Rate-limit build submissions. Request quota increase proactively. Consider multiple Cloud Build regions to increase effective concurrency.

### Pitfall 2: Firestore Document Size Limits

**What goes wrong:** Blueprint envelopes or validation results exceed Firestore's 1MB document size limit.

**Prevention:** Already mitigated by sharding nodes into subcollections. Continue this pattern for any data structure that could grow (deploy logs, activity history). Design pagination for large collections.

### Pitfall 3: VPC Connector Throughput Limits

**What goes wrong:** Serverless VPC Access Connectors have throughput limits (100-1000 Mbps depending on machine type). Multiple Cloud Run services sharing one connector can saturate it.

**Prevention:** Design for one VPC connector per compute node, or at least per "throughput tier." Document connector sizing in resource lifecycle specs. Cloud Run v2 supports Direct VPC egress as an alternative to connectors -- evaluate this as it may eliminate the issue entirely.

### Pitfall 4: Terraform Provider Version Drift

**What goes wrong:** Platform generates TF with one Google provider version, but tenant state was created with an older version. Provider upgrades can introduce breaking changes.

**Prevention:** Pin the Google provider version in all generated TF. When upgrading, plan a migration: `terraform init -upgrade` + `terraform plan` across all tenant states. Never upgrade providers without testing against existing state.

### Pitfall 5: Environment Promotion with Incompatible Configs

**What goes wrong:** Promoting a dev blueprint to staging fails because dev uses a `db-f1-micro` Cloud SQL instance and staging's quotas or policies require `db-n1-standard-1`.

**Prevention:** Design promotion as "blueprint copy + environment overrides." Each environment has override configs (instance sizes, replica counts, min instances). Promotion copies the topology but applies env-specific sizing.

### Pitfall 6: Orphaned GCP Resources on Tenant Deletion

**What goes wrong:** When a tenant is deleted or a project is removed, GCP resources continue running and incurring costs.

**Prevention:** Design a cleanup pipeline: `terraform destroy` for all layers in reverse order, then GCP project deletion. Store cleanup state in Firestore. Require confirmation. Have a "grace period" before actual deletion. Track all provisioned resources independently of TF state (in case state is corrupted).

## Minor Pitfalls

### Pitfall 1: Cloud Run Cold Start Affecting Deploy Verification

**What goes wrong:** Post-deploy health checks fail because Cloud Run is cold-starting.

**Prevention:** Use Cloud Run startup probes. Don't treat the first failed health check as deploy failure. Design retry logic with exponential backoff.

### Pitfall 2: Firestore Index Limits

**What goes wrong:** Generated Firestore composite indexes for tenant databases hit the 200 composite index limit per database.

**Prevention:** Generate only essential indexes. Warn users when approaching limits. Document index budget in schema management design.

### Pitfall 3: Secret Manager Version Accumulation

**What goes wrong:** Every secret update creates a new version. Old versions accumulate, consuming quota (default 10,000 versions per secret).

**Prevention:** Design secret lifecycle to disable old versions after rotation. Set up automatic cleanup of disabled versions older than retention period.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Networking design | CIDR exhaustion, overlapping ranges | Automated allocator with atomic operations |
| Deploy ordering | Mid-deploy failures leaving partial state | Design rollback strategy per layer |
| IAM inference | Missing role mappings for edge cases | Exhaustive testing of all ActionType x NodeType combinations |
| Incremental deploy | Change detection misses (false negatives) | Conservative approach: when in doubt, include in change set |
| Database schema | Cloud SQL DDL failures leaving partial schema | Transactional migrations, pre-migration backup |
| Billing | Cost attribution to wrong tenant | Per-project cost filtering (projects are already per-tenant-per-env) |
| Multi-env lifecycle | Drift between environments after independent changes | Drift detection worker, visual diff in UI |
| Resource lifecycle | Destroy-recreate on immutable field changes | Lock immutable fields after first deploy, clear UI warnings |

## Sources

- [Terraform Resource Targeting Caveats](https://developer.hashicorp.com/terraform/tutorials/state/resource-targeting)
- [Cloud SQL Terraform Lifecycle](https://medium.com/google-cloud/managing-cloud-sql-resources-with-terraform-76cc044319e9)
- [GCP Shared VPC Documentation](https://cloud.google.com/vpc/docs/shared-vpc)
- [Stripe Billing Meters](https://docs.stripe.com/billing/subscriptions/usage-based)
- Existing codebase analysis: `packages/platform/deploy_orchestrator.py`, `packages/core/registry.py`

---

*Pitfalls research: 2026-03-26*
