# Architecture Patterns for Design Specification

**Domain:** GCP Infrastructure Orchestration Platform
**Researched:** 2026-03-26

## Recommended Architecture for Design Phase

The platform already has a working architecture (stateless FastAPI + Firestore + Cloud Build). The design specification needs to formalize subsystem boundaries and interaction patterns for the areas that are currently ad-hoc or unbuilt.

### Subsystem Map

```
+---------------------------------------------------+
|  PLATFORM HOST PROJECT                             |
|                                                    |
|  +-------------+  +-------------+  +------------+ |
|  | FastAPI API  |  | Cloud Build |  | Billing    | |
|  | (Cloud Run)  |  | (TF Runner) |  | Worker     | |
|  +------+------+  +------+------+  +-----+------+ |
|         |                |               |         |
|  +------+----------------+---------------+------+  |
|  |              Firestore                       |  |
|  |  (Blueprints, Projects, Deploy State,        |  |
|  |   Tenant Config, CIDR Allocations)           |  |
|  +----------------------------------------------+  |
|                                                    |
|  +----------------------------------------------+  |
|  |           Shared VPC (Host Network)          |  |
|  |  +--------+  +--------+  +--------+         |  |
|  |  |Subnet A|  |Subnet B|  |Subnet C|  ...    |  |
|  |  |(Tenant1)|  |(Tenant2)|  |(Tenant3)|       |  |
|  +--+--------+--+--------+--+--------+---------+  |
+---------------------------------------------------+
         |              |              |
    +----+----+    +----+----+    +----+----+
    | Tenant 1|    | Tenant 2|    | Tenant 3|
    | GCP Proj|    | GCP Proj|    | GCP Proj|
    | (Service|    | (Service|    | (Service|
    |  Project)|   |  Project)|   |  Project)|
    +---------+    +---------+    +---------+
```

### Component Boundaries

| Component | Responsibility | Communicates With | State |
|-----------|---------------|-------------------|-------|
| Blueprint Engine | Validation, DAG operations, change detection | API Layer, TF Generator | Reads from Firestore |
| TF Generator | Jinja2 template rendering, layered file output | Blueprint Engine, Cloud Build Submitter | Stateless (reads blueprint, writes files) |
| Deploy Orchestrator | Coordinates TF generation -> Cloud Build -> status tracking | TF Generator, Cloud Build API, Firestore | Writes deploy status to Firestore |
| IAM Inference Engine | Computes IAM bindings from dependency edges + action types | Blueprint Engine, TF Generator | Stateless (pure function of graph) |
| Network Allocator | CIDR range management, subnet assignment | Provisioning Service, TF Generator | Reads/writes CIDR state in Firestore |
| Schema Migration Runner | Post-TF schema DDL execution | Deploy Orchestrator, Cloud Build | Reads schema definitions from blueprint |
| Billing Aggregator | BigQuery cost query -> Stripe meter events | BigQuery, Stripe API, Firestore | Reads billing data, writes invoice state |
| Drift Detector | Compares blueprint desired state vs actual GCP state | Cloud Asset Inventory API, Firestore | Reads both sources, writes drift reports |

### Data Flow: Deploy Pipeline (Expanded)

The current deploy flow is: generate TF -> submit Cloud Build -> poll -> done. The design specification must expand this to handle layered deploys, IAM, and schema migrations.

```
1. User triggers deploy for env "dev"
2. API loads blueprint from Firestore
3. Blueprint Engine:
   a. Validates blueprint (zero errors required)
   b. Computes DAG topological sort
   c. Computes change set (diff vs last deployed blueprint)
   d. Determines affected layers (network? compute? data? IAM?)
4. IAM Inference Engine:
   a. Walks dependency edges
   b. Maps ActionType -> GCP IAM role per edge
   c. Computes desired IAM bindings
   d. Diffs vs previously deployed IAM bindings
5. TF Generator:
   a. Generates layered TF files:
      - 00-network.tf (VPC, subnets, connectors, NAT)
      - 01-data.tf (Cloud SQL instances, Firestore DBs, BigQuery datasets)
      - 02-iam.tf (Service accounts, role bindings)
      - 03-compute.tf (Cloud Run, Functions, with VPC connector refs)
      - 04-messaging.tf (Pub/Sub, Cloud Tasks)
      - 05-schema.tf (BigQuery tables, Cloud SQL databases)
   b. Only generates files for affected layers
6. Deploy Orchestrator:
   a. Uploads TF to GCS
   b. Submits Cloud Build with targeted layers
   c. Cloud Build runs: init -> plan -> apply per layer, in order
   d. If data layer deployed: run schema migrations (Cloud SQL DDL)
   e. Polls status, updates Firestore
7. Post-deploy:
   a. Snapshot deployed blueprint state
   b. Record per-node deploy versions
   c. Update environment status
```

## Patterns to Follow

### Pattern 1: Layered Terraform State

**What:** Separate Terraform state files per resource category within each tenant environment.

**When:** Always. Every tenant environment gets layered state.

**Structure:**
```
gs://{tf-bucket}/{tenant-id}/{env-name}/
  network/terraform.tfstate
  data/terraform.tfstate
  iam/terraform.tfstate
  compute/terraform.tfstate
  messaging/terraform.tfstate
```

**Why:** Reduces blast radius. Network changes cannot accidentally destroy compute resources. Enables incremental deploys -- only apply layers with changes.

### Pattern 2: IAM Inference from Dependency Graph

**What:** Automatically derive IAM bindings from the blueprint's dependency edges and action types.

**When:** Every time a blueprint is saved or deployed.

**Inference rules (examples):**
```
Edge: CloudRun "api" --[Read]--> CloudSQL "db"
  => google_project_iam_member {
       member = serviceAccount:${sa-api}
       role   = "roles/cloudsql.client"
     }

Edge: CloudRun "api" --[Emit]--> PubSubTopic "events"
  => google_pubsub_topic_iam_member {
       topic  = ${topic-events}
       member = serviceAccount:${sa-api}
       role   = "roles/pubsub.publisher"
     }

Edge: CloudRun "api" --[Read]--> SecretManager "api-key"
  => google_secret_manager_secret_iam_member {
       secret = ${secret-api-key}
       member = serviceAccount:${sa-api}
       role   = "roles/secretmanager.secretAccessor"
     }
```

**Data structure:** The registry already has `iam_scope` and `iam_terraform_resource` per node type. Extend with an `ACTION_TO_ROLE` mapping:

```python
ACTION_TO_ROLE: dict[tuple[ActionType, NodeType], str] = {
    (ActionType.READ, NodeType.CLOUD_SQL): "roles/cloudsql.client",
    (ActionType.WRITE, NodeType.CLOUD_SQL): "roles/cloudsql.client",
    (ActionType.READ, NodeType.FIRESTORE): "roles/datastore.user",
    (ActionType.WRITE, NodeType.FIRESTORE): "roles/datastore.user",
    (ActionType.READ, NodeType.GCS_BUCKET): "roles/storage.objectViewer",
    (ActionType.WRITE, NodeType.GCS_BUCKET): "roles/storage.objectCreator",
    (ActionType.READ, NodeType.BIGQUERY): "roles/bigquery.dataViewer",
    (ActionType.WRITE, NodeType.BIGQUERY): "roles/bigquery.dataEditor",
    (ActionType.INVOKE, NodeType.CLOUD_RUN): "roles/run.invoker",
    (ActionType.INVOKE, NodeType.CLOUD_FUNCTION): "roles/cloudfunctions.invoker",
    (ActionType.EMIT, NodeType.PUBSUB_TOPIC): "roles/pubsub.publisher",
    (ActionType.ENQUEUE, NodeType.CLOUD_TASK_QUEUE): "roles/cloudtasks.enqueuer",
    (ActionType.READ, NodeType.SECRET_MANAGER): "roles/secretmanager.secretAccessor",
    (ActionType.READ, NodeType.BIGTABLE): "roles/bigtable.reader",
    (ActionType.WRITE, NodeType.BIGTABLE): "roles/bigtable.user",
}
```

### Pattern 3: Resource State Machine

**What:** Every resource in the blueprint has a lifecycle state machine.

**States:**
```
PENDING -> PROVISIONING -> READY -> DEPLOYING -> DEPLOYED -> MODIFYING -> DEPLOYED
                |                      |              |
                v                      v              v
             FAILED              DEPLOY_FAILED    MODIFY_FAILED
```

**When:** For design specs, every resource type must document which state transitions are valid, what triggers each transition, and what happens on failure.

### Pattern 4: Change Set Computation

**What:** Before each deploy, compute the minimal set of changes by diffing current blueprint against last deployed blueprint.

**Algorithm:**
```
1. Load current blueprint (from Firestore)
2. Load last deployed blueprint snapshot (from Firestore)
3. For each node in current:
   a. If not in previous: ADDED
   b. If config/dependencies changed: MODIFIED
   c. If unchanged: UNCHANGED
4. For each node in previous but not current: REMOVED
5. Group changes by layer (network, data, IAM, compute, messaging)
6. Only deploy layers with changes
7. Within each layer, use -target for specific modified resources
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Monolithic Deploy

**What:** Applying all Terraform in a single `terraform apply` regardless of what changed.
**Why bad:** Slow deploys, large blast radius, unnecessary API calls to GCP for unchanged resources. At 20+ resources, full plan/apply takes minutes even with no changes.
**Instead:** Layered state files + change set computation + targeted apply.

### Anti-Pattern 2: IAM at Project Level for Everything

**What:** Granting all IAM roles at the project level (`google_project_iam_member`).
**Why bad:** Over-permissive. A Cloud Run service that needs to read one specific GCS bucket gets `roles/storage.objectViewer` on ALL buckets in the project.
**Instead:** Use resource-level IAM (`google_storage_bucket_iam_member`, `google_pubsub_topic_iam_member`) whenever the resource supports it. The registry's `iam_scope` field already distinguishes "resource" vs "project" scope.

### Anti-Pattern 3: Terraform for Schema DDL

**What:** Using Terraform to manage Cloud SQL table schemas (CREATE TABLE, ALTER TABLE).
**Why bad:** Terraform's lifecycle model (desired state reconciliation) does not handle data migrations. ALTER TABLE with data transformation is not expressible in HCL. Terraform destroy of a table = data loss.
**Instead:** Generate SQL migration files. Execute via Cloud Build step post-infrastructure-deploy. Track migration version in Firestore.

### Anti-Pattern 4: Shared Terraform State Across Tenants

**What:** Multiple tenants sharing a single state file or state bucket without isolation.
**Why bad:** State file corruption, lock contention, information leakage (one tenant could see another's resource IDs).
**Instead:** `gs://{tf-bucket}/{tenant-id}/{env-name}/{layer}/terraform.tfstate` -- complete isolation at the GCS object level.

## Scalability Considerations

| Concern | At 10 tenants | At 100 tenants | At 1000 tenants |
|---------|---------------|----------------|-----------------|
| Cloud Build concurrency | No issue (10 concurrent builds) | May hit quota (default 10 concurrent builds per project) | Need quota increase or build queue. Design a deploy queue in Firestore. |
| Shared VPC subnet allocation | Manual CIDR ranges fine | Need automated CIDR allocator | Need CIDR pool management with reclamation on tenant deletion |
| Firestore read/write volume | Negligible | Moderate (real-time listeners per tenant) | May need Firestore database sharding or read replicas |
| TF state file size | Small (<100KB per state) | Still small individually | Fine -- GCS handles millions of objects |
| Billing export processing | Small BigQuery queries | Moderate queries | Need partitioned/clustered BigQuery tables, batch processing |
| GCP API quotas | Default quotas sufficient | May need quota increases for Compute API, IAM API | Need quota monitoring and per-tenant rate limiting |

## Sources

- Existing codebase analysis: `packages/core/dag.py`, `packages/core/registry.py`, `packages/platform/deploy_orchestrator.py`
- [GCP Shared VPC Documentation](https://cloud.google.com/vpc/docs/shared-vpc)
- [Terraform State Management at Scale](https://www.stackguardian.io/post/terraform-state-management-at-scale-strategies-for-enterprise-environments)
- [Terraform Resource Targeting](https://developer.hashicorp.com/terraform/tutorials/state/resource-targeting)
- [Cloud Run IAM Roles](https://cloud.google.com/run/docs/reference/iam/roles)

---

*Architecture research: 2026-03-26*
