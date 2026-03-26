# Technology Stack for Design Specification

**Project:** GCP Orchestration Platform - System Design Phase
**Researched:** 2026-03-26

## Context

This is not a greenfield stack selection. The platform has an existing stack (FastAPI, React, Firestore, Terraform/Jinja2, Cloud Build). This research identifies the GCP APIs, design patterns, specification standards, and reference architectures needed for the **design specification milestone** -- the theoretical framework that makes implementation mechanical.

## Recommended Stack Additions for Design Phase

### GCP APIs and Services (Design Targets)

| Technology | Version/API | Purpose | Why |
|------------|-------------|---------|-----|
| Shared VPC | Compute API v1 | Host-project networking for tenant isolation | Google's recommended multi-tenant network model. Platform owns network centrally; tenant projects attach as service projects. Avoids per-tenant VPC sprawl. |
| VPC Service Controls | Access Context Manager API | Data exfiltration prevention | Adds perimeter-based isolation on top of project-level isolation. Required for enterprise tenants handling sensitive data. |
| Cloud SQL Auth Proxy | v2 | Secure database connectivity from Cloud Run | Eliminates public IP exposure for SQL instances. Works with IAM-based auth, no password management needed. |
| GCP Billing Export | BigQuery Export | Per-tenant cost tracking | Only reliable way to get granular GCP cost data. Export to BigQuery, query per-project costs, feed to Stripe meters. |
| Cloud Asset Inventory | v1 | Drift detection, resource auditing | Provides actual-state view of tenant resources independent of Terraform state. Enables drift detection between blueprint and reality. |
| Recommender API | v1 | IAM right-sizing | Google ML-based recommendations for removing unused permissions. Post-deploy optimization of auto-inferred IAM. |

**Confidence:** HIGH -- these are all GA GCP services with stable APIs.

### Terraform Patterns (Generation Strategy)

| Pattern | Implementation | Purpose | Why |
|---------|---------------|---------|-----|
| Layered State Files | Separate `.tf` per resource layer | Incremental deploys | Network resources change rarely; compute changes often. Separate state files enable targeted `terraform apply` per layer without risking stable infrastructure. |
| `terraform plan -target` | Module-level targeting | Selective resource deployment | For second+ deploys, only target modules containing changed resources. The DAG already computes `parallel_batches()` -- extend to compute change sets. |
| `terraform_remote_state` data source | Cross-stack references | Layer interdependency | Network layer outputs (VPC ID, subnet IDs) consumed by compute layer via remote state. Enables independent state management per layer. |
| State locking via GCS | GCS backend with locking | Concurrent deploy safety | Already using GCS for TF source tarballs. Add state backend with object versioning for rollback capability. |
| `prevent_destroy` lifecycle | On critical resources | Protect databases and networking | Cloud SQL, VPC, and Firestore instances should never be accidentally destroyed. Add lifecycle rules in generated TF. |

**Confidence:** HIGH -- standard Terraform patterns, well-documented by HashiCorp.

### IAM Inference Model

| Component | Technology | Purpose | Why |
|-----------|-----------|---------|-----|
| Dependency graph analysis | Existing `BlueprintDAG` + `ACTION_VALID_TARGETS` | Auto-infer IAM bindings from edges | The platform already has `ActionType` (Read, Write, Invoke, Emit, Enqueue) mapped to valid node types. Each action type maps to specific GCP IAM roles. This is the core inference engine. |
| Per-service-account scoping | `google_service_account` per compute node | Workload identity | Each Cloud Run/Function gets its own SA. Never use default compute SA -- violates least privilege. Already in registry as `SERVICE_ACCOUNT` node type. |
| Role mapping table | Static config (not API) | Action-to-role translation | `ActionType.READ` on `CLOUD_SQL` -> `roles/cloudsql.client`. `ActionType.INVOKE` on `CLOUD_RUN` -> `roles/run.invoker`. Deterministic, auditable mapping. |
| IAM diff on redeploy | Compare previous vs current bindings | Prevent permission accumulation | When edges are removed from the graph, corresponding IAM bindings must be revoked. Track "desired state" vs "applied state". |

**Confidence:** HIGH for the pattern, MEDIUM for completeness of role mappings (need to verify every node type's IAM roles against current GCP docs).

### Database Schema Lifecycle

| Component | Technology | Purpose | Why |
|-----------|-----------|---------|-----|
| Schema definition in blueprint | Existing child node types (`cloud_sql_table`, `firestore_collection`, `bigquery_table`) | Declarative schema | Users define tables/collections as child nodes with field definitions. Already partially implemented. |
| Schema migration for Cloud SQL | Generated SQL DDL (not Terraform) | DDL lifecycle management | Terraform manages Cloud SQL *instances* and *databases*, but table schemas should be managed via SQL migrations. Terraform's `google_sql_database` does not handle table DDL. Use Cloud Build steps to run migrations post-instance-creation. |
| Firestore schema (schemaless) | Index generation + security rules | Firestore lifecycle | Firestore is schemaless -- "schema" means composite indexes and security rules. Generate `firestore.indexes.json` and `firestore.rules` from collection definitions. |
| BigQuery schema | Terraform `google_bigquery_table` | Table DDL via TF | Unlike Cloud SQL, BigQuery table schemas ARE managed well by Terraform. Column definitions map directly to TF resource attributes. |

**Confidence:** HIGH -- separation of instance provisioning (Terraform) from schema management (migration scripts) is the industry standard.

### Billing Pass-Through

| Component | Technology | Purpose | Why |
|-----------|-----------|---------|-----|
| GCP Billing Export | BigQuery dataset in host project | Raw cost data | GCP exports detailed billing to BigQuery. Filter by `project.id` to get per-tenant costs. |
| Stripe Billing Meters | Stripe Meters API (2025+) | Usage-based invoicing | Stripe's meter-based billing (required since API version 2025-03-31.basil) is purpose-built for infrastructure pass-through. Send usage events with tenant and resource dimensions. |
| Cost aggregation worker | Cloud Run Job (scheduled) | Periodic cost rollup | Daily/weekly Cloud Run Job queries BigQuery billing export, aggregates per-tenant costs, sends meter events to Stripe. |
| Markup configuration | Firestore tenant config | Per-tenant pricing | Store markup percentage per tenant. Apply on top of raw GCP costs when sending to Stripe. |

**Confidence:** MEDIUM -- the GCP-to-Stripe pipeline is straightforward, but billing export lag (up to 24 hours) and cost attribution granularity need validation.

### Networking Architecture

| Component | Technology | Purpose | Why |
|-----------|-----------|---------|-----|
| Shared VPC Host Project | Platform's host GCP project | Centralized network ownership | Platform controls all networking. Tenants never touch VPC config directly. Host project owns VPCs, subnets, firewall rules. |
| Per-tenant subnet allocation | CIDR range management in Firestore | IP space isolation | Each tenant gets a subnet from a managed CIDR pool. Prevents IP conflicts. Enables network-level isolation without separate VPCs. |
| Serverless VPC Access Connector | `google_vpc_access_connector` | Cloud Run -> private resources | Required for Cloud Run services to reach Cloud SQL, Memorystore, or other VPC-internal resources. Already a node type in registry. |
| Private Service Connect | `google_compute_global_forwarding_rule` | Cross-project private connectivity | For tenant Cloud Run services connecting to shared platform services (if needed). More secure than VPC peering. |
| Cloud NAT | `google_compute_router_nat` | Outbound internet for VPC resources | Tenant resources in private subnets need NAT for outbound traffic (pulling dependencies, calling external APIs). |

**Confidence:** HIGH for Shared VPC pattern. MEDIUM for whether PSC is needed (depends on cross-project connectivity requirements).

## Design Specification Standards

### What Format to Write Specs In

| Standard | Use For | Why |
|----------|---------|-----|
| Sequence diagrams (Mermaid) | Deploy flows, provisioning flows, IAM inference | Shows temporal ordering and actor interactions. Mermaid renders in GitHub markdown. |
| Data model diagrams | Firestore schema evolution, Terraform state structure | Shows entity relationships and cardinality. |
| Decision records (ADR format) | Key architecture decisions | "Context, Decision, Consequences" format forces rigorous thinking. Each design question gets a numbered ADR. |
| State machine diagrams | Resource lifecycle, deploy status, provisioning status | Resources have clear states (pending, provisioning, ready, deploying, deployed, failed). State machines prevent invalid transitions. |
| Interface contracts (Pydantic models) | API boundaries between subsystems | Pydantic models serve as executable specifications. Define the contract, implementation follows. |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Network isolation | Shared VPC | Separate VPC per tenant | VPC sprawl, quota limits (max 15 VPC networks per project without quota increase), operational overhead. Shared VPC gives isolation via subnets + firewall rules with centralized management. |
| Schema migration | SQL DDL via Cloud Build | Terraform `null_resource` with provisioner | Terraform provisioners are a last resort per HashiCorp docs. Fragile, no rollback, no idempotency guarantees. Dedicated migration steps in Cloud Build are testable and repeatable. |
| State management | Layered state per resource category | Single monolithic state file | Monolithic state means every deploy touches all resources. Blast radius is unbounded. Layered state isolates network from compute from data. |
| Cost tracking | BigQuery billing export | Cloud Billing API direct queries | API is for real-time billing info but lacks the granularity and historical depth of BigQuery export. Export is the canonical approach for cost analytics. |
| IAM management | Auto-inferred from graph + user override | Manual IAM configuration only | Manual-only defeats the platform's value proposition. Users should not need to understand GCP IAM. Auto-inference from dependency edges is deterministic and auditable. |
| Incremental deploy | Blueprint diff + targeted TF apply | Full TF apply every time | Full apply is safe but slow and wasteful. With 20+ resources, unchanged infrastructure should not be re-evaluated. Diff-based targeting reduces deploy time and blast radius. |

## GCP API Versions to Target

```
# These are the current GA API versions to reference in design specs
google-cloud-compute v1 (Shared VPC, VPC, subnets, firewall)
google-cloud-sql v1 (Cloud SQL instances, databases, users)
google-cloud-run v2 (Cloud Run services and jobs -- already using v2 resources)
google-cloud-functions v2 (Cloud Functions 2nd gen -- already using)
google-cloud-pubsub v1 (Topics, subscriptions, schemas)
google-cloud-bigquery v2 (Datasets, tables, jobs)
google-cloud-bigtable admin v2 (Instances, tables)
google-cloud-iam v1 (Roles, service accounts, policy bindings)
google-cloud-billing v1 (Billing accounts, budget API)
google-cloud-asset v1 (Asset inventory, feeds)
google-cloud-recommender v1 (IAM recommender)
```

**Confidence:** HIGH -- all GA APIs.

## What NOT to Do

| Anti-Pattern | Why Not | What Instead |
|-------------|---------|--------------|
| GKE for tenant workloads | Massive operational overhead, cost, complexity. The platform targets serverless-first users. | Cloud Run + Cloud Functions cover all compute needs. |
| Terraform Cloud/Enterprise | Adds vendor lock-in and cost on top of GCP. Platform already manages TF execution via Cloud Build. | Continue with Cloud Build + GCS state backend. Self-managed TF execution gives full control over the deploy pipeline. |
| Pulumi or CDK for TF | Would require rewriting the entire Jinja2 template system. Existing templates work and are debuggable. | Keep Jinja2 templates. They produce readable HCL that users could inspect if needed. |
| VPC peering for tenant connectivity | VPC peering is non-transitive, has a 25-peer limit, and creates routing complexity at scale. | Shared VPC with subnets, or Private Service Connect for cross-project connectivity. |
| Managing Cloud SQL passwords in Terraform | Passwords in state files are a security risk. | Use Cloud SQL IAM authentication. Compute service accounts get `roles/cloudsql.client` and authenticate via IAM, no passwords needed. |
| Single Terraform state for all tenant resources | One tenant's broken state blocks all deploys. State file corruption affects everyone. | Per-tenant, per-environment state files in GCS. Complete blast radius isolation. |

## Sources

- [GCP VPC Design Best Practices](https://docs.google.com/architecture/best-practices-vpc-design) - HIGH confidence
- [GCP Shared VPC Documentation](https://cloud.google.com/vpc/docs/shared-vpc) - HIGH confidence
- [Terraform Resource Targeting](https://developer.hashicorp.com/terraform/tutorials/state/resource-targeting) - HIGH confidence
- [Cloud Run IAM Roles](https://docs.google.com/run/docs/reference/iam/roles) - HIGH confidence
- [GCP IAM Roles Overview](https://cloud.google.com/iam/docs/roles-overview) - HIGH confidence
- [Stripe Usage-Based Billing](https://docs.stripe.com/billing/subscriptions/usage-based) - HIGH confidence
- [Stripe Billing Meters Migration](https://docs.stripe.com/billing/subscriptions/usage-based-legacy/migration-guide) - HIGH confidence
- [Atlas Cloud SQL Schema Migrations](https://atlasgo.io/guides/deploying/cloud-sql-via-github-actions) - MEDIUM confidence
- [Terraform State Splitting](https://support.hashicorp.com/hc/en-us/articles/7955227415059-How-to-Split-State-Files) - HIGH confidence
- [GCP Project-Per-Tenant Multi-Tenancy](https://oneuptime.com/blog/post/2026-02-17-how-to-implement-project-per-tenant-multi-tenancy-on-google-cloud-platform/view) - MEDIUM confidence
- [HashiCorp Project Infragraph](https://newsroom.ibm.com/2025-09-25-hashicorp-previews-the-future-of-agentic-infrastructure-automation-with-project-infragraph) - LOW confidence (future/preview)

---

*Stack research: 2026-03-26*
