# BigQuery: Specifics

**Node Type:** `bigquery`
**Terraform Resource:** `google_bigquery_dataset`
**Category:** Data
**Archetype:** Parent-Child Composite
**Children:** bigquery_table (TF: `google_bigquery_table`)
**Provider version:** ~5.0
**Last verified:** 2026-03-26

---

## Overview

BigQuery is GCP's serverless data warehouse. The platform models BigQuery datasets with optional inline table and view definitions. BigQuery has the simplest ForceNew story of any data type -- only `location` is ForceNew. Most fields are freely mutable.

The Pydantic model `BigQueryConfig` has 12 fields: 10 Terraform-mapped and 2 platform-only (tables, views). An additional `custom_sql` field (list[BqCustomSql]) exists for custom SQL operations.

## Critical ForceNew Fields

### location

The ONLY ForceNew field on BigQuery datasets. Cannot move a dataset between regions or multi-regions after creation.

Valid locations:
- Multi-region: `US`, `EU`
- Regions: `us-east1`, `europe-west1`, `asia-northeast1`, etc.

**Data Loss Implication:** Changing location triggers full destroy-recreate. ALL tables, views, and data within the dataset are lost. BigQuery Transfer Service can migrate data between locations, but this is not automatic and requires manual orchestration.

Default: `"US"` -- the platform warns (warning severity) when location is not explicitly set.

## Mutable Fields of Note

### dataset_id

Surprisingly, `dataset_id` is mutable according to Terraform provider documentation. However, in practice it behaves as an identity field -- changing it effectively renames the dataset. The platform should treat this as a high-risk change:
- All table references using `project.dataset.table` notation will break
- All queries referencing the old dataset_id will fail
- All IAM bindings at the dataset level are tied to the dataset ID

Recommendation: Treat as "functionally immutable" in the platform UX even though TF allows it.

### default_table_expiration_ms

Sets a default expiration for new tables created in the dataset. Existing tables are NOT affected by changes to this value. Only applies to tables created after the setting is changed.

### default_partition_expiration_ms

Similar to table expiration -- sets default partition expiration for new partitioned tables. Does not retroactively affect existing partitions.

### max_time_travel_hours

Controls how far back time travel queries can go. Range: 48-168 hours (2-7 days). Default: 168 (7 days). Reducing this value is safe but limits the ability to query historical data.

### delete_contents_on_destroy

Controls cascade behavior during dataset deletion:
- `false` (default): Terraform destroy will FAIL if the dataset contains any tables or views
- `true`: Terraform destroy will delete all tables and views within the dataset

This is BigQuery's version of deletion protection -- it prevents accidental data loss by default.

### is_case_insensitive

Makes table and column names case-insensitive. Default: `false`. This is mutable but changing it after tables exist may cause issues if there are columns that differ only by case.

## Terraform Template Analysis

The `bigquery.tf.j2` template generates:

### 1. google_bigquery_dataset

The primary dataset resource. All 10 TF-mapped fields are rendered. Labels are rendered as a map block.

### 2. google_bigquery_table (from config.tables[])

For each entry in `config.tables[]`, generates a table resource with:
- `dataset_id`: References the parent dataset
- `table_id`: Table identifier
- `schema`: JSON-encoded column definitions (from `columns[]` or loaded from `schema_file`)
- `deletion_protection`: Table-level deletion protection
- `clustering`: Up to 4 clustering column names
- `time_partitioning {}`: Optional time-based partitioning config

Key observation: The template supports two schema definition methods:
1. Inline `columns[]` (rendered as `jsonencode([...])`)
2. External `schema_file` (loaded via `file()` function)

Nested RECORD columns are supported with recursive `fields[]` rendering.

## IAM: Dataset-Level Scoping

BigQuery is unique among data types in supporting dataset-level IAM:
- IAM scope: `dataset`
- TF IAM resource: `google_bigquery_dataset_iam_member`

This means IAM roles can be granted per-dataset, not just per-project. Common roles:
- `roles/bigquery.dataViewer`: Read access to dataset
- `roles/bigquery.dataEditor`: Read/write access to dataset
- `roles/bigquery.dataOwner`: Full control of dataset

This is more granular than cloud_sql/firestore/bigtable (which all use project-level IAM) and enables multi-team scenarios where different teams own different datasets.

## Integration Points

- **Cloud Run / Cloud Function:** Connect via `@google-cloud/bigquery` client library. Reference datasets by `project.dataset_id`.
- **Streaming inserts:** Cloud Run services can stream data into BigQuery tables for real-time analytics.
- **Scheduled queries:** BigQuery supports scheduled queries that can transform data on a schedule (not currently modeled in the platform).
- **Data transfer:** BigQuery Transfer Service can ingest from external sources (also not currently modeled).

## Validation Rules (from validation.py)

Required fields:
- `dataset_id` (error): "Dataset ID is required"
- `location` (warning): "Location not set (defaults to 'US')"

Additional validation:
- BigQueryTableConfig validates `parentRef` is non-empty
- BigQueryTableConfig validates max 4 clustering columns

---

## Child: bigquery_table (Detailed)

### Overview

Represents a table within a BigQuery dataset. Has its own TF resource (`google_bigquery_table`), enabling independent lifecycle management. This is one of the most feature-rich child types with partitioning, clustering, and schema management.

### Pydantic Model: BigQueryTableConfig

```
parentRef: str                                  -- slug of parent bigquery dataset node (required)
name: str                                       -- table_id in BigQuery terms
description: str                                -- default ""
columns: list[BqColumn]                         -- default []
time_partitioning: BqTimePartitioning | None    -- default null
range_partitioning: BqRangePartitioning | None  -- default null
clustering: list[str]                           -- default [] (max 4 columns)
deletion_protection: bool                       -- default true
```

### BqColumn Sub-Model

Each column supports:
- `name` (str): Column name
- `type` (BqColumnType): 17 supported types -- STRING, INTEGER, INT64, FLOAT64, BOOL, TIMESTAMP, DATE, DATETIME, NUMERIC, JSON, RECORD, BYTES, FLOAT, BIGNUMERIC, BOOLEAN, TIME, GEOGRAPHY
- `mode` (BqColumnMode): NULLABLE (default), REQUIRED, REPEATED
- `description` (str | None): Column description
- `fields` (list[BqColumn]): Nested fields for RECORD type (recursive structure)

### Partitioning Options

BigQuery tables support two mutually exclusive partitioning strategies:

**Time Partitioning** (BqTimePartitioning):
- `type`: Granularity -- DAY (default), HOUR, MONTH, YEAR
- `field`: Column to partition on (must be TIMESTAMP, DATE, or DATETIME). If null, uses `_PARTITIONTIME` pseudo-column.
- `expiration_ms`: Auto-delete partitions after this many milliseconds
- `require_partition_filter`: Force queries to include partition filter (prevents expensive full-table scans)

**Range Partitioning** (BqRangePartitioning):
- `field`: INTEGER column to partition on
- `range.start`: Start of range
- `range.end`: End of range
- `range.interval`: Size of each partition

Partitioning is a key design choice that affects query performance and cost. The platform should surface this prominently in the UI.

### Schema Evolution

BigQuery has specific rules about schema changes:
- **Adding columns:** Safe -- new columns are added with null values for existing rows
- **Removing columns:** Destructive -- requires table recreation (can use `bq query` with SELECT to create a new table without the column)
- **Renaming columns:** Not supported -- requires recreation
- **Changing column types:** Limited -- some type widening is allowed (INT64 -> FLOAT64) but narrowing is not
- **Changing mode:** NULLABLE -> REQUIRED requires all existing values to be non-null

The platform's schema field renders as JSON via `jsonencode()`, and TF tracks schema changes. Adding columns is safe; other changes may trigger recreation depending on the specific change.

### Clustering

Clustering improves query performance by co-locating rows with similar values for up to 4 columns. Clustering columns should be chosen based on common query filter/group-by patterns. Clustering is mutable -- can be changed without recreation.

### Deletion Protection

The `deletion_protection` flag (default: true) prevents accidental table deletion via Terraform. Must be explicitly set to false before the table can be destroyed. The platform's delete flow should handle this automatically (Phase 3-5).

### Lifecycle Coupling

- Deleting the parent dataset cascades to tables IF `delete_contents_on_destroy=true`
- If `delete_contents_on_destroy=false` (default), dataset deletion FAILS when tables exist
- Tables can be independently created/deleted via TF while the dataset exists
- Table-level deletion_protection must be disabled before individual table deletion
