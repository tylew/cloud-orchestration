# Data Category: Shared Patterns

**Category:** Data + Storage
**Types covered:** cloud_sql, firestore, bigquery, bigtable, gcs_bucket
**Child types:** cloud_sql_database, cloud_sql_table, firestore_collection, bigquery_table

---

## Parent-Child Lifecycle Coupling

Data types in the platform include the most complex parent-child relationships. Understanding cascade behavior is critical for deploy ordering and deletion safety.

### CHILD_PARENT_MAP Hierarchy (from enums.py)

```python
CHILD_PARENT_MAP = {
    NodeType.FIRESTORE_COLLECTION: NodeType.FIRESTORE,
    NodeType.BIGQUERY_TABLE: NodeType.BIGQUERY,
    NodeType.CLOUD_SQL_DATABASE: NodeType.CLOUD_SQL,
    NodeType.CLOUD_SQL_TABLE: NodeType.CLOUD_SQL_DATABASE,
}
```

### Cascade Behavior on Parent Deletion

| Parent | Children | Cascade Behavior |
|--------|----------|-----------------|
| cloud_sql | cloud_sql_database, cloud_sql_table | Deleting the Cloud SQL instance deletes ALL databases and their tables. GCP enforces this at the infrastructure level. |
| firestore | firestore_collection | Deleting the Firestore database deletes all collections and documents. `delete_protection_state` must be disabled first. |
| bigquery | bigquery_table | Deleting the BigQuery dataset deletes all tables IF `delete_contents_on_destroy=true`. Otherwise, deletion fails if tables exist. |

### Two-Level Nesting (The Only 3-Level Hierarchy)

Cloud SQL is the only type with three levels of nesting:

```
cloud_sql (google_sql_database_instance)
  -> cloud_sql_database (google_sql_database)
    -> cloud_sql_table (NO TF resource -- platform-only)
```

This is documented per D-06: all three levels are documented flat under the cloud_sql specifics doc. The platform must handle:
1. Deleting a cloud_sql instance cascades through databases AND tables
2. Deleting a cloud_sql_database cascades to its tables (platform-level cleanup only since tables have no TF resource)
3. cloud_sql_table is pure metadata -- deletion has no infrastructure impact

## Independent vs Platform-Only Children

Not all child types are equal. Some have their own Terraform resources (and thus their own infrastructure lifecycle), while others exist only as platform metadata.

### Children with Terraform Resources (Independent)

| Child Type | TF Resource | Can Exist Independently? | Notes |
|-----------|-------------|-------------------------|-------|
| cloud_sql_database | `google_sql_database` | Yes -- can be created/deleted via TF while parent instance exists | Has ForceNew field: `name` |
| bigquery_table | `google_bigquery_table` | Yes -- can be independently managed via TF | Has `deletion_protection` flag |

These child types:
- Generate their own Terraform resource blocks
- Can be deployed/destroyed independently of the parent (while parent exists)
- Have their own ForceNew and mutability characteristics
- Still cascade-delete when parent is destroyed

### Children Without Terraform Resources (Platform-Only)

| Child Type | TF Resource | Purpose | Notes |
|-----------|-------------|---------|-------|
| firestore_collection | None | Schema documentation for expected collection structure | Firestore is schemaless; this tracks intended structure |
| cloud_sql_table | None | Schema documentation for table definitions | For documentation and future code generation |

These child types:
- Generate NO Terraform resources (except: firestore_collection's `ttl_field` generates a `google_firestore_field` resource)
- All fields are always mutable per D-09
- Deletion is purely platform-level (Firestore document cleanup)
- Exist to give the platform visibility into data structure for downstream features (code generation, MCP tools)

## Deletion Protection Patterns

Three data types implement deletion protection, each with different mechanisms:

| Type | Field | Default | Mechanism |
|------|-------|---------|-----------|
| firestore | `delete_protection_state` | DELETE_PROTECTION_ENABLED | TF argument; must be set to DELETE_PROTECTION_DISABLED before `terraform destroy` will succeed |
| bigtable | `deletion_protection` | true | TF argument; boolean flag that blocks deletion |
| gcs_bucket | `force_destroy` | false | Inverse logic: by default, non-empty buckets CANNOT be deleted. Set `force_destroy=true` to allow deletion of non-empty buckets |
| bigquery | `delete_contents_on_destroy` | false | Controls cascade: if false, dataset deletion fails when tables exist. Not strictly "protection" but similar effect |
| bigquery_table | `deletion_protection` | true | TF argument on child table; must be disabled before table deletion |

### Platform Implications

The platform must enforce a two-step deletion for protected resources:
1. First update: disable protection (set delete_protection_state=DISABLED, deletion_protection=false, or force_destroy=true)
2. Second update: perform the actual deletion

This should be automated in the deploy engine (Phase 3-5) rather than requiring users to manually toggle protection flags.

## Data Persistence and Destroy-Recreate Risk

Unlike compute types (Cloud Run, Cloud Function), data types hold stateful data. The destroy-recreate cycle triggered by ForceNew field changes has fundamentally different consequences:

### Data Loss Scenarios

| Type | ForceNew Field | Impact of Change |
|------|---------------|-----------------|
| cloud_sql | database_version | Entire instance destroyed and recreated. ALL databases and data lost unless manual migration (pg_dump/mysqldump + restore). |
| cloud_sql | region | Instance recreation. Same data loss risk. |
| firestore | location_id | Database destroyed and recreated. ALL documents lost. No automated migration path. |
| firestore | type | Database destroyed and recreated. FIRESTORE_NATIVE to DATASTORE_MODE (or vice versa) is a fundamental data model change. |
| bigquery | location | Dataset destroyed and recreated. ALL tables and data lost. BigQuery Transfer Service can help but is not automatic. |
| bigtable | cluster.storage_type | Cluster recreation. Data in that cluster lost (but may exist in other replica clusters). |
| bigtable | cluster.zone | Same as storage_type -- cluster-level recreation. |
| gcs_bucket | name/location | Bucket destroyed and recreated. ALL objects lost unless manually copied (gsutil cp). |

### Critical Context for Phase 4 (Safety)

Phase 4 must implement safeguards for data types:
- **Warning before ForceNew changes:** "This change will destroy and recreate the resource. All data will be lost."
- **Block by default:** ForceNew changes on data types should require explicit user confirmation
- **Migration guidance:** Where possible, suggest migration steps (e.g., "Run pg_dump before changing database_version")
- **Backup verification:** Check if backups are enabled before allowing destructive changes

## IAM Scope Variation

Data types have the most varied IAM scoping across any category, affecting how access control is configured in Terraform.

| Type | IAM Scope | TF IAM Resource | Granularity |
|------|-----------|----------------|-------------|
| cloud_sql | project | `google_project_iam_member` | All Cloud SQL instances in the project share the same IAM roles |
| firestore | project | `google_project_iam_member` | All Firestore databases in the project share the same IAM roles |
| bigtable | project | `google_project_iam_member` | All Bigtable instances in the project share the same IAM roles |
| bigquery | dataset | `google_bigquery_dataset_iam_member` | IAM can be scoped to individual datasets -- more granular than project-level |
| gcs_bucket | resource | `google_storage_bucket_iam_member` | IAM scoped to individual buckets -- most granular |

### Implications for Phase 6 (IAM)

- Project-level IAM types (cloud_sql, firestore, bigtable): Granting `roles/cloudsql.client` to a service account gives it access to ALL Cloud SQL instances in the project. The platform cannot restrict per-instance access via IAM alone.
- Dataset-level IAM (bigquery): The platform CAN restrict access per dataset, which is important for multi-tenant or multi-team scenarios.
- Resource-level IAM (gcs_bucket): The platform CAN restrict access per bucket, enabling fine-grained access control.

## Category Classification Notes

The REGISTRY classifies `gcs_bucket` as "Storage" category while `cloud_sql`, `firestore`, `bigquery`, and `bigtable` are "Data" category. This specification treats them together because:

1. They share the same lifecycle characteristics (stateful resources with data loss risk on destroy-recreate)
2. They share deletion protection patterns
3. They share the same state machine archetypes (Simple CRUD or Parent-Child Composite)
4. They are all valid targets for Read/Write actions in the internal graph (ACTION_VALID_TARGETS)

The category distinction is primarily for UI organization, not lifecycle behavior.

## Common Terraform Patterns

### Inline vs Separate Resources

The Terraform templates show two patterns for child resources:

1. **Inline in parent template:** Cloud SQL databases are generated as `google_sql_database` resources within the `cloud_sql.tf.j2` template, iterating over `config.databases[]`. BigQuery tables similarly iterate over `config.tables[]`.

2. **Separate TF resources from platform children:** When child node types (cloud_sql_database, bigquery_table) are modeled as separate nodes in the blueprint, they generate their own TF resources via the node's own template/handler.

The platform supports both patterns -- users can define databases inline on the Cloud SQL config OR as separate child nodes. The child node approach enables independent lifecycle management and more granular blueprint organization.

### Environment Prefixing

Data resources use environment-prefixed names in TF:
- Cloud SQL: `name = "${var.environment}-{{ node.name }}"`
- GCS Bucket: `name = "${var.environment}-{{ node.name }}"`
- Others (Firestore, BigQuery, Bigtable): use their own identity fields directly

This is important because Cloud SQL instance names and GCS bucket names are globally scoped in GCP, while Firestore database_id, BigQuery dataset_id, and Bigtable instance_id are project-scoped.
