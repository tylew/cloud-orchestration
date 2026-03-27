# Data Category: Rigid Template

**Category:** Data + Storage
**Types covered:** cloud_sql, firestore, bigquery, bigtable, gcs_bucket
**Child types (inline):** cloud_sql_database, cloud_sql_table, firestore_collection, bigquery_table
**Provider version:** ~5.0
**Last verified:** 2026-03-26

---

## Cloud SQL

### Terraform Resource

- Resource: `google_sql_database_instance`
- Provider version: ~5.0
- Last verified: 2026-03-26

### State Machine

Archetype: **Parent-Child Composite** (children: cloud_sql_database, cloud_sql_table)

| Current State | Event | Next State | Notes |
|--------------|-------|------------|-------|
| (none) | create | draft | Initial node creation in blueprint |
| draft | deploy | deploying | TF apply submitted |
| deploying | success | deployed | TF apply completed |
| deploying | failure | failed | TF apply errored |
| deployed | update (mutable) | updating | In-place TF apply |
| deployed | update (immutable) | destroying | Destroy-recreate cycle -- DATA LOSS without migration |
| updating | success | deployed | |
| updating | failure | failed | |
| deployed | delete | destroying | TF destroy submitted; cascades to all child databases and tables |
| destroying | success | destroyed | |
| destroying | failure | failed | |
| failed | retry | deploying/updating/destroying | Deferred to Phase 3-5 |

### Field Classification

#### Terraform-mapped fields (12 fields)

| Field | Type | Required | Default | Mutable | TF Argument | Validation |
|-------|------|----------|---------|---------|-------------|------------|
| database_version | string | yes (error) | -- | **No (ForceNew)** | `database_version` | Must be valid version string (e.g., POSTGRES_15, MYSQL_8_0) |
| tier | string | yes (error) | -- | Yes | `settings.tier` | Must be valid machine type (e.g., db-f1-micro, db-custom-2-8192) |
| availability_type | string | no | "ZONAL" | Yes | `settings.availability_type` | ZONAL or REGIONAL |
| disk_size | int | no | 10 | Yes (with caveat) | `settings.disk_size` | >= 10 GB; changes may trigger recreation -- use lifecycle.ignore_changes |
| disk_type | string | no | "PD_SSD" | Yes | `settings.disk_type` | PD_SSD or PD_HDD |
| disk_autoresize | bool | no | true | Yes | `settings.disk_autoresize` | |
| disk_autoresize_limit | int | no | 0 | Yes | `settings.disk_autoresize_limit` | 0 = unlimited |
| deletion_protection | bool | no | true | Yes | `deletion_protection` | Must be disabled before delete |
| edition | string | no | null | Yes | `settings.edition` | ENTERPRISE or ENTERPRISE_PLUS |
| backup_configuration | SqlBackupConfiguration | no | null | Yes | `settings.backup_configuration {}` | Nested: enabled, point_in_time_recovery_enabled, start_time, transaction_log_retention_days, retained_backups |
| ip_configuration | SqlIpConfiguration | no | null | Yes (semi-immutable: private_network can be set but not removed) | `settings.ip_configuration {}` | Nested: ipv4_enabled, private_network, require_ssl, ssl_mode, allocated_ip_range |
| flags | list[SqlFlag] | no | [] | Yes | `settings.database_flags {}` | Nested: name, value pairs |

**Additional nested models in Pydantic (not top-level fields):**
- `insights_config` (SqlInsightsConfig): query_insights_enabled, query_plans_per_minute, query_string_length, record_application_tags, record_client_address
- `maintenance_window` (SqlMaintenanceWindow): day, hour, update_track
- `databases` (list[SqlDatabase]): Inline database definitions (name, charset, collation, tables, custom_ddl) -- generates separate `google_sql_database` TF resources

#### Platform-only fields

None -- all 12 CloudSqlConfig fields map to Terraform arguments.

### Required Fields (error-level)

- `database_version`: Database engine and version is required for instance creation
- `tier`: Machine tier determines compute resources; no sensible default

### Warning Fields

None.

### ForceNew Summary

Changing any of these fields triggers destroy-recreate of the entire Cloud SQL instance:
- `database_version` -- engine version change means full instance recreation (DATA LOSS without migration)
- `region` -- implicit via TF resource name/location (set from GlobalConfig)
- `name` -- implicit identity field (set from node name + environment prefix)
- `master_instance_name` -- only applies to read replicas

### Semi-immutable

- `ip_configuration.private_network`: Can ADD a private network connection but CANNOT remove it once set

---

### Child: cloud_sql_database

**Terraform Resource:** `google_sql_database`
**Lifecycle:** Coupled to parent cloud_sql instance. Deleting the instance cascades to all databases.

#### Field Classification

| Field | Type | Required | Default | Mutable | TF Argument | Validation |
|-------|------|----------|---------|---------|-------------|------------|
| parentRef | string | yes (error) | -- | Yes | (platform-only) | Must reference existing cloud_sql node slug |
| name | string | yes | -- | **No (ForceNew)** | `name` | Database name within the instance |
| charset | string | no | "UTF8" | Yes | `charset` | Valid charset for the database engine |
| collation | string | no | "en_US.UTF8" | Yes | `collation` | Valid collation for the database engine |

**Notes:**
- Has its own TF resource (`google_sql_database`) -- can be independently created/deleted while parent instance exists
- `parentRef` is platform-only (maps to `instance` TF argument via node resolution)
- The Pydantic model `CloudSqlDatabaseConfig` validates that parentRef is non-empty

---

### Child: cloud_sql_table

**Terraform Resource:** None (platform-only metadata)
**Lifecycle:** Coupled to parent cloud_sql_database. This is the deepest nesting level: cloud_sql -> cloud_sql_database -> cloud_sql_table (the only 3-level hierarchy in the platform).

#### Field Classification

All fields are platform-only -- always mutable per D-09.

| Field | Type | Required | Default | Mutable | TF Argument | Validation |
|-------|------|----------|---------|---------|-------------|------------|
| parentRef | string | yes (error) | -- | Yes | (none) | Must reference existing cloud_sql_database node slug |
| name | string | yes | -- | Yes | (none) | Table name |
| columns | list[SqlColumn] | no | [] | Yes | (none) | Each column: name, type (SqlColumnType enum), length, nullable, primary_key, unique, default, references |

**Notes:**
- NO Terraform generation -- workflow documentation only
- Purpose: allows users to define table schemas in the blueprint for documentation and future code generation
- SqlColumn sub-model supports: 22 column types (INTEGER, VARCHAR, TEXT, BOOLEAN, TIMESTAMP, JSON, JSONB, UUID, etc.)

---

## Firestore

### Terraform Resource

- Resource: `google_firestore_database`
- Provider version: ~5.0
- Last verified: 2026-03-26

### State Machine

Archetype: **Parent-Child Composite** (child: firestore_collection)

| Current State | Event | Next State | Notes |
|--------------|-------|------------|-------|
| (none) | create | draft | Initial node creation in blueprint |
| draft | deploy | deploying | TF apply submitted |
| deploying | success | deployed | TF apply completed |
| deploying | failure | failed | TF apply errored |
| deployed | update (mutable) | updating | In-place TF apply |
| deployed | update (immutable) | destroying | Destroy-recreate cycle -- DATA LOSS |
| updating | success | deployed | |
| updating | failure | failed | |
| deployed | delete | destroying | TF destroy submitted; delete_protection_state must be disabled first |
| destroying | success | destroyed | |
| destroying | failure | failed | |
| failed | retry | deploying/updating/destroying | Deferred to Phase 3-5 |

### Field Classification

#### Terraform-mapped fields (6 fields)

| Field | Type | Required | Default | Mutable | TF Argument | Validation |
|-------|------|----------|---------|---------|-------------|------------|
| database_id | string | yes (warning) | "(default)" | **No (ForceNew)** | `name` | Database ID; defaults to "(default)". Multi-database requires paid plan. |
| location_id | string | yes (error) | "" | **No (ForceNew)** | `location_id` | Must be valid GCP region/multi-region (e.g., nam5, eur3, us-east1) |
| type | string | no | "FIRESTORE_NATIVE" | **No (ForceNew)** | `type` | FIRESTORE_NATIVE or DATASTORE_MODE -- immutable after creation, affects query capabilities |
| concurrency_mode | string | no | "OPTIMISTIC" | Yes | `concurrency_mode` | OPTIMISTIC, PESSIMISTIC, or OPTIMISTIC_WITH_ENTITY_GROUPS |
| point_in_time_recovery_enablement | string | no | "POINT_IN_TIME_RECOVERY_ENABLED" | Yes | `point_in_time_recovery_enablement` | POINT_IN_TIME_RECOVERY_ENABLED or POINT_IN_TIME_RECOVERY_DISABLED |
| delete_protection_state | string | no | "DELETE_PROTECTION_ENABLED" | Yes | `delete_protection_state` | DELETE_PROTECTION_ENABLED or DELETE_PROTECTION_DISABLED; must be disabled before database deletion |

#### Platform-only fields (2 fields)

| Field | Type | Required | Default | Mutable | Notes |
|-------|------|----------|---------|---------|-------|
| collections | list[FirestoreCollection] | no | [] | Yes (always, per D-09) | Schema documentation for expected collection structure. Generates no TF resources directly. |
| indexes | list[FirestoreIndex] | no | [] | Yes (always, per D-09) | Composite index definitions. Generates `google_firestore_index` TF resources. |

**Note on indexes:** While `indexes` is categorized as platform-only (it lives on the FirestoreConfig model, not as a TF argument of `google_firestore_database`), the platform DOES generate separate `google_firestore_index` TF resources from this list. Each index has: collection, query_scope, api_scope, fields (field_path + order/array_config).

### Required Fields (error-level)

- `location_id`: Location is required -- cannot create a Firestore database without specifying where

### Warning Fields

- `database_id`: Database ID not set (defaults to "(default)"). Free tier is limited to the "(default)" database.

### ForceNew Summary

- `database_id` (mapped as `name` in TF) -- cannot rename a database after creation
- `location_id` -- cannot move a Firestore database after creation
- `type` -- FIRESTORE_NATIVE vs DATASTORE_MODE is permanent; affects query capabilities and data model
- `tags` -- per TF provider docs (uncommon to use)

---

### Child: firestore_collection

**Terraform Resource:** None (platform-only metadata)
**Lifecycle:** Coupled to parent firestore database. All fields always mutable per D-09.

#### Field Classification

All fields are platform-only -- always mutable.

| Field | Type | Required | Default | Mutable | TF Argument | Validation |
|-------|------|----------|---------|---------|-------------|------------|
| parentRef | string | yes (error) | -- | Yes | (none) | Must reference existing firestore node slug |
| name | string | yes | -- | Yes | (none) | Collection name (e.g., "users") |
| description | string | no | "" | Yes | (none) | |
| id_strategy | FirestoreIdStrategy | no | "auto" | Yes | (none) | auto, uuid, or custom |
| ttl_field | string | no | "" | Yes | (none) | Must reference a timestamp field in fields[]; generates `google_firestore_field` TTL config |
| fields | list[FirestoreField] | no | [] | Yes | (none) | Each field: name, type (FirestoreFieldType enum: 12 types), description, required, array_of, subfields |

**Notes:**
- NO direct TF resource -- Firestore is schemaless; this is platform-level schema documentation
- The `ttl_field` does generate a `google_firestore_field` TF resource for TTL configuration
- FirestoreField supports nested `subfields` for map types (recursive structure)
- `FirestoreCollectionConfig` validates that ttl_field references an existing timestamp field

---

## BigQuery

### Terraform Resource

- Resource: `google_bigquery_dataset`
- Provider version: ~5.0
- Last verified: 2026-03-26

### State Machine

Archetype: **Parent-Child Composite** (child: bigquery_table)

| Current State | Event | Next State | Notes |
|--------------|-------|------------|-------|
| (none) | create | draft | Initial node creation in blueprint |
| draft | deploy | deploying | TF apply submitted |
| deploying | success | deployed | TF apply completed |
| deploying | failure | failed | TF apply errored |
| deployed | update (mutable) | updating | In-place TF apply |
| deployed | update (immutable) | destroying | Destroy-recreate (location change) -- DATA LOSS |
| updating | success | deployed | |
| updating | failure | failed | |
| deployed | delete | destroying | TF destroy; delete_contents_on_destroy controls cascade behavior |
| destroying | success | destroyed | |
| destroying | failure | failed | |
| failed | retry | deploying/updating/destroying | Deferred to Phase 3-5 |

### Field Classification

#### Terraform-mapped fields (10 fields)

| Field | Type | Required | Default | Mutable | TF Argument | Validation |
|-------|------|----------|---------|---------|-------------|------------|
| dataset_id | string | yes (error) | -- | Yes (surprisingly) | `dataset_id` | Must match [a-zA-Z0-9_]+ pattern; identity-like but TF allows update |
| location | string | yes (warning) | "US" | **No (ForceNew)** | `location` | Valid GCP region or multi-region (US, EU, us-east1, etc.) |
| friendly_name | string | no | null | Yes | `friendly_name` | |
| description | string | no | null | Yes | `description` | |
| default_table_expiration_ms | int | no | null | Yes | `default_table_expiration_ms` | Milliseconds; applies to new tables |
| default_partition_expiration_ms | int | no | null | Yes | `default_partition_expiration_ms` | Milliseconds; applies to new partitioned tables |
| delete_contents_on_destroy | bool | no | false | Yes | `delete_contents_on_destroy` | If true, deleting dataset also deletes all tables within |
| max_time_travel_hours | int | no | 168 | Yes | `max_time_travel_hours` | 48-168 hours (2-7 days) |
| is_case_insensitive | bool | no | false | Yes | `is_case_insensitive` | Case-insensitive table/column names |
| labels | dict[str, str] | no | {} | Yes | `labels` | Key-value pairs for cost attribution and organization |

#### Platform-only fields (2 fields)

| Field | Type | Required | Default | Mutable | Notes |
|-------|------|----------|---------|---------|-------|
| tables | list[BqTable] | no | [] | Yes (always, per D-09) | Inline table definitions; generates `google_bigquery_table` TF resources |
| views | list[BqView] | no | [] | Yes (always, per D-09) | View definitions (table_id, query, use_legacy_sql) |

**Additional nested models:**
- `custom_sql` (list[BqCustomSql]): name, description, sql -- for custom SQL operations (platform-only)

### Required Fields (error-level)

- `dataset_id`: Dataset ID is required for dataset creation

### Warning Fields

- `location`: Location not set (defaults to "US")

### ForceNew Summary

- `location` -- the ONLY ForceNew field. Cannot move a dataset after creation. DATA LOSS on change.

---

### Child: bigquery_table

**Terraform Resource:** `google_bigquery_table`
**Lifecycle:** Coupled to parent bigquery dataset. Deleting the dataset cascades if `delete_contents_on_destroy=true`.

#### Field Classification

| Field | Type | Required | Default | Mutable | TF Argument | Validation |
|-------|------|----------|---------|---------|-------------|------------|
| parentRef | string | yes (error) | -- | Yes | (platform-only) | Must reference existing bigquery node slug |
| name | string | yes | -- | Yes | `table_id` | Table ID within the dataset |
| description | string | no | "" | Yes | `description` | |
| columns | list[BqColumn] | no | [] | Yes (additive only) | `schema` (JSON) | Each column: name, type (BqColumnType: 17 types), mode (NULLABLE/REQUIRED/REPEATED), description, nested fields for RECORD |
| time_partitioning | BqTimePartitioning | no | null | Yes (with caveats) | `time_partitioning {}` | type (DAY/HOUR/MONTH/YEAR), field, expiration_ms, require_partition_filter |
| range_partitioning | BqRangePartitioning | no | null | Yes | `range_partitioning {}` | field, range (start, end, interval) |
| clustering | list[str] | no | [] | Yes | `clustering` | Up to 4 column names; validated by Pydantic model |
| deletion_protection | bool | no | true | Yes | `deletion_protection` | Must be disabled before table can be deleted |

**Notes:**
- Has its own TF resource (`google_bigquery_table`) -- can be independently managed via TF
- Schema changes: adding columns is safe; removing or renaming columns is destructive
- `time_partitioning` and `range_partitioning` are mutually exclusive
- BigQueryTableConfig validates max 4 clustering columns

---

## Bigtable

### Terraform Resource

- Resource: `google_bigtable_instance`
- Provider version: ~5.0
- Last verified: 2026-03-26

### State Machine

Archetype: **Simple CRUD** (no child types in platform model)

| Current State | Event | Next State | Notes |
|--------------|-------|------------|-------|
| (none) | create | draft | Initial node creation in blueprint |
| draft | deploy | deploying | TF apply submitted |
| deploying | success | deployed | TF apply completed |
| deploying | failure | failed | TF apply errored |
| deployed | update (mutable) | updating | In-place TF apply |
| deployed | update (immutable) | destroying | Destroy-recreate -- DATA LOSS (cluster-level ForceNew) |
| updating | success | deployed | |
| updating | failure | failed | |
| deployed | delete | destroying | TF destroy; deletion_protection must be disabled first |
| destroying | success | destroyed | |
| destroying | failure | failed | |
| failed | retry | deploying/updating/destroying | Deferred to Phase 3-5 |

### Field Classification

#### Terraform-mapped fields (5 fields)

| Field | Type | Required | Default | Mutable | TF Argument | Validation |
|-------|------|----------|---------|---------|-------------|------------|
| instance_id | string | yes (error) | -- | **No (ForceNew, implicit identity)** | `name` | Instance identifier |
| instance_type | string | no | "PRODUCTION" | Yes | (derived from node count) | PRODUCTION (3+ nodes) or DEVELOPMENT (single node, no SLA) |
| deletion_protection | bool | no | true | Yes | `deletion_protection` | Must be disabled before instance can be deleted |
| cluster | BigtableCluster | yes | -- | Partially (see ForceNew below) | `cluster {}` | Nested: cluster_id, zone, num_nodes, storage_type, kms_key_name |
| autoscaling | BigtableAutoscaling | no | null | Yes | `cluster.autoscaling_config {}` | Nested: min_nodes, max_nodes, cpu_target, storage_target |

**Additional nested models:**
- `tables` (list[BigtableTable]): table_id, split_keys, deletion_protection, column_families -- generates separate `google_bigtable_table` TF resources (NOT modeled as child node types)

#### Platform-only fields

None -- all 5 BigtableConfig fields map to Terraform arguments.

### Required Fields (error-level)

- `instance_id`: Instance ID is required for instance creation

### Warning Fields

None.

### ForceNew Summary (cluster-level)

These fields are ForceNew PER CLUSTER, not per instance:
- `cluster.storage_type` -- HDD or SSD; cannot change after cluster creation
- `cluster.zone` -- cluster zone is immutable
- `cluster.kms_key_name` -- CMEK key cannot be changed after creation
- `node_scaling_factor` -- (if used) immutable per cluster

**Note:** A Bigtable instance can have multiple clusters for replication. ForceNew on cluster fields means that specific cluster must be recreated, but the instance itself may survive if other clusters exist.

---

## GCS Bucket

### Terraform Resource

- Resource: `google_storage_bucket`
- Provider version: ~5.0
- Last verified: 2026-03-26

### State Machine

Archetype: **Simple CRUD** (no children)

| Current State | Event | Next State | Notes |
|--------------|-------|------------|-------|
| (none) | create | draft | Initial node creation in blueprint |
| draft | deploy | deploying | TF apply submitted |
| deploying | success | deployed | TF apply completed |
| deploying | failure | failed | TF apply errored |
| deployed | update (mutable) | updating | In-place TF apply |
| deployed | update (immutable) | destroying | Destroy-recreate -- DATA LOSS (name/location change) |
| updating | success | deployed | |
| updating | failure | failed | |
| deployed | delete | destroying | TF destroy; non-empty bucket fails unless force_destroy=true |
| destroying | success | destroyed | |
| destroying | failure | failed | |
| failed | retry | deploying/updating/destroying | Deferred to Phase 3-5 |

### Field Classification

#### Terraform-mapped fields (10 fields)

| Field | Type | Required | Default | Mutable | TF Argument | Validation |
|-------|------|----------|---------|---------|-------------|------------|
| location | string | yes (error) | -- | **No (ForceNew, identity)** | `location` | Valid GCP region or multi-region; bucket location is permanent |
| storage_class | string | no | "STANDARD" | Yes | `storage_class` | STANDARD, NEARLINE, COLDLINE, ARCHIVE; class transitions have cost implications |
| uniform_bucket_level_access | bool | no | true | Yes | `uniform_bucket_level_access` | When enabled, disables ACLs in favor of IAM-only (recommended) |
| force_destroy | bool | no | false | Yes | `force_destroy` | If false (default), non-empty buckets cannot be deleted |
| versioning | GcsVersioning | no | null | Yes | `versioning {}` | Nested: enabled (bool) |
| lifecycle_rule | list[LifecycleRule] | no | null | Yes | `lifecycle_rule {}` | Nested: action (type, storage_class) + condition (age, num_newer_versions, with_state, created_before, matches_prefix, matches_suffix) |
| cors | list[GcsCors] | no | null | Yes | `cors {}` | Nested: origin, method, response_header, max_age_seconds |
| retention_policy | GcsRetentionPolicy | no | null | Yes | `retention_policy {}` | Nested: retention_period (seconds), is_locked (IRREVERSIBLE once true) |
| encryption | GcsEncryption | no | null | Yes | `encryption {}` | Nested: default_kms_key_name |
| logging | GcsLogging | no | null | Yes | `logging {}` | Nested: log_bucket, log_object_prefix |
| labels | dict[str, str] | no | {} | Yes | `labels` | Key-value pairs |

**Note:** The Pydantic model has 10 explicit fields but `labels` brings the effective count to 11. The plan references "10 fields" counting the top-level config attributes.

#### Platform-only fields

None -- all GcsBucketConfig fields map to Terraform arguments.

### Required Fields (error-level)

- `location`: Location is required -- bucket location is permanent and determines data residency

### Warning Fields

None.

### ForceNew Summary

- `name` -- implicit identity field (bucket names are globally unique in GCP); set from node name + environment prefix
- `location` -- implicit identity field; bucket location is permanent
- `hierarchical_namespace` -- explicit ForceNew per TF provider docs
- `custom_placement_config.data_locations` -- explicit ForceNew (dual-region config)

### Retention Policy Warning

- `retention_policy.is_locked`: Once set to `true`, this is IRREVERSIBLE. The retention policy cannot be removed or shortened. The bucket cannot be deleted until every object meets the retention period. Use with extreme caution.
