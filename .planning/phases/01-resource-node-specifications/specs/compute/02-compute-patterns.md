# Compute Category: Shared Patterns

**Category:** Compute
**Types:** cloud_run, cloud_run_job, cloud_function
**Archetype:** Compute with Image

---

## Shared Compute Behaviors

All three compute types share these characteristics from the REGISTRY and schema definitions:

- **is_compute = True** in the component registry. This is unique to these three types.
- **Support internalGraph/workflow:** Compute types can define behavioral interfaces via `WorkflowDefinition` (structured references to databases, secrets, pub/sub, task queues, and other compute nodes) and `internalGraph` (step-by-step workflow visualization).
- **Part of GRAPH_TYPES:** All three are in the `GRAPH_TYPES` set, meaning they can carry behavioral step definitions.
- **Service account requirement:** All compute types require a `service_account` field at error severity. Every compute resource must run under a specific service account identity.

## Image / Source Lifecycle

The defining characteristic of the **Compute with Image** archetype is how code changes flow through the system:

### Container-Based (Cloud Run, Cloud Run Job)

1. User builds a container image (via Cloud Build or external CI).
2. The `image` field in the config references the container image URI (e.g., `gcr.io/project/image:tag`).
3. Updating the `image` field triggers a new **revision** -- the Cloud Run service or job creates a new revision with the new image. The old revision remains available.
4. For Cloud Run services, traffic can be split between revisions for gradual rollout.
5. The `image` field is mutable and revision-creating -- it is NOT ForceNew.

### Source-Based (Cloud Function)

1. User writes function source code.
2. Source is uploaded to GCS via the `CfSource` model (storage_source with bucket/object) or auto-derived by the platform pipeline (source_bucket/source_object fields).
3. Updating the source creates a new **function version**.
4. Only one version is active at a time (no traffic splitting for Cloud Functions).
5. The source fields are mutable -- uploading new source is the normal update path.

### Key Insight

The distinction between "mutable field update" and "revision-creating update" matters for UX:
- **Mutable field update**: Changes take effect on the existing revision/version (e.g., changing `min_instances` on Cloud Run).
- **Revision-creating update**: Changes create a new revision with the updated configuration. For Cloud Run, this includes ALL template fields (image, CPU, memory, env vars, etc.). Any template change = new revision.
- **ForceNew update**: Only identity fields (name, location) and a few Cloud Function-specific fields. These destroy and recreate the entire resource.

## Revision Model

### Cloud Run Service Revisions

- Every change to `template.*` fields creates a new revision.
- Revisions are immutable snapshots of the service configuration.
- Traffic can be split across multiple revisions using the `traffic` field (list of `CloudRunTraffic` entries).
- The default traffic routing sends 100% to the latest revision (`TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST`).
- Old revisions are retained and can receive traffic if configured.
- Revisions are named automatically by Cloud Run (e.g., `service-name-00001-abc`).

### Cloud Run Job Revisions

- Template changes create new job revisions.
- Job executions run against the latest revision.
- No traffic splitting concept -- jobs run to completion.
- Each execution creates tasks based on `task_count` and `parallelism`.

### Cloud Function Versions

- Source/config changes create a new function version.
- Only one version serves traffic at any time.
- No traffic splitting for individual Cloud Functions (traffic splitting happens at the Cloud Run service level that backs the 2nd gen function).

## Service Account Requirement

All compute types require a `service_account` field with error-level severity in REQUIRED_FIELDS:

- **cloud_run**: `service_account` (error) -- "Service account is required"
- **cloud_run_job**: `service_account` (error) -- "Service account is required"
- **cloud_function**: `service_account` (error) -- "Service account is required"

The service_account field should reference a `service_account` node in the blueprint. This creates an implicit dependency: the service account must be deployed before the compute resource. The validation module checks that `iam.service_account` references point to valid `service_account` nodes.

## VPC Access Patterns

Compute types need VPC access to reach private resources (Cloud SQL, Memorystore, etc.). Two patterns exist:

### Connector-Based VPC Access (Cloud Run, Cloud Run Job)

Uses the `CloudRunVpcAccess` model:
```
vpc_access:
  connector: "node:my-vpc-connector"  # Reference to a vpc_connector node
  egress: "PRIVATE_RANGES_ONLY"       # or "ALL_TRAFFIC"
```

The connector must be a `vpc_connector` node deployed in the same region. This is the traditional approach.

### Direct VPC Egress (Cloud Run only)

Uses the `CloudRunVpcAccessDirect` model:
```
vpc_access_direct:
  network: "my-vpc"
  subnetwork: "my-subnet"
  network_interfaces:
    - network: "my-vpc"
      subnetwork: "my-subnet"
      tags: ["allow-internet"]
```

Direct VPC egress connects the Cloud Run instance directly to the VPC without a connector. This avoids the VPC connector's throughput limitations and immutability constraints. Note: Direct VPC Egress model exists in the codebase but is not yet rendered in the `cloud_run.tf.j2` template.

### Cloud Function VPC Access

Uses simpler fields directly on the config:
```
vpc_connector: "node:my-vpc-connector"
vpc_connector_egress_settings: "PRIVATE_RANGES_ONLY"
```

Cloud Functions use the same connector-based approach but with flat fields instead of a nested model.

## Scaling Patterns

Each compute type has a different scaling model:

### Cloud Run Service Scaling

| Field | Default | Description |
|-------|---------|-------------|
| min_instances | 0 | Minimum running instances (0 = scale to zero) |
| max_instances | 100 | Maximum running instances |
| max_concurrent_requests | 80 | Requests per instance before scaling out |
| cpu_idle | true | Whether CPU is allocated only during request processing |
| startup_cpu_boost | false | Temporarily increase CPU during startup |

Cloud Run scales based on concurrent requests. When `cpu_idle=true`, CPU is throttled between requests (cost savings). When `cpu_idle=false`, CPU is always allocated (needed for background processing).

### Cloud Run Job Scaling

| Field | Default | Description |
|-------|---------|-------------|
| task_count | 1 | Total number of tasks to run |
| parallelism | 1 | Maximum tasks running simultaneously |
| max_retries | 3 | Retries per failed task |

Jobs run a fixed number of tasks. Parallelism controls how many run concurrently. This is batch processing, not request-based scaling.

### Cloud Function Scaling

| Field | Default | Description |
|-------|---------|-------------|
| min_instances | 0 | Minimum warm instances |
| max_instances | 100 | Maximum concurrent instances |
| max_concurrent_requests | 1 | Requests per instance (default 1 for functions) |

Cloud Functions scale per-invocation by default (`max_concurrent_requests=1`). Increasing concurrency allows a single instance to handle multiple requests, similar to Cloud Run.

## Archetype Differentiation

The **Compute with Image** archetype differs from **Simple CRUD** in exactly one way: the update path for image/source changes.

- **Simple CRUD:** Field is either mutable (in-place update) or ForceNew (destroy-recreate). No middle ground.
- **Compute with Image:** Image/source and template fields have a third update path -- **revision-creating**. The resource is not destroyed. Instead, a new revision/version is created alongside the existing one. This is the normal deployment flow for compute resources.

This distinction matters for:
1. **Deploy engine:** Compute deploys should expect revision creation, not in-place updates for most config changes.
2. **Rollback:** Cloud Run services can roll back by shifting traffic to a previous revision. Cloud Functions can only roll back by redeploying previous source.
3. **UX:** Users should understand that changing CPU/memory on a Cloud Run service creates a new revision, even though it feels like an "in-place" config change.

---

*References: [01-compute-template.md](01-compute-template.md), [00-lifecycle-archetypes.md](../00-lifecycle-archetypes.md)*
*Phase: 01-resource-node-specifications*
