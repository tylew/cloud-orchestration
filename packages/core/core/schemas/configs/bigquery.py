from enum import StrEnum

from pydantic import BaseModel, model_validator


class BqColumnMode(StrEnum):
    NULLABLE = "NULLABLE"
    REQUIRED = "REQUIRED"
    REPEATED = "REPEATED"


class BqColumnType(StrEnum):
    STRING = "STRING"
    INTEGER = "INTEGER"
    INT64 = "INT64"
    FLOAT64 = "FLOAT64"
    BOOL = "BOOL"
    TIMESTAMP = "TIMESTAMP"
    DATE = "DATE"
    DATETIME = "DATETIME"
    NUMERIC = "NUMERIC"
    JSON = "JSON"
    RECORD = "RECORD"
    BYTES = "BYTES"
    FLOAT = "FLOAT"
    BIGNUMERIC = "BIGNUMERIC"
    BOOLEAN = "BOOLEAN"
    TIME = "TIME"
    GEOGRAPHY = "GEOGRAPHY"


class BqColumn(BaseModel):
    name: str
    type: BqColumnType = BqColumnType.STRING
    mode: BqColumnMode = BqColumnMode.NULLABLE
    description: str | None = None
    fields: list["BqColumn"] = []  # recursive for RECORD type


class BqTimePartitioning(BaseModel):
    type: str = "DAY"
    field: str | None = None
    expiration_ms: int | None = None
    require_partition_filter: bool = False


class BqRangePartitioningRange(BaseModel):
    start: int
    end: int
    interval: int


class BqRangePartitioning(BaseModel):
    field: str
    range: BqRangePartitioningRange


class BqTable(BaseModel):
    table_id: str
    schema_file: str | None = None
    description: str | None = None
    deletion_protection: bool = True
    time_partitioning: BqTimePartitioning | None = None
    range_partitioning: BqRangePartitioning | None = None
    clustering: list[str] | None = None
    labels: dict[str, str] = {}
    columns: list[BqColumn] = []


class BqView(BaseModel):
    table_id: str
    query: str
    use_legacy_sql: bool = False


class BqCustomSql(BaseModel):
    name: str
    description: str | None = None
    sql: str = ""


class BigQueryTableConfig(BaseModel):
    """Config for a flat bigquery_table node (child of a BigQuery dataset)."""
    parentRef: str    # slug of parent bigquery dataset node
    name: str         # table_id in BQ terms
    description: str = ""
    columns: list[BqColumn] = []
    time_partitioning: BqTimePartitioning | None = None
    range_partitioning: BqRangePartitioning | None = None
    clustering: list[str] = []  # up to 4 column names
    deletion_protection: bool = True

    @model_validator(mode="after")
    def validate_config(self):
        if not self.parentRef:
            raise ValueError("parentRef is required")
        if len(self.clustering) > 4:
            raise ValueError("BigQuery supports max 4 clustering columns")
        return self


class StorageBillingModel(StrEnum):
    LOGICAL = "LOGICAL"
    PHYSICAL = "PHYSICAL"


class BigQueryConfig(BaseModel):
    location: str = "US"
    friendly_name: str | None = None
    description: str | None = None
    default_table_expiration_ms: int | None = None
    default_partition_expiration_ms: int | None = None
    delete_contents_on_destroy: bool = False
    max_time_travel_hours: int = 168
    is_case_insensitive: bool = False
    default_collation: str | None = None
    storage_billing_model: StorageBillingModel = StorageBillingModel.LOGICAL
    labels: dict[str, str] = {}
    tables: list[BqTable] = []
    views: list[BqView] = []
    custom_sql: list[BqCustomSql] = []
