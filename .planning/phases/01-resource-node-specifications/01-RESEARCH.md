# Phase 1: Resource Node Specifications - Research

**Researched:** 2026-03-26
**Domain:** GCP resource lifecycle documentation / Terraform provider mutability analysis
**Confidence:** HIGH

## Summary

Phase 1 is a pure documentation phase -- no code changes. The deliverable is a set of specification documents covering all 22 node types (plus 4 child types) with lifecycle state machines, field mutability classifications, default values, and validation constraints. The existing codebase already contains comprehensive Pydantic config models for every node type (in `packages/core/schemas/configs/`), a component registry (in `packages/core/registry.py`), and a validation module with required field definitions. These serve as the primary source of truth for field inventories.

The key research question was: which config fields are mutable (in-place update) vs immutable (destroy-recreate) in Terraform? Decision D-07 locks the Terraform Google provider's ForceNew annotations as the primary source. The provider version is pinned at `~> 5.0` per `infra/host/main.tf`. Research against the provider's raw documentation reveals that most GCP resources have only 1-3 ForceNew fields (typically `name`, `location`, and one or two resource-specific identifiers), while the vast majority of configuration fields are mutable in-place.

**Primary recommendation:** Structure the work as six category-level waves (Compute, Data, Messaging, Network, Security/Identity, External), each producing the three-tier document structure defined in D-01. Use the existing Pydantic config models as the field inventory starting point and cross-reference each field against Terraform provider documentation for mutability classification.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Three-tier document structure per category: rigid template doc, flexible narrative doc, specifics doc per resource
- **D-02:** Categories follow existing REGISTRY categories: Compute, Data, Messaging, Network, Security/Identity, External
- **D-03:** Platform-level states only (draft -> deploying -> deployed -> updating -> failed -> destroying -> destroyed). No GCP internal intermediate states.
- **D-04:** Document failure states but defer recovery design to deploy engine phases (Phase 3-5). Happy path + failure markers only.
- **D-05:** Child types documented inline under parent's specifics doc (not standalone)
- **D-06:** Cloud SQL hierarchy (cloud_sql -> cloud_sql_database -> cloud_sql_table) documented flat under cloud_sql specifics doc
- **D-07:** Terraform provider ForceNew annotations as primary mutability source. GCP API docs as fallback only.
- **D-08:** Pin and document Google Terraform provider version (~5.0) used for research. Add "last verified" date per category.
- **D-09:** Only classify fields that map to Terraform arguments. Platform-metadata fields (Firestore-only) always mutable.

### Claude's Discretion
- State machine archetype strategy: May define shared lifecycle archetypes (simple CRUD, parent-child, compute with image, network with dependencies) and map types to archetypes, OR document each type individually -- whichever reduces redundancy without sacrificing clarity.

### Deferred Ideas (OUT OF SCOPE)
- None
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RSLC-01 | Document create/update/delete behavior for all 22+ node types with per-type state machines | State machine archetypes identified; all 22 node types + 4 child types inventoried from enums.py and registry.py |
| RSLC-02 | Identify mutable vs immutable fields per resource type (which changes trigger destroy-recreate) | ForceNew fields researched per Terraform resource via provider docs; mutability summary compiled for all types |
| RSLC-03 | Define default values and validation constraints for every config field per node type | All 22 Pydantic config models read; defaults, types, validators, and REQUIRED_FIELDS already documented in code |
</phase_requirements>

## Architecture Patterns

### Document Output Structure (from D-01, D-02)
```
.planning/phases/01-resource-node-specifications/specs/
  compute/
    01-compute-template.md          # Rigid template: Cloud Run, Cloud Run Job, Cloud Function
    02-compute-patterns.md          # Narrative: shared compute behaviors, image lifecycle, scaling
    03-cloud-run.md                 # Specifics: Cloud Run edge cases, traffic splitting, probes
    04-cloud-run-job.md             # Specifics: Cloud Run Job edge cases, scheduling
    05-cloud-function.md            # Specifics: Cloud Function edge cases, source/build
  data/
    01-data-template.md             # Rigid template: Cloud SQL, Firestore, BigQuery, Bigtable, GCS Bucket
    02-data-patterns.md             # Narrative: shared data behaviors, deletion protection, child types
    03-cloud-sql.md                 # Specifics: Cloud SQL + cloud_sql_database + cloud_sql_table (D-06)
    04-firestore.md                 # Specifics: Firestore + firestore_collection (D-05)
    05-bigquery.md                  # Specifics: BigQuery + bigquery_table (D-05)
    06-bigtable.md                  # Specifics
    07-gcs-bucket.md                # Specifics
  messaging/
    01-messaging-template.md        # Rigid template: PubSub Schema/Topic/Subscription, Cloud Tasks
    02-messaging-patterns.md        # Narrative: shared messaging behaviors
    03-pubsub-schema.md             # Specifics
    04-pubsub-topic.md              # Specifics
    05-pubsub-subscription.md       # Specifics
    06-cloud-task-queue.md          # Specifics
  network/
    01-network-template.md          # Rigid template: VPC, Subnet, VPC Connector, External LB
    02-network-patterns.md          # Narrative: dependency ordering, CIDR management
    03-vpc.md                       # Specifics
    04-subnet.md                    # Specifics
    05-vpc-connector.md             # Specifics
    06-external-lb.md               # Specifics
  security/
    01-security-template.md         # Rigid template: Service Account, Secret Manager
    02-security-patterns.md         # Narrative: IAM scope, role bindings
    03-service-account.md           # Specifics
    04-secret-manager.md            # Specifics
  external/
    01-external-template.md         # Rigid template: Third Party API
    02-external-patterns.md         # Narrative: no Terraform resource, platform-only lifecycle
    03-third-party-api.md           # Specifics
```

### Rigid Template Schema (per D-01)

Each rigid template doc must contain these standardized sections for every node type in its category:

```markdown
## [Node Type Name]

### Terraform Resource
- Resource: `google_xxx_yyy`
- Provider version: ~5.0
- Last verified: YYYY-MM-DD

### State Machine
| Current State | Event | Next State | Notes |
|--------------|-------|------------|-------|
| (none) | create | draft | Initial node creation in blueprint |
| draft | deploy | deploying | TF apply submitted |
| deploying | success | deployed | TF apply completed |
| deploying | failure | failed | TF apply errored |
| deployed | update (mutable) | updating | In-place TF apply |
| deployed | update (immutable) | destroying | Destroy-recreate cycle |
| updating | success | deployed | |
| updating | failure | failed | |
| deployed | delete | destroying | TF destroy submitted |
| destroying | success | destroyed | |
| destroying | failure | failed | |
| failed | retry | deploying/updating/destroying | (deferred to Phase 3-5) |

### Field Classification
| Field | Type | Required | Default | Mutable | Validation |
|-------|------|----------|---------|---------|------------|
| field_name | string | yes | "" | yes/no (ForceNew) | constraints... |

### Required Fields (error-level)
- field_a: reason
- field_b: reason

### Warning Fields
- field_x: reason (has sensible default)
```

### State Machine Archetype Strategy (Claude's Discretion)

Based on analysis of the 22 node types, I recommend **four lifecycle archetypes** that cover all types:

1. **Simple CRUD** -- Most resources. Create via TF, update mutable fields in-place, immutable field changes trigger destroy-recreate, delete via TF destroy.
   - Applies to: service_account, secret_manager, gcs_bucket, pubsub_schema, pubsub_topic, pubsub_subscription, cloud_task_queue, bigquery, bigtable

2. **Compute with Image** -- Like Simple CRUD but with container image or source code as a special mutable field that triggers a new revision/version without destroying the resource.
   - Applies to: cloud_run, cloud_run_job, cloud_function

3. **Parent-Child Composite** -- Parent resource has child resources that are either managed inline (Terraform sub-blocks) or as separate TF resources. Delete of parent cascades to children.
   - Applies to: cloud_sql (with cloud_sql_database, cloud_sql_table), firestore (with firestore_collection), bigquery (with bigquery_table)

4. **Network with Dependencies** -- Resources that form infrastructure layers. Other resources depend on them; deletion requires reverse-dependency checking.
   - Applies to: vpc, subnet, vpc_connector, external_lb

**Non-Terraform type (special case):** third_party_api has no Terraform resource (`terraform_resource=""`). Its lifecycle is purely platform-level (Firestore CRUD only). Document it separately with a simplified state machine.

**Child-only types** (firestore_collection, bigquery_table, cloud_sql_database, cloud_sql_table): These are documented inline under their parents per D-05/D-06. Their state machines are tied to the parent's lifecycle.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Field inventory per type | Manual field listing | Read existing Pydantic config models from `packages/core/schemas/configs/` | Already comprehensive with types, defaults, validators |
| Required field lists | Manual requirements | Read `REQUIRED_FIELDS` dict from `packages/core/validation.py` | Already categorized as error vs warning severity |
| Terraform resource mapping | Manual lookup | Read `REGISTRY` from `packages/core/registry.py` | Already maps NodeType to terraform_resource string |
| Category classification | Manual grouping | Read `REGISTRY` category field | Already assigns Compute/Data/Messaging/Network/Security/External |
| Parent-child relationships | Manual hierarchy | Read `CHILD_PARENT_MAP` from `packages/core/schemas/enums.py` | Already defines firestore_collection->firestore, etc. |

**Key insight:** The existing codebase has ~80% of the raw data needed for the specifications. The primary value-add of this phase is (1) mutability classification from Terraform docs and (2) structuring everything into the three-tier document format that downstream phases can reference.

## Terraform ForceNew Fields by Resource (Mutability Research)

**Provider version:** hashicorp/google ~5.0 (pinned in `infra/host/main.tf`)
**Source:** Raw GitHub documentation for terraform-provider-google, fetched 2026-03-26
**Confidence:** MEDIUM -- Terraform docs don't always explicitly label ForceNew; some fields are inferred from "cannot be changed after creation" language. Actual provider source code would give HIGH confidence.

### Compute Types

**google_cloud_run_v2_service (Cloud Run)**
- ForceNew: `name`, `location` (implicit -- resource identifiers)
- All other fields including `template.*` are mutable (new revision created)
- Note: `template` changes create new revisions, not in-place updates to existing revisions

**google_cloud_run_v2_job (Cloud Run Job)**
- ForceNew: `name`, `location` (implicit -- resource identifiers)
- All other fields including `template.*` are mutable

**google_cloudfunctions2_function (Cloud Function)**
- ForceNew: `name`, `location`
- ForceNew (build_config): `docker_repository`, `worker_pool`
- ForceNew (event_trigger): `event_type`, `trigger_region`
- Mutable: `runtime`, `entry_point`, `source`, most service_config fields

### Data Types

**google_sql_database_instance (Cloud SQL)**
- ForceNew: `database_version`, `region`, `name`, `master_instance_name`
- Semi-immutable: `private_network` (can set but not remove)
- Note: `disk_size` changes may trigger recreation -- use `lifecycle.ignore_changes`

**google_firestore_database (Firestore)**
- ForceNew: `name` (database_id), `location_id`, `type` (FIRESTORE_NATIVE/DATASTORE_MODE), `tags`
- Mutable: `concurrency_mode`, `point_in_time_recovery_enablement`, `delete_protection_state`
- Note: `type` is immutable -- documented in existing config model comment

**google_bigquery_dataset (BigQuery)**
- ForceNew: `location`
- Mutable: `dataset_id` (surprisingly), `friendly_name`, `description`, `labels`, expiration settings

**google_bigtable_instance (Bigtable)**
- ForceNew (cluster-level): `storage_type`, `zone`, `kms_key_name`, `node_scaling_factor`
- Mutable: `num_nodes`, `display_name`, `deletion_protection`, `autoscaling_config`

**google_storage_bucket (GCS Bucket)**
- ForceNew: `hierarchical_namespace`, `custom_placement_config.data_locations`
- Note: Bucket `name` and `location` are identity fields (implicit ForceNew)
- Mutable: `storage_class`, `lifecycle_rule`, `versioning`, `cors`, `labels`, `uniform_bucket_level_access`

### Messaging Types

**google_pubsub_schema (Pub/Sub Schema)**
- ForceNew: `name` (implicit)
- Mutable: `type`, `definition`

**google_pubsub_topic (Pub/Sub Topic)**
- ForceNew: `tags`
- Mutable: `name` change not supported (identity), `kms_key_name`, `message_retention_duration`, `schema_settings`, `labels`

**google_pubsub_subscription (Pub/Sub Subscription)**
- ForceNew: `tags`, `filter` (cannot modify after creation)
- Mutable: `ack_deadline_seconds`, `message_retention_duration`, `push_config`, `retry_policy`, `labels`

**google_cloud_tasks_queue (Cloud Tasks)**
- ForceNew: `name`, `location` (implicit -- identity fields)
- Mutable: `rate_limits`, `retry_config`, `stackdriver_logging_config`

### Network Types

**google_compute_network (VPC)**
- ForceNew: `description`, `network_profile`, `delete_default_routes_on_create`
- Mutable: `routing_mode`, `mtu`, `auto_create_subnetworks`

**google_compute_subnetwork (Subnet)**
- ForceNew: `description`, `ipv6_access_type`, `params.resource_manager_tags`
- Mutable: `ip_cidr_range` (can expand, not shrink), `private_ip_google_access`, `secondary_ip_ranges`, `log_config`
- Note: `network` and `region` are identity fields (implicit ForceNew)

**google_vpc_access_connector (VPC Connector)**
- ForceNew: ALL fields -- VPC Connectors are entirely immutable after creation
- `name`, `network`, `ip_cidr_range`, `machine_type`, `subnet`, `region`, `min_instances`, `max_instances`, `min_throughput`, `max_throughput` all require recreation

**google_compute_global_address (External LB -- base resource)**
- ForceNew: Most fields -- global addresses are largely immutable
- The External LB is a composite of multiple TF resources (address, SSL cert, backend service, URL map, etc.)

### Security/Identity Types

**google_service_account**
- ForceNew: `account_id`
- Mutable: `display_name`, `description`

**google_secret_manager_secret**
- ForceNew: `replication` (entire replication config)
- Mutable: `rotation`, `expire_time`, `ttl`, `version_aliases`, `labels`
- Note: `secret_id` is an identity field (implicit ForceNew)

### External Types

**third_party_api** -- No Terraform resource. All fields are platform-metadata (Firestore-only), always mutable per D-09.

## Common Pitfalls

### Pitfall 1: Confusing Terraform Mutability with Platform Mutability
**What goes wrong:** Documenting a field as "immutable" when it's only immutable in Terraform but the platform could handle it by creating a new resource with data migration.
**Why it happens:** The platform's state machine wraps Terraform -- an immutable TF field doesn't necessarily mean the user can't change it, just that the platform must handle the destroy-recreate cycle.
**How to avoid:** Clearly separate "TF-immutable (ForceNew)" from "platform-immutable (user cannot change)". Most ForceNew fields should still be changeable by users; the platform just needs to warn about the destroy-recreate implications.
**Warning signs:** Field table showing "immutable" without specifying which layer.

### Pitfall 2: Missing Platform-Only Fields
**What goes wrong:** The Pydantic config models contain fields that exist only in the platform (e.g., `mode` on compute types, `workflow` definitions, `parentRef` on child types) and have no Terraform equivalent. Forgetting to document these separately leads to gaps.
**Why it happens:** D-09 says only classify TF-mapped fields, but the specs still need to document ALL fields for completeness.
**How to avoid:** Split field tables into two sections: "Terraform-mapped fields" (with mutability classification) and "Platform-only fields" (always mutable, no TF implications).
**Warning signs:** Field count in spec doesn't match field count in Pydantic model.

### Pitfall 3: VPC Connector Total Immutability
**What goes wrong:** Treating VPC Connector like other resources with some mutable fields. In reality, ALL VPC Connector fields are ForceNew -- any change requires full recreation.
**Why it happens:** Most other resources have only 1-3 ForceNew fields.
**How to avoid:** Flag VPC Connector as the one resource where the entire config is immutable. This has significant UX implications (warn users on any change).
**Warning signs:** Treating VPC Connector updates like Cloud Run updates.

### Pitfall 4: Child Type Lifecycle Coupling
**What goes wrong:** Documenting child types as having independent lifecycles when they're actually coupled to their parents.
**Why it happens:** Child types have their own Pydantic models and some have their own TF resources (google_sql_database, google_bigquery_table), making them seem independent.
**How to avoid:** Document that deleting a parent cascades to children. Note which child types have independent TF resources (cloud_sql_database, bigquery_table) vs pure platform-level children (firestore_collection, cloud_sql_table).
**Warning signs:** Child delete succeeding when parent is deleted.

### Pitfall 5: External LB Composite Resource Complexity
**What goes wrong:** Treating External LB as a single TF resource when it's actually a composite of 5-8 Terraform resources (global address, managed SSL cert, backend service, URL map, target HTTPS proxy, forwarding rule, serverless NEG, CDN policy).
**Why it happens:** REGISTRY maps it to `google_compute_global_address` which is just the base resource.
**How to avoid:** Document External LB's composite nature in its specifics doc. List all sub-resources and their individual mutability characteristics.
**Warning signs:** Spec treating `external_lb` as having a single TF resource lifecycle.

## Node Type Complete Inventory

### From enums.py NodeType + registry.py REGISTRY

| # | Node Type | Category | Terraform Resource | Has Children | Is Compute |
|---|-----------|----------|-------------------|-------------|-----------|
| 1 | service_account | Identity | google_service_account | No | No |
| 2 | vpc | Network | google_compute_network | No | No |
| 3 | subnet | Network | google_compute_subnetwork | No | No |
| 4 | vpc_connector | Network | google_vpc_access_connector | No | No |
| 5 | secret_manager | Security | google_secret_manager_secret | No | No |
| 6 | gcs_bucket | Storage | google_storage_bucket | No | No |
| 7 | cloud_sql | Data | google_sql_database_instance | Yes (database, table) | No |
| 8 | firestore | Data | google_firestore_database | Yes (collection) | No |
| 9 | bigquery | Data | google_bigquery_dataset | Yes (table) | No |
| 10 | bigtable | Data | google_bigtable_instance | No | No |
| 11 | pubsub_schema | Messaging | google_pubsub_schema | No | No |
| 12 | pubsub_topic | Messaging | google_pubsub_topic | No | No |
| 13 | pubsub_subscription | Messaging | google_pubsub_subscription | No | No |
| 14 | cloud_task_queue | Messaging | google_cloud_tasks_queue | No | No |
| 15 | cloud_run | Compute | google_cloud_run_v2_service | No | Yes |
| 16 | cloud_run_job | Compute | google_cloud_run_v2_job | No | Yes |
| 17 | cloud_function | Compute | google_cloudfunctions2_function | No | Yes |
| 18 | external_lb | Network | google_compute_global_address (composite) | No | No |
| 19 | third_party_api | External | (none) | No | No |

### Child Types (documented inline per D-05, D-06)

| # | Child Type | Parent Type | Terraform Resource | Notes |
|---|-----------|-------------|-------------------|-------|
| 20 | firestore_collection | firestore | (none -- platform only) | Inline under firestore specifics |
| 21 | bigquery_table | bigquery | google_bigquery_table | Inline under bigquery specifics |
| 22 | cloud_sql_database | cloud_sql | google_sql_database | Inline under cloud_sql specifics |
| 23 | cloud_sql_table | cloud_sql_database | (none -- platform only) | Inline under cloud_sql specifics |

### Field Counts per Config Model (from Pydantic models)

| Node Type | Total Fields | TF-Mapped Fields | Platform-Only Fields | Nested Sub-Models |
|-----------|-------------|------------------|---------------------|-------------------|
| cloud_run | 28 | 25 | 3 (mode, workflow, client) | 11 (VpcAccess, Probe, Traffic, Volume, etc.) |
| cloud_run_job | 18 | 15 | 3 (mode, workflow, scheduler_triggers) | 5 (VpcAccess, Volume, BinaryAuth, etc.) |
| cloud_function | 17 | 14 | 3 (mode, workflow, source_bucket*) | 5 (Source, EventTrigger, BuildConfig, etc.) |
| cloud_sql | 12 | 12 | 0 | 6 (IpConfig, Backup, Database, Flag, etc.) |
| firestore | 8 | 6 | 2 (collections, indexes) | 3 (Collection, Index, Field) |
| bigquery | 12 | 10 | 2 (tables, views) | 4 (Table, View, Partitioning, etc.) |
| bigtable | 5 | 5 | 0 | 4 (Cluster, Autoscaling, Table, etc.) |
| gcs_bucket | 10 | 10 | 0 | 6 (Versioning, Lifecycle, CORS, etc.) |
| service_account | 4 | 3 | 1 (roles -- platform IAM) | 1 (IamRole) |
| secret_manager | 11 | 8 | 3 (value, value_provided, pending_email) | 0 |
| vpc | 5 | 5 | 0 | 0 |
| subnet | 7 | 7 | 0 | 2 (SecondaryIpRange, LogConfig) |
| vpc_connector | 8 | 8 | 0 | 0 |
| pubsub_schema | 2 | 2 | 0 | 0 |
| pubsub_topic | 5 | 5 | 0 | 2 (SchemaSettings, StoragePolicy) |
| pubsub_subscription | 12 | 12 | 0 | 7 (RetryPolicy, DeadLetter, Push, etc.) |
| cloud_task_queue | 4 | 4 | 0 | 3 (RateLimits, RetryConfig, Logging) |
| external_lb | 13 | 13 | 0 | 6 (SslPolicy, Backend, CDN, IAP, etc.) |
| third_party_api | 6 | 0 | 6 (all platform-only) | 1 (RateLimit) |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Cloud Run v1 API (google_cloud_run_service) | Cloud Run v2 API (google_cloud_run_v2_service) | Provider ~4.x -> ~5.x | Registry already uses v2 resources |
| Cloud Functions 1st gen | Cloud Functions 2nd gen (google_cloudfunctions2_function) | Provider ~4.x | Registry already uses 2nd gen |
| VPC Connector only | Direct VPC Egress available | Cloud Run 2024+ | CloudRunVpcAccessDirect model exists but not yet in TF templates |
| google provider ~5.0 | google provider ~7.x available | 2025-2026 | Project pins ~5.0; mutability research should note ~5.0 as baseline |

**Note on provider version:** The project pins `~> 5.0` but the latest is 7.x. Mutability classifications are based on 5.x documentation. Some ForceNew fields may have changed in newer versions. The "last verified" date per D-08 handles this.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest with pytest-asyncio |
| Config file | `packages/pyproject.toml` |
| Quick run command | `python -m pytest tests/ -x --tb=short` |
| Full suite command | `python -m pytest tests/` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RSLC-01 | State machines documented for all 22+ types | manual-only | N/A -- documentation review | N/A |
| RSLC-02 | Mutable vs immutable fields classified | manual-only | N/A -- documentation review | N/A |
| RSLC-03 | Default values and validation constraints defined | manual-only | N/A -- documentation review | N/A |

### Sampling Rate
- **Per task commit:** Manual review -- verify spec covers all fields from Pydantic model
- **Per wave merge:** Cross-reference field counts between spec and config model
- **Phase gate:** All 19 top-level types + 4 child types have complete specs

### Wave 0 Gaps
None -- this is a documentation-only phase. No test infrastructure needed. Validation is structural review (all types covered, all fields listed, all mutability classified).

## Open Questions

1. **Provider version gap (5.x vs 7.x)**
   - What we know: Project pins ~5.0, latest is 7.x. Some ForceNew fields may differ.
   - What's unclear: Whether any fields changed mutability between 5.x and 7.x.
   - Recommendation: Document based on 5.x (current pin), add "last verified" dates per D-08. Update when provider is upgraded.

2. **External LB composite resource mapping**
   - What we know: REGISTRY maps to `google_compute_global_address` but the actual LB requires 5-8 TF resources.
   - What's unclear: Exact set of sub-resources the platform generates (need to read `external_lb.tf.j2` template in detail).
   - Recommendation: Document the composite nature in the specifics doc; list each sub-resource and its mutability.

3. **Cloud Function source immutability nuance**
   - What we know: WebFetch response listed `runtime`, `entry_point`, `service_account_email` as immutable, but these are commonly updated for Cloud Functions.
   - What's unclear: Whether the Terraform docs are accurate or the WebFetch extraction was over-aggressive. These fields are typically mutable in the GCP API.
   - Recommendation: Mark as MEDIUM confidence, verify against provider source code or actual `terraform plan` output before finalizing. The GCP API allows updating runtime and entry_point on 2nd gen functions.

## Sources

### Primary (HIGH confidence)
- `packages/core/schemas/configs/*.py` -- All 22 Pydantic config models with field types, defaults, validators
- `packages/core/registry.py` -- REGISTRY mapping NodeType to terraform_resource, category, iam_scope
- `packages/core/schemas/enums.py` -- NodeType enum, CHILD_PARENT_MAP, COMPUTE_TYPES, ACTION_VALID_TARGETS
- `packages/core/validation.py` -- REQUIRED_FIELDS dict with error/warning severity per type
- `infra/host/main.tf` -- Terraform provider version `~> 5.0`

### Secondary (MEDIUM confidence)
- [Terraform google_cloud_run_v2_service docs](https://raw.githubusercontent.com/hashicorp/terraform-provider-google/main/website/docs/r/cloud_run_v2_service.html.markdown) -- ForceNew fields
- [Terraform google_sql_database_instance docs](https://raw.githubusercontent.com/hashicorp/terraform-provider-google/main/website/docs/r/sql_database_instance.html.markdown) -- ForceNew: database_version, region, name
- [Terraform google_firestore_database docs](https://raw.githubusercontent.com/hashicorp/terraform-provider-google/main/website/docs/r/firestore_database.html.markdown) -- ForceNew: name, location_id, type, tags
- [Terraform google_bigquery_dataset docs](https://raw.githubusercontent.com/hashicorp/terraform-provider-google/main/website/docs/r/bigquery_dataset.html.markdown) -- ForceNew: location
- [Terraform google_bigtable_instance docs](https://raw.githubusercontent.com/hashicorp/terraform-provider-google/main/website/docs/r/bigtable_instance.html.markdown) -- ForceNew: cluster storage_type, zone, kms_key_name
- [Terraform google_storage_bucket docs](https://raw.githubusercontent.com/hashicorp/terraform-provider-google/main/website/docs/r/storage_bucket.html.markdown) -- ForceNew: hierarchical_namespace
- [Terraform google_compute_network docs](https://raw.githubusercontent.com/hashicorp/terraform-provider-google/main/website/docs/r/compute_network.html.markdown) -- ForceNew: description, network_profile
- [Terraform google_compute_subnetwork docs](https://raw.githubusercontent.com/hashicorp/terraform-provider-google/main/website/docs/r/compute_subnetwork.html.markdown) -- ForceNew: description, ipv6_access_type
- [Terraform google_vpc_access_connector docs](https://raw.githubusercontent.com/hashicorp/terraform-provider-google/main/website/docs/r/vpc_access_connector.html.markdown) -- ForceNew: ALL fields
- [Terraform google_service_account docs](https://raw.githubusercontent.com/hashicorp/terraform-provider-google/main/website/docs/r/google_service_account.html.markdown) -- ForceNew: account_id
- [Terraform google_secret_manager_secret docs](https://raw.githubusercontent.com/hashicorp/terraform-provider-google/main/website/docs/r/secret_manager_secret.html.markdown) -- ForceNew: replication
- [Terraform google_pubsub_topic docs](https://raw.githubusercontent.com/hashicorp/terraform-provider-google/main/website/docs/r/pubsub_topic.html.markdown) -- ForceNew: tags only
- [Terraform google_pubsub_subscription docs](https://raw.githubusercontent.com/hashicorp/terraform-provider-google/main/website/docs/r/pubsub_subscription.html.markdown) -- ForceNew: tags, filter
- [Terraform google_cloud_tasks_queue docs](https://raw.githubusercontent.com/hashicorp/terraform-provider-google/main/website/docs/r/cloud_tasks_queue.html.markdown) -- ForceNew: name, location (implicit)
- [Terraform google_cloudfunctions2_function docs](https://raw.githubusercontent.com/hashicorp/terraform-provider-google/main/website/docs/r/cloudfunctions2_function.html.markdown) -- ForceNew: name, location, some build_config fields
- [Magic Modules Immutable Fields Best Practices](https://googlecloudplatform.github.io/magic-modules/best-practices/immutable-fields/) -- ForceNew pattern documentation

### Tertiary (LOW confidence)
- Cloud Function field mutability (runtime, entry_point) -- WebFetch extraction may be over-aggressive; needs validation against actual provider behavior

## Metadata

**Confidence breakdown:**
- Node type inventory: HIGH -- directly from codebase (enums.py, registry.py)
- Field inventory & defaults: HIGH -- directly from Pydantic config models
- State machine design: HIGH -- follows locked decision D-03 (platform-level states only)
- Mutability classification: MEDIUM -- from Terraform raw docs, not all fields explicitly labeled; Cloud Function fields uncertain
- Archetype strategy: HIGH -- clear patterns emerge from the 22 types

**Research date:** 2026-03-26
**Valid until:** 2026-05-26 (60 days -- stable domain, Terraform provider ~5.0 is pinned)
