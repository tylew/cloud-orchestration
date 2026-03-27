# Cloud SQL: Specifics

**Node Type:** `cloud_sql`
**Terraform Resource:** `google_sql_database_instance`
**Category:** Data
**Archetype:** Parent-Child Composite
**Children:** cloud_sql_database (TF: `google_sql_database`), cloud_sql_table (platform-only)
**Provider version:** ~5.0
**Last verified:** 2026-03-26

---

## Overview

Cloud SQL is the most complex data type in the platform. It has 12 top-level config fields, 6 nested sub-models (SqlIpConfiguration, SqlBackupConfiguration, SqlDatabase, SqlFlag, SqlInsightsConfig, SqlMaintenanceWindow), and is the only type with a 3-level hierarchy (instance -> database -> table).

The Pydantic model `CloudSqlConfig` defines the instance configuration. Child databases can be defined either inline (via `databases` list on CloudSqlConfig) or as separate `cloud_sql_database` nodes in the blueprint. Tables are always separate `cloud_sql_table` nodes.

## Critical ForceNew Fields

### database_version

The `database_version` field (e.g., `POSTGRES_15`, `MYSQL_8_0`, `SQLSERVER_2019_STANDARD`) is ForceNew. Changing the database version triggers a full destroy-recreate of the Cloud SQL instance.

**Data Loss Implication:** Changing from `POSTGRES_15` to `POSTGRES_16` destroys the ENTIRE instance -- all databases, all data, all users. Without manual intervention:
1. Export all databases (pg_dump / mysqldump)
2. Deploy the new instance with the updated version
3. Import the data into the new instance
4. Update connection strings in dependent services

The platform should BLOCK this change with a warning and require explicit user confirmation (Phase 4 safety gate).

### region

The `region` is set from `GlobalConfig.region` and rendered as `var.gcp_region` in the TF template. It is an implicit ForceNew field -- Cloud SQL instances cannot be moved between regions.

### name

The instance name is derived from the node name with an environment prefix: `${var.environment}-{{ node.name }}`. Changing the node name changes the TF resource identity, triggering recreation.

### master_instance_name

Only applies to read replicas. If set, the instance is a replica of the referenced master. ForceNew -- cannot change which master a replica follows.

## Semi-Immutable: private_network

The `ip_configuration.private_network` field is semi-immutable:
- You CAN add a private network connection (set from null to a VPC self_link)
- You CANNOT remove it once set (going from a VPC reference back to null triggers an error, not recreation)

This means the first connection to a VPC is a one-way door. The platform should warn users that enabling private IP is irreversible on the existing instance.

## disk_size Gotcha

The `disk_size` field is technically mutable, but decreasing it may trigger recreation depending on the current allocated size. Best practice:
- Use `disk_autoresize = true` (default) to avoid manual size management
- If managing manually, only increase, never decrease
- Consider adding `lifecycle { ignore_changes = [settings[0].disk_size] }` when autoresize is enabled

## Nested Sub-Model Details

### SqlIpConfiguration

Controls network access to the instance.

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| ipv4_enabled | bool | false | Enable public IP. False = private-only (recommended for production) |
| private_network | string | null | VPC self_link for private IP. Semi-immutable (see above). Resolved via `resolve_ref()` in TF template. |
| require_ssl | bool | true | Require SSL for connections |
| ssl_mode | string | null | SSL enforcement mode (if specified) |
| allocated_ip_range | string | null | Named IP range for private IP allocation |
| enable_private_path_for_google_cloud_services | bool | true | Allow Google services to access via private path |

### SqlBackupConfiguration

Automated backup settings.

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| enabled | bool | true | Enable automated backups |
| point_in_time_recovery_enabled | bool | true | Enable PITR (requires binary logging for MySQL) |
| start_time | string | "03:00" | Backup window start (UTC) |
| transaction_log_retention_days | int | 7 | How long to retain transaction logs |
| retained_backups | int | 7 | Number of backups to retain |
| retention_unit | string | "COUNT" | COUNT or (future: DAYS) |

### SqlInsightsConfig

Query Insights for performance monitoring.

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| query_insights_enabled | bool | true | Enable Query Insights |
| query_plans_per_minute | int | 5 | Sample rate for query plans |
| query_string_length | int | 1024 | Max length of captured query strings |
| record_application_tags | bool | true | Record application-level tags |
| record_client_address | bool | true | Record client IP addresses |

### SqlMaintenanceWindow

When GCP can apply maintenance updates.

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| day | int | 7 | Day of week (1=Monday, 7=Sunday) |
| hour | int | 3 | Hour (0-23, UTC) |
| update_track | string | "stable" | "stable" or "canary" |

### SqlFlag

Database engine flags (e.g., PostgreSQL GUC settings, MySQL system variables).

| Field | Type | Notes |
|-------|------|-------|
| name | string | Flag name (e.g., "max_connections", "log_min_duration_statement") |
| value | string | Flag value (always string, even for numeric values) |

## Terraform Template Analysis

The `cloud_sql.tf.j2` template generates:
1. One `google_sql_database_instance` resource for the instance
2. One `google_sql_database` resource per entry in `config.databases[]`

Key observations:
- Instance name is environment-prefixed: `${var.environment}-{{ node.name }}`
- Database resources reference the instance via `google_sql_database_instance.{{ node.name }}.name`
- The template does NOT generate any table resources (cloud_sql_table is platform-only)
- `private_network` uses `resolve_ref()` which resolves node references (e.g., a VPC node slug)

## Integration Points

- **Service accounts:** Cloud SQL uses project-level IAM (`google_project_iam_member`). Common roles: `roles/cloudsql.client` (connect), `roles/cloudsql.admin` (full admin).
- **VPC connectivity:** Private IP requires a VPC with Private Services Access configured. The `private_network` field references a VPC node.
- **Cloud Run / Cloud Function:** Typically connect via Cloud SQL Auth Proxy (uses connection_name output) or private IP (uses private_ip output).
- **Secret Manager:** Database passwords should be stored in Secret Manager and referenced by compute nodes.

## Validation Rules (from validation.py)

Required fields:
- `database_version` (error): "Database version is required"
- `tier` (error): "Machine tier is required"

Additional validation:
- `CloudSqlDatabaseConfig` validates `parentRef` is non-empty
- `CloudSqlTableConfig` validates `parentRef` is non-empty
- Global uniqueness warning: Cloud SQL instance names must be globally unique in GCP (`GLOBAL_UNIQUE_TYPES`)

---

## Child: cloud_sql_database (Detailed)

### Overview

Represents an individual database within a Cloud SQL instance. Has its own TF resource (`google_sql_database`), enabling independent lifecycle management.

### Pydantic Model: CloudSqlDatabaseConfig

```
parentRef: str     -- slug of parent cloud_sql instance node (required, validated non-empty)
name: str          -- database name within the instance (ForceNew in TF)
charset: str       -- default "UTF8"
collation: str     -- default "en_US.UTF8"
```

### Terraform Behavior

- Resource: `google_sql_database`
- `name` is ForceNew -- renaming a database requires recreation (and data loss for that database)
- `charset` and `collation` are mutable in TF
- The database resource depends on the parent instance: `instance = google_sql_database_instance.{{ node.name }}.name`

### Lifecycle Coupling

- Deleting the parent Cloud SQL instance CASCADE-DELETES all databases at the GCP level
- Deleting a database independently (via TF) does NOT affect the parent instance or sibling databases
- The platform should prevent orphaning: if a cloud_sql node is deleted, all child cloud_sql_database nodes should be removed from the blueprint

### Inline vs Flat Node

Databases can be defined two ways:
1. **Inline on parent:** `CloudSqlConfig.databases[]` uses the `SqlDatabase` model (includes tables and custom_ddl)
2. **Flat child node:** `cloud_sql_database` node type uses `CloudSqlDatabaseConfig` model (simpler, no inline tables)

Both generate `google_sql_database` TF resources. The flat node approach enables separate lifecycle management and is the recommended pattern for complex blueprints.

---

## Child: cloud_sql_table (Detailed)

### Overview

Represents a table within a Cloud SQL database. This is purely platform-level metadata -- NO Terraform resource is generated. This is the deepest nesting level in the platform: cloud_sql -> cloud_sql_database -> cloud_sql_table.

### Pydantic Model: CloudSqlTableConfig

```
parentRef: str              -- slug of parent cloud_sql_database node (required, validated non-empty)
name: str                   -- table name
columns: list[SqlColumn]    -- column definitions (default: [])
```

### SqlColumn Sub-Model

Each column supports:
- `name` (str): Column name
- `type` (SqlColumnType): 22 supported types -- INTEGER, BIGINT, SERIAL, VARCHAR, TEXT, BOOLEAN, TIMESTAMP, TIMESTAMPTZ, DATE, NUMERIC, JSON, JSONB, UUID, SMALLINT, DECIMAL, FLOAT, DOUBLE, CHAR, DATETIME, TIME, BLOB, ENUM
- `length` (int | None): For VARCHAR/CHAR types
- `nullable` (bool): Default true
- `primary_key` (bool): Default false
- `unique` (bool): Default false
- `default` (str | None): Default value expression
- `references` (str | None): Foreign key reference (e.g., "users(id)")

### Purpose and Future Use

cloud_sql_table exists for:
1. **Documentation:** Users can define their intended table schema within the blueprint
2. **Code generation:** Future AI agents / MCP tools can use table schemas to generate service code (models, migrations, CRUD endpoints)
3. **Validation:** Future phases can validate that internal graph field references match defined table columns

### All Fields Always Mutable

Per D-09, all fields on platform-only types are always mutable. There is no TF lifecycle concern since no infrastructure is generated.
