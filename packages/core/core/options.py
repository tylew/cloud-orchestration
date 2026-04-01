"""Options registry — enumerates valid choices for constrained config fields.

Maps (NodeType, field_path) → list of {value, label} dicts so the frontend
can render dropdowns and the backend can validate user selections.
"""

from core.schemas.enums import NodeType

_LAST_UPDATED = "2026-03-31"

# ── GCP Regions ──────────────────────────────────────────────────────

GCP_REGIONS: list[dict[str, str]] = [
    {"value": "africa-south1", "label": "Johannesburg"},
    {"value": "asia-east1", "label": "Taiwan"},
    {"value": "asia-east2", "label": "Hong Kong"},
    {"value": "asia-northeast1", "label": "Tokyo"},
    {"value": "asia-northeast2", "label": "Osaka"},
    {"value": "asia-northeast3", "label": "Seoul"},
    {"value": "asia-south1", "label": "Mumbai"},
    {"value": "asia-south2", "label": "Delhi"},
    {"value": "asia-southeast1", "label": "Singapore"},
    {"value": "asia-southeast2", "label": "Jakarta"},
    {"value": "australia-southeast1", "label": "Sydney"},
    {"value": "australia-southeast2", "label": "Melbourne"},
    {"value": "europe-central2", "label": "Warsaw"},
    {"value": "europe-north1", "label": "Finland"},
    {"value": "europe-southwest1", "label": "Madrid"},
    {"value": "europe-west1", "label": "Belgium"},
    {"value": "europe-west2", "label": "London"},
    {"value": "europe-west3", "label": "Frankfurt"},
    {"value": "europe-west4", "label": "Netherlands"},
    {"value": "europe-west6", "label": "Zurich"},
    {"value": "europe-west8", "label": "Milan"},
    {"value": "europe-west9", "label": "Paris"},
    {"value": "europe-west10", "label": "Berlin"},
    {"value": "europe-west12", "label": "Turin"},
    {"value": "me-central1", "label": "Doha"},
    {"value": "me-central2", "label": "Dammam"},
    {"value": "me-west1", "label": "Tel Aviv"},
    {"value": "northamerica-northeast1", "label": "Montréal"},
    {"value": "northamerica-northeast2", "label": "Toronto"},
    {"value": "northamerica-south1", "label": "Mexico"},
    {"value": "southamerica-east1", "label": "São Paulo"},
    {"value": "southamerica-west1", "label": "Santiago"},
    {"value": "us-central1", "label": "Iowa"},
    {"value": "us-east1", "label": "South Carolina"},
    {"value": "us-east4", "label": "Virginia"},
    {"value": "us-east5", "label": "Columbus"},
    {"value": "us-south1", "label": "Dallas"},
    {"value": "us-west1", "label": "Oregon"},
    {"value": "us-west2", "label": "Los Angeles"},
    {"value": "us-west3", "label": "Salt Lake City"},
    {"value": "us-west4", "label": "Las Vegas"},
]

GCP_MULTI_REGIONS: list[dict[str, str]] = [
    {"value": "US", "label": "United States (multi-region)"},
    {"value": "EU", "label": "European Union (multi-region)"},
    {"value": "ASIA", "label": "Asia (multi-region)"},
]

# ── Helpers ──────────────────────────────────────────────────────────

def _opts(*pairs: tuple[str, str]) -> list[dict[str, str]]:
    """Build option list from (value, label) tuples."""
    return [{"value": v, "label": l} for v, l in pairs]

# ── Per-type option sets ─────────────────────────────────────────────

_CLOUD_SQL_DATABASE_VERSIONS = _opts(
    ("POSTGRES_17", "PostgreSQL 17"),
    ("POSTGRES_16", "PostgreSQL 16"),
    ("POSTGRES_15", "PostgreSQL 15"),
    ("POSTGRES_14", "PostgreSQL 14"),
    ("POSTGRES_13", "PostgreSQL 13"),
    ("MYSQL_8_0", "MySQL 8.0"),
    ("MYSQL_8_4", "MySQL 8.4"),
    ("SQLSERVER_2022_STANDARD", "SQL Server 2022 Standard"),
    ("SQLSERVER_2022_ENTERPRISE", "SQL Server 2022 Enterprise"),
    ("SQLSERVER_2022_EXPRESS", "SQL Server 2022 Express"),
    ("SQLSERVER_2022_WEB", "SQL Server 2022 Web"),
    ("SQLSERVER_2019_STANDARD", "SQL Server 2019 Standard"),
    ("SQLSERVER_2019_ENTERPRISE", "SQL Server 2019 Enterprise"),
    ("SQLSERVER_2019_EXPRESS", "SQL Server 2019 Express"),
    ("SQLSERVER_2019_WEB", "SQL Server 2019 Web"),
)

_CLOUD_SQL_TIERS = _opts(
    ("db-f1-micro", "Shared-core f1-micro"),
    ("db-g1-small", "Shared-core g1-small"),
    ("db-custom-1-3840", "1 vCPU, 3.75 GB"),
    ("db-custom-2-7680", "2 vCPU, 7.5 GB"),
    ("db-custom-2-13312", "2 vCPU, 13 GB"),
    ("db-custom-4-15360", "4 vCPU, 15 GB"),
    ("db-custom-4-26624", "4 vCPU, 26 GB"),
    ("db-custom-8-30720", "8 vCPU, 30 GB"),
    ("db-custom-8-53248", "8 vCPU, 52 GB"),
    ("db-custom-16-61440", "16 vCPU, 60 GB"),
    ("db-custom-16-106496", "16 vCPU, 104 GB"),
    ("db-custom-32-122880", "32 vCPU, 120 GB"),
    ("db-custom-64-245760", "64 vCPU, 240 GB"),
    ("db-custom-96-368640", "96 vCPU, 360 GB"),
)

_CLOUD_SQL_EDITIONS = _opts(
    ("ENTERPRISE", "Enterprise"),
    ("ENTERPRISE_PLUS", "Enterprise Plus"),
)

_AVAILABILITY_TYPES = _opts(
    ("ZONAL", "Zonal (single zone)"),
    ("REGIONAL", "Regional (HA)"),
)

_CLOUD_SQL_DISK_TYPES = _opts(
    ("PD_SSD", "SSD persistent disk"),
    ("PD_HDD", "HDD persistent disk"),
)

_CLOUD_SQL_ACTIVATION_POLICIES = _opts(
    ("ALWAYS", "Always on"),
    ("NEVER", "Never (stopped)"),
    ("ON_DEMAND", "On demand"),
)

_CLOUD_SQL_CONNECTOR_ENFORCEMENT = _opts(
    ("NOT_REQUIRED", "Not required"),
    ("REQUIRED", "Required"),
)

_CLOUD_RUN_INGRESS = _opts(
    ("INGRESS_TRAFFIC_ALL", "All traffic"),
    ("INGRESS_TRAFFIC_INTERNAL_ONLY", "Internal only"),
    ("INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER", "Internal + Cloud Load Balancing"),
)

_CLOUD_RUN_EXECUTION_ENV = _opts(
    ("EXECUTION_ENVIRONMENT_GEN1", "First generation"),
    ("EXECUTION_ENVIRONMENT_GEN2", "Second generation"),
)

_CLOUD_RUN_LAUNCH_STAGE = _opts(
    ("GA", "General Availability"),
    ("BETA", "Beta"),
    ("ALPHA", "Alpha"),
)

_CLOUD_RUN_VPC_EGRESS = _opts(
    ("ALL_TRAFFIC", "All traffic"),
    ("PRIVATE_RANGES_ONLY", "Private ranges only"),
)

_CF_RUNTIMES = _opts(
    ("python313", "Python 3.13"),
    ("python312", "Python 3.12"),
    ("python311", "Python 3.11"),
    ("python310", "Python 3.10"),
    ("nodejs22", "Node.js 22"),
    ("nodejs20", "Node.js 20"),
    ("nodejs18", "Node.js 18"),
    ("go123", "Go 1.23"),
    ("go122", "Go 1.22"),
    ("go121", "Go 1.21"),
    ("java21", "Java 21"),
    ("java17", "Java 17"),
    ("java11", "Java 11"),
    ("dotnet8", ".NET 8"),
    ("dotnet6", ".NET 6"),
    ("ruby33", "Ruby 3.3"),
    ("ruby32", "Ruby 3.2"),
    ("php83", "PHP 8.3"),
    ("php82", "PHP 8.2"),
)

_CF_INGRESS = _opts(
    ("ALLOW_ALL", "Allow all traffic"),
    ("ALLOW_INTERNAL_ONLY", "Internal only"),
    ("ALLOW_INTERNAL_AND_GCLB", "Internal + Cloud Load Balancing"),
)

_CF_VPC_EGRESS = _opts(
    ("ALL_TRAFFIC", "All traffic"),
    ("PRIVATE_RANGES_ONLY", "Private ranges only"),
)

_CF_RETRY_POLICY = _opts(
    ("RETRY_POLICY_RETRY", "Retry on failure"),
    ("RETRY_POLICY_DO_NOT_RETRY", "Do not retry"),
)

_GCS_STORAGE_CLASSES = _opts(
    ("STANDARD", "Standard"),
    ("NEARLINE", "Nearline"),
    ("COLDLINE", "Coldline"),
    ("ARCHIVE", "Archive"),
)

_GCS_PUBLIC_ACCESS_PREVENTION = _opts(
    ("inherited", "Inherited"),
    ("enforced", "Enforced"),
)

_GCS_AUTOCLASS_TERMINAL = _opts(
    ("NEARLINE", "Nearline"),
    ("ARCHIVE", "Archive"),
)

_BQ_STORAGE_BILLING = _opts(
    ("LOGICAL", "Logical bytes"),
    ("PHYSICAL", "Physical bytes"),
)

_BQ_TIME_PARTITIONING_TYPE = _opts(
    ("DAY", "Daily"),
    ("HOUR", "Hourly"),
    ("MONTH", "Monthly"),
    ("YEAR", "Yearly"),
)

_FIRESTORE_TYPE = _opts(
    ("FIRESTORE_NATIVE", "Firestore Native"),
    ("DATASTORE_MODE", "Datastore mode"),
)

_FIRESTORE_EDITION = _opts(
    ("STANDARD", "Standard"),
    ("ENTERPRISE", "Enterprise"),
)

_FIRESTORE_CONCURRENCY = _opts(
    ("OPTIMISTIC", "Optimistic"),
    ("PESSIMISTIC", "Pessimistic"),
    ("OPTIMISTIC_WITH_ENTITY_GROUPS", "Optimistic with entity groups"),
)

_FIRESTORE_PITR = _opts(
    ("POINT_IN_TIME_RECOVERY_ENABLED", "Enabled"),
    ("POINT_IN_TIME_RECOVERY_DISABLED", "Disabled"),
)

_FIRESTORE_DELETE_PROTECTION = _opts(
    ("DELETE_PROTECTION_ENABLED", "Enabled"),
    ("DELETE_PROTECTION_DISABLED", "Disabled"),
)

_FIRESTORE_APP_ENGINE = _opts(
    ("ENABLED", "Enabled"),
    ("DISABLED", "Disabled"),
)

_BIGTABLE_STORAGE_TYPE = _opts(
    ("SSD", "SSD"),
    ("HDD", "HDD"),
)

_BIGTABLE_INSTANCE_TYPE = _opts(
    ("PRODUCTION", "Production"),
    ("DEVELOPMENT", "Development"),
)

_PUBSUB_ENCODING = _opts(
    ("JSON", "JSON"),
    ("BINARY", "Binary"),
)

_PUBSUB_SCHEMA_TYPE = _opts(
    ("AVRO", "Avro"),
    ("PROTOCOL_BUFFER", "Protocol Buffer"),
)

_VPC_ROUTING_MODE = _opts(
    ("REGIONAL", "Regional"),
    ("GLOBAL", "Global"),
)

_SUBNET_ROLE = _opts(
    ("ACTIVE", "Active"),
    ("BACKUP", "Backup"),
)

_LB_SCHEME = _opts(
    ("EXTERNAL_MANAGED", "External (global, managed)"),
    ("EXTERNAL", "External (classic)"),
)

_LB_SSL_PROFILE = _opts(
    ("COMPATIBLE", "Compatible"),
    ("MODERN", "Modern"),
    ("RESTRICTED", "Restricted"),
    ("CUSTOM", "Custom"),
)

_LB_MIN_TLS = _opts(
    ("TLS_1_0", "TLS 1.0"),
    ("TLS_1_1", "TLS 1.1"),
    ("TLS_1_2", "TLS 1.2"),
)

_LB_CACHE_MODE = _opts(
    ("CACHE_ALL_STATIC", "Cache all static content"),
    ("USE_ORIGIN_HEADERS", "Use origin headers"),
    ("FORCE_CACHE_ALL", "Force cache all"),
)

# ── Registry ─────────────────────────────────────────────────────────

OPTIONS_REGISTRY: dict[tuple[NodeType, str], list[dict[str, str]]] = {
    # Cloud SQL
    (NodeType.CLOUD_SQL, "database_version"): _CLOUD_SQL_DATABASE_VERSIONS,
    (NodeType.CLOUD_SQL, "tier"): _CLOUD_SQL_TIERS,
    (NodeType.CLOUD_SQL, "edition"): _CLOUD_SQL_EDITIONS,
    (NodeType.CLOUD_SQL, "availability_type"): _AVAILABILITY_TYPES,
    (NodeType.CLOUD_SQL, "disk_type"): _CLOUD_SQL_DISK_TYPES,
    (NodeType.CLOUD_SQL, "activation_policy"): _CLOUD_SQL_ACTIVATION_POLICIES,
    (NodeType.CLOUD_SQL, "connector_enforcement"): _CLOUD_SQL_CONNECTOR_ENFORCEMENT,
    # Cloud Run
    (NodeType.CLOUD_RUN, "ingress"): _CLOUD_RUN_INGRESS,
    (NodeType.CLOUD_RUN, "execution_environment"): _CLOUD_RUN_EXECUTION_ENV,
    (NodeType.CLOUD_RUN, "launch_stage"): _CLOUD_RUN_LAUNCH_STAGE,
    (NodeType.CLOUD_RUN, "vpc_access.egress"): _CLOUD_RUN_VPC_EGRESS,
    # Cloud Run Job
    (NodeType.CLOUD_RUN_JOB, "execution_environment"): _CLOUD_RUN_EXECUTION_ENV,
    # Cloud Function
    (NodeType.CLOUD_FUNCTION, "runtime"): _CF_RUNTIMES,
    (NodeType.CLOUD_FUNCTION, "ingress"): _CF_INGRESS,
    (NodeType.CLOUD_FUNCTION, "vpc_connector_egress_settings"): _CF_VPC_EGRESS,
    (NodeType.CLOUD_FUNCTION, "event_trigger.retry_policy"): _CF_RETRY_POLICY,
    # GCS Bucket
    (NodeType.GCS_BUCKET, "location"): GCP_REGIONS + GCP_MULTI_REGIONS,
    (NodeType.GCS_BUCKET, "storage_class"): _GCS_STORAGE_CLASSES,
    (NodeType.GCS_BUCKET, "public_access_prevention"): _GCS_PUBLIC_ACCESS_PREVENTION,
    (NodeType.GCS_BUCKET, "autoclass.terminal_storage_class"): _GCS_AUTOCLASS_TERMINAL,
    # BigQuery
    (NodeType.BIGQUERY, "location"): GCP_REGIONS + GCP_MULTI_REGIONS,
    (NodeType.BIGQUERY, "storage_billing_model"): _BQ_STORAGE_BILLING,
    # BigQuery Table (child node)
    (NodeType.BIGQUERY_TABLE, "time_partitioning.type"): _BQ_TIME_PARTITIONING_TYPE,
    # Firestore
    (NodeType.FIRESTORE, "location_id"): GCP_REGIONS + GCP_MULTI_REGIONS,
    (NodeType.FIRESTORE, "type"): _FIRESTORE_TYPE,
    (NodeType.FIRESTORE, "database_edition"): _FIRESTORE_EDITION,
    (NodeType.FIRESTORE, "concurrency_mode"): _FIRESTORE_CONCURRENCY,
    (NodeType.FIRESTORE, "point_in_time_recovery_enablement"): _FIRESTORE_PITR,
    (NodeType.FIRESTORE, "delete_protection_state"): _FIRESTORE_DELETE_PROTECTION,
    (NodeType.FIRESTORE, "app_engine_integration_mode"): _FIRESTORE_APP_ENGINE,
    # Bigtable
    (NodeType.BIGTABLE, "cluster.storage_type"): _BIGTABLE_STORAGE_TYPE,
    (NodeType.BIGTABLE, "instance_type"): _BIGTABLE_INSTANCE_TYPE,
    # PubSub Topic
    (NodeType.PUBSUB_TOPIC, "schema_settings.encoding"): _PUBSUB_ENCODING,
    # PubSub Schema
    (NodeType.PUBSUB_SCHEMA, "type"): _PUBSUB_SCHEMA_TYPE,
    # VPC
    (NodeType.VPC, "routing_mode"): _VPC_ROUTING_MODE,
    # Subnet
    (NodeType.SUBNET, "region"): GCP_REGIONS,
    (NodeType.SUBNET, "role"): _SUBNET_ROLE,
    # VPC Connector
    (NodeType.VPC_CONNECTOR, "region"): GCP_REGIONS,
    # Cloud Task Queue
    (NodeType.CLOUD_TASK_QUEUE, "location"): GCP_REGIONS,
    # External LB
    (NodeType.EXTERNAL_LB, "scheme"): _LB_SCHEME,
    (NodeType.EXTERNAL_LB, "ssl_policy.profile"): _LB_SSL_PROFILE,
    (NodeType.EXTERNAL_LB, "ssl_policy.min_tls_version"): _LB_MIN_TLS,
    (NodeType.EXTERNAL_LB, "cdn_policy.cache_mode"): _LB_CACHE_MODE,
}
