# Bigtable: Specifics

**Node Type:** `bigtable`
**Terraform Resource:** `google_bigtable_instance`
**Category:** Data
**Archetype:** Simple CRUD
**Children:** None (tables use separate TF resource but are NOT modeled as child node types)
**Provider version:** ~5.0
**Last verified:** 2026-03-26

---

## Overview

Bigtable is GCP's managed wide-column NoSQL database, designed for massive throughput and low latency at scale. The platform model is relatively simple (5 top-level config fields) but has important cluster-level immutability characteristics.

Unlike other data types, Bigtable tables are defined within `config.tables[]` and generate separate `google_bigtable_table` TF resources, but they are NOT modeled as child node types (no `bigtable_table` in NodeType enum). This means table lifecycle is entirely managed through the parent bigtable node's config.

## Instance Types

Bigtable has two instance types with fundamentally different characteristics:

| Aspect | PRODUCTION | DEVELOPMENT |
|--------|-----------|-------------|
| Minimum nodes | 3 per cluster | 1 (single node) |
| SLA | 99.5% (single cluster), 99.99% (multi-cluster) | None |
| Replication | Yes (multi-cluster) | No |
| Performance | Full production throughput | Limited throughput, suitable for dev/test |
| Cost | Higher (3+ nodes minimum) | Lower (single node) |

The `instance_type` field is derived from node count rather than explicitly set in TF. The Pydantic model defaults to `"PRODUCTION"` which means 3+ nodes.

## Cluster-Level ForceNew Fields

Bigtable's ForceNew fields are unusual because they apply at the cluster level, not the instance level. A single Bigtable instance can have multiple clusters (for replication across zones/regions).

### storage_type

- `SSD` (default): Higher performance, higher cost
- `HDD`: Lower cost, lower performance (suitable for batch workloads)

ForceNew per cluster -- changing storage_type requires recreating that specific cluster. If the instance has multiple clusters, only the affected cluster needs recreation, but the data in that cluster is lost (may exist in replica clusters).

### zone

The cluster's zone (e.g., `us-central1-a`). Cannot move a cluster to a different zone after creation.

### kms_key_name

Customer-managed encryption key (CMEK) for the cluster. Cannot be changed after creation. If CMEK is needed, it must be specified at cluster creation time.

### node_scaling_factor

If used, immutable per cluster. Controls the granularity of autoscaling.

## Autoscaling Configuration

Autoscaling is a mutable configuration that can be added, modified, or removed after cluster creation:

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| min_nodes | int | 3 | Minimum number of nodes |
| max_nodes | int | 10 | Maximum number of nodes |
| cpu_target | int | 70 | CPU utilization target (percentage) |
| storage_target | int | null | Storage utilization target (percentage) |

When autoscaling is configured, the `num_nodes` field in the cluster config is ignored (TF template conditionally renders either `num_nodes` or `autoscaling_config`).

## Deletion Protection

The `deletion_protection` field (default: true) prevents accidental instance deletion. Must be explicitly set to false before the instance can be destroyed. The platform's delete flow should handle this automatically.

## Table Configuration (Inline, Not Child Nodes)

Tables are defined within `config.tables[]` using the `BigtableTable` model:

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| table_id | string | -- | Table identifier |
| split_keys | list[str] | [] | Pre-split row keys for initial distribution |
| deletion_protection | string | "PROTECTED" | Per-table deletion protection |
| column_families | list[BigtableColumnFamily] | -- | Required: at least one column family |

### Column Families

Bigtable organizes data by column families, not individual columns. Each column family has:
- `family` (str): Column family name
- `gc_policy` (BigtableGcPolicy): Garbage collection policy
  - `mode` (str | None): "union" or "intersection" for combining policies
  - `max_age` (str | None): Maximum age of cells (e.g., "72h")
  - `max_version` (int | None): Maximum number of cell versions
- `columns` (list[BigtableColumnQualifier]): Column qualifiers within the family
  - `qualifier` (str): Column name
  - `description` (str | None): Description
  - `value_type` (str | None): Value type hint (e.g., "string", "int64", "bytes")

**Key concept:** In Bigtable, column families are the schema unit. Columns within a family are not pre-defined in the schema -- any column qualifier can be written at runtime. The `columns` field in the platform model is for documentation purposes.

### Why Tables Are Not Child Nodes

Unlike Cloud SQL databases and BigQuery tables, Bigtable tables are not modeled as separate node types because:
1. Bigtable tables are tightly coupled to the instance and cluster configuration
2. Table operations (split keys, column families) are closely tied to cluster topology
3. The platform's use case for Bigtable is simpler (fewer users, less need for independent lifecycle)

Tables generate `google_bigtable_table` TF resources via the bigtable template, with column families rendered as nested blocks.

## Terraform Template Analysis

The `bigtable.tf.j2` template generates:

### 1. google_bigtable_instance

The primary instance resource:
- `name`: Set from `config.instance_id`
- `deletion_protection`: Boolean flag
- Single `cluster {}` block with cluster_id, zone, storage_type
- Conditional: `num_nodes` (when no autoscaling) OR `autoscaling_config {}` (when autoscaling configured)

### 2. google_bigtable_table (per table in config.tables[])

For each table:
- `name`: Set from `table.table_id`
- `instance_name`: References parent instance
- `column_family {}` blocks for each column family (only `family` name rendered -- GC policies handled separately in practice)

**Note:** The current template renders column families but does NOT render GC policies inline. GC policies may need to be managed via a separate `google_bigtable_gc_policy` resource (not currently generated).

## Integration Points

- **Service accounts:** Bigtable uses project-level IAM (`google_project_iam_member`). Common roles: `roles/bigtable.reader`, `roles/bigtable.user`, `roles/bigtable.admin`.
- **Cloud Run / Cloud Function:** Connect via `@google-cloud/bigtable` client library. Reference by instance ID.
- **HBase compatibility:** Bigtable is compatible with the HBase API for applications migrating from HBase.
- **Data flow:** Common pattern is Cloud Dataflow/Dataproc writing to Bigtable for serving, with BigQuery for analytics.

## Validation Rules (from validation.py)

Required fields:
- `instance_id` (error): "Instance ID is required"

No additional validation beyond standard required field checks.
