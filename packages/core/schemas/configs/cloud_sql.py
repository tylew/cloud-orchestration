from enum import StrEnum

from pydantic import BaseModel, model_validator


class SqlColumnType(StrEnum):
    INTEGER = "INTEGER"
    BIGINT = "BIGINT"
    SERIAL = "SERIAL"
    VARCHAR = "VARCHAR"
    TEXT = "TEXT"
    BOOLEAN = "BOOLEAN"
    TIMESTAMP = "TIMESTAMP"
    TIMESTAMPTZ = "TIMESTAMPTZ"
    DATE = "DATE"
    NUMERIC = "NUMERIC"
    JSON = "JSON"
    JSONB = "JSONB"
    UUID = "UUID"
    SMALLINT = "SMALLINT"
    DECIMAL = "DECIMAL"
    FLOAT = "FLOAT"
    DOUBLE = "DOUBLE"
    CHAR = "CHAR"
    DATETIME = "DATETIME"
    TIME = "TIME"
    BLOB = "BLOB"
    ENUM = "ENUM"


class SqlColumn(BaseModel):
    name: str
    type: SqlColumnType = SqlColumnType.TEXT
    length: int | None = None
    nullable: bool = True
    primary_key: bool = False
    unique: bool = False
    default: str | None = None
    references: str | None = None  # e.g. "users(id)"


class SqlTable(BaseModel):
    name: str
    columns: list[SqlColumn] = []


class SqlCustomDdl(BaseModel):
    name: str
    description: str | None = None
    sql: str = ""


class SqlLocationPreference(BaseModel):
    zone: str | None = None
    secondary_zone: str | None = None


class SqlDenyMaintenancePeriod(BaseModel):
    start_date: str
    end_date: str
    time: str = "00:00:00"


class SqlAuthorizedNetwork(BaseModel):
    name: str | None = None
    value: str
    expiration_time: str | None = None


class SqlPscConfig(BaseModel):
    psc_enabled: bool = False
    allowed_consumer_projects: list[str] = []


class SqlIpConfiguration(BaseModel):
    ipv4_enabled: bool = False
    private_network: str | None = None
    require_ssl: bool = True
    ssl_mode: str | None = None
    server_ca_mode: str | None = None
    allocated_ip_range: str | None = None
    enable_private_path_for_google_cloud_services: bool = True
    authorized_networks: list[SqlAuthorizedNetwork] = []
    psc_config: SqlPscConfig | None = None


class SqlBackupConfiguration(BaseModel):
    enabled: bool = True
    point_in_time_recovery_enabled: bool = True
    start_time: str = "03:00"
    transaction_log_retention_days: int = 7
    retained_backups: int = 7
    retention_unit: str = "COUNT"


class SqlDatabase(BaseModel):
    name: str
    charset: str = "UTF8"
    collation: str = "en_US.UTF8"
    tables: list[SqlTable] = []
    custom_ddl: list[SqlCustomDdl] = []


class CloudSqlDatabaseConfig(BaseModel):
    """Config for a flat cloud_sql_database node (child of a Cloud SQL instance)."""
    parentRef: str    # slug of parent cloud_sql instance node
    name: str
    charset: str = "UTF8"
    collation: str = "en_US.UTF8"

    @model_validator(mode="after")
    def validate_config(self):
        if not self.parentRef:
            raise ValueError("parentRef is required")
        return self


class CloudSqlTableConfig(BaseModel):
    """Config for a flat cloud_sql_table node (child of a cloud_sql_database).
    Workflow documentation only -- NO Terraform generation.
    """
    parentRef: str    # slug of parent cloud_sql_database node
    name: str
    columns: list[SqlColumn] = []

    @model_validator(mode="after")
    def validate_config(self):
        if not self.parentRef:
            raise ValueError("parentRef is required")
        return self


class SqlFlag(BaseModel):
    name: str
    value: str


class SqlInsightsConfig(BaseModel):
    query_insights_enabled: bool = True
    query_plans_per_minute: int = 5
    query_string_length: int = 1024
    record_application_tags: bool = True
    record_client_address: bool = True


class SqlMaintenanceWindow(BaseModel):
    day: int = 7
    hour: int = 3
    update_track: str = "stable"


class SqlDataCacheConfig(BaseModel):
    data_cache_enabled: bool = False


class SqlPasswordValidationPolicy(BaseModel):
    enable_password_policy: bool = False
    min_length: int | None = None
    complexity: str | None = None
    reuse_interval: int | None = None
    disallow_username_substring: bool = False
    password_change_interval: str | None = None


class CloudSqlConfig(BaseModel):
    database_version: str
    tier: str
    edition: str | None = None
    availability_type: str = "ZONAL"
    activation_policy: str | None = None
    collation: str | None = None
    time_zone: str | None = None
    connector_enforcement: str | None = None
    disk_size: int = 10
    disk_type: str = "PD_SSD"
    disk_autoresize: bool = True
    disk_autoresize_limit: int = 0
    deletion_protection: bool = True
    deletion_protection_enabled: bool = False
    encryption_key_name: str | None = None
    root_password: str | None = None
    user_labels: dict[str, str] = {}
    backup_configuration: SqlBackupConfiguration | None = None
    ip_configuration: SqlIpConfiguration | None = None
    databases: list[SqlDatabase] = []
    flags: list[SqlFlag] = []
    insights_config: SqlInsightsConfig | None = None
    maintenance_window: SqlMaintenanceWindow | None = None
    location_preference: SqlLocationPreference | None = None
    deny_maintenance_period: SqlDenyMaintenancePeriod | None = None
    data_cache_config: SqlDataCacheConfig | None = None
    password_validation_policy: SqlPasswordValidationPolicy | None = None
