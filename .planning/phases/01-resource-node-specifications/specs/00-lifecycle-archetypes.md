# Lifecycle Archetypes

**Purpose:** Shared lifecycle definitions referenced by all category-level specification documents.
**Provider version:** Google Terraform Provider ~5.0
**Last verified:** 2026-03-26

All node types in the platform map to one of four lifecycle archetypes (or a special non-Terraform case). Each archetype defines a state machine, update semantics, and failure behavior. Individual category specs reference these archetypes rather than repeating the same state machine tables.

---

## Platform State Machine (Shared)

All Terraform-backed archetypes share this state machine. States are platform-level only (per D-03). GCP internal intermediate states are not modeled.

| Current State | Event | Next State | Notes |
|---------------|-------|------------|-------|
| (none) | create | draft | Initial node creation in blueprint |
| draft | deploy | deploying | TF apply submitted via Cloud Build |
| deploying | success | deployed | TF apply completed successfully |
| deploying | failure | failed | TF apply errored |
| deployed | update (mutable) | updating | In-place TF apply for mutable field changes |
| deployed | update (immutable) | destroying | Destroy-recreate cycle for ForceNew field changes |
| updating | success | deployed | In-place update completed |
| updating | failure | failed | Update errored |
| deployed | delete | destroying | TF destroy submitted |
| destroying | success | destroyed | Resource removed from GCP |
| destroying | failure | failed | Destroy errored |
| failed | retry | deploying/updating/destroying | Recovery design deferred to Phase 3-5 (per D-04) |

**Failure behavior (D-04):** Failure is possible on any asynchronous transition (deploying, updating, destroying). The platform marks the node as `failed` and records the error. Recovery mechanisms (retry with backoff, manual intervention, rollback) are deferred to deploy engine phases (Phase 3-5). Phase 1 documents only that failure is possible, not how to recover.

---

## Archetype 1: Simple CRUD

**Applies to:** service_account, secret_manager, gcs_bucket, pubsub_schema, pubsub_topic, pubsub_subscription, cloud_task_queue, bigquery, bigtable

**State machine:** Uses the shared platform state machine above without modification.

**Update semantics:**
- **Mutable fields:** Changed in-place via `terraform apply`. The resource is updated without recreation. Transition: deployed -> updating -> deployed.
- **Immutable fields (ForceNew):** Changing a ForceNew field triggers Terraform's destroy-then-create cycle. The platform must warn users that this operation will briefly destroy the resource. Transition: deployed -> destroying -> (auto-recreate) -> deploying -> deployed.

**Delete semantics:** `terraform destroy` removes the resource from GCP. The platform transitions the node to `destroyed`.

**Key characteristic:** These resources have straightforward CRUD lifecycles. Most fields are mutable. Typically only 1-3 fields are ForceNew (usually identity fields like `name` or `location`).

---

## Archetype 2: Compute with Image

**Applies to:** cloud_run, cloud_run_job, cloud_function

**State machine:** Uses the shared platform state machine above, but with a critical nuance in update behavior.

**Update semantics -- the key differentiator from Simple CRUD:**
- **Container image / source code changes** create new **revisions** (Cloud Run, Cloud Run Job) or **versions** (Cloud Function) WITHOUT destroying the resource. This is the defining characteristic. The image/source field is mutable and revision-creating, not ForceNew.
- **Template/config changes** (CPU, memory, env vars, scaling, etc.) also create new revisions for Cloud Run/Job. For Cloud Function, most service_config fields are updated in-place.
- **True ForceNew fields** are limited to identity fields: `name` and `location` for all three types, plus `build_config.docker_repository`, `build_config.worker_pool`, `event_trigger.event_type`, and `event_trigger.trigger_region` for Cloud Function.
- The `update (immutable)` transition in the state machine applies ONLY to true ForceNew fields, NOT to image/source changes.

**Revision model:**
- **Cloud Run:** Every template change creates a new revision. Traffic can be split across revisions (gradual rollout). Old revisions are retained.
- **Cloud Run Job:** Template changes create new job revisions. Executions run against the latest revision.
- **Cloud Function:** Source/config changes create a new version. Only one version is active at a time.

**Delete semantics:** Same as Simple CRUD -- `terraform destroy` removes the resource.

**Key characteristic:** These are the only `is_compute=True` types. They support `internalGraph`/`workflow` definitions. The revision-creating update path is what separates them from Simple CRUD.

---

## Archetype 3: Parent-Child Composite

**Applies to:**
- cloud_sql (children: cloud_sql_database, cloud_sql_table)
- firestore (children: firestore_collection)
- bigquery (children: bigquery_table)

**State machine:** Parent uses the shared platform state machine. Children have a coupled lifecycle.

**Parent-child coupling:**
- Deleting a parent cascades deletion to all children.
- Children cannot exist without their parent.
- Children reference their parent via `parentRef` (slug of the parent node).

**Child Terraform resource status:**

| Child Type | Has Own TF Resource | TF Resource Name | Notes |
|------------|-------------------|------------------|-------|
| cloud_sql_database | Yes | google_sql_database | Independent TF resource, but lifecycle tied to parent instance |
| cloud_sql_table | No | (platform-only) | Schema metadata stored in Firestore only |
| firestore_collection | No | (platform-only) | Collections are implicit in Firestore; no TF resource |
| bigquery_table | Yes | google_bigquery_table | Independent TF resource within the dataset |

**Update semantics:**
- Parent follows Simple CRUD update rules.
- Children with TF resources follow Simple CRUD update rules independently (but deletion cascades from parent).
- Platform-only children (firestore_collection, cloud_sql_table) are always mutable -- they exist only in Firestore.

**Key characteristic:** The parent-child hierarchy creates deployment ordering constraints. Parents must be deployed before children. This has implications for the deploy engine (Phase 3-5).

---

## Archetype 4: Network with Dependencies

**Applies to:** vpc, subnet, vpc_connector, external_lb

**State machine:** Uses the shared platform state machine above without modification.

**Update semantics:**
- Same as Simple CRUD for field-level mutability.
- **Critical difference:** Other resources depend on network resources. Deletion requires checking for dependents first. A VPC cannot be deleted if subnets still reference it. A subnet cannot be deleted if compute resources use it.

**Dependency ordering:**
- VPC must be created before subnets.
- Subnets must be created before VPC connectors.
- VPC connectors must be created before compute resources that reference them.
- External LB backends reference Cloud Run services.

**Special case -- vpc_connector:** VPC Connectors are ENTIRELY immutable. ALL fields are ForceNew in Terraform provider ~5.0. Any configuration change requires full resource recreation. This is unique among all node types and has significant UX implications (the platform must warn users that ANY change will destroy and recreate the connector).

**Special case -- external_lb:** External LB is a composite resource. The REGISTRY maps it to `google_compute_global_address`, but the actual infrastructure comprises 5-8 Terraform resources (global address, managed SSL certificate, backend service, URL map, target HTTPS proxy, forwarding rule, serverless NEG, CDN policy). Mutability varies per sub-resource. See the external_lb specifics doc (Phase 1, Plan 2) for details.

**Key characteristic:** These resources form infrastructure layers. Deploy ordering must respect the dependency chain. Deletion must be reverse-ordered.

---

## Special Case: Non-Terraform (Platform-Only)

**Applies to:** third_party_api

**State machine (simplified):**

| Current State | Event | Next State | Notes |
|---------------|-------|------------|-------|
| (none) | create | active | Node created in blueprint, saved to Firestore |
| active | update | active | All fields always mutable (Firestore CRUD only) |
| active | delete | deleted | Node removed from Firestore |

**Update semantics:** All fields are platform-metadata (D-09). No Terraform resource exists (`terraform_resource=""` in REGISTRY). Updates are immediate Firestore writes with no deploy cycle.

**Deploy behavior:** This node type is completely skipped during Terraform generation. The `third_party_api.tf.j2` template generates only a comment, no resources.

**Key characteristic:** Exists purely for dependency graph visualization. Compute nodes can have `Invoke` edges to third_party_api nodes (per ACTION_VALID_TARGETS). This allows the graph to show outbound API dependencies without creating any infrastructure.

---

## Archetype Assignment Summary

| Node Type | Archetype | ForceNew Field Count | Notes |
|-----------|-----------|---------------------|-------|
| service_account | Simple CRUD | 1 (account_id) | |
| secret_manager | Simple CRUD | 2 (secret_id, replication) | |
| gcs_bucket | Simple CRUD | 2-3 (name, location, hierarchical_namespace) | |
| pubsub_schema | Simple CRUD | 1 (name) | |
| pubsub_topic | Simple CRUD | 1 (tags) | |
| pubsub_subscription | Simple CRUD | 2 (tags, filter) | |
| cloud_task_queue | Simple CRUD | 2 (name, location) | |
| bigquery | Simple CRUD + Parent-Child | 1 (location) | Also Parent-Child for bigquery_table |
| bigtable | Simple CRUD | 3-4 (cluster: storage_type, zone, kms_key_name, node_scaling_factor) | |
| cloud_run | Compute with Image | 2 (name, location) | |
| cloud_run_job | Compute with Image | 2 (name, location) | |
| cloud_function | Compute with Image | 6 (name, location, docker_repository, worker_pool, event_type, trigger_region) | |
| cloud_sql | Parent-Child Composite | 4 (database_version, region, name, master_instance_name) | |
| firestore | Parent-Child Composite | 4 (name, location_id, type, tags) | |
| vpc | Network with Dependencies | 2-3 (description, network_profile, delete_default_routes_on_create) | |
| subnet | Network with Dependencies | 2-3 (description, ipv6_access_type, params.resource_manager_tags) | |
| vpc_connector | Network with Dependencies | ALL fields | Entirely immutable |
| external_lb | Network with Dependencies | Varies per sub-resource | Composite resource |
| third_party_api | Non-Terraform | 0 | Platform-only, no TF resource |

---

*Referenced by: All category-level template docs (compute, data, messaging, network, security, external)*
*Phase: 01-resource-node-specifications*
