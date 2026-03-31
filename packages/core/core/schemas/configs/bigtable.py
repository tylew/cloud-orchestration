from pydantic import BaseModel


class BigtableCluster(BaseModel):
    cluster_id: str
    zone: str
    num_nodes: int = 3
    storage_type: str = "SSD"
    kms_key_name: str | None = None


class BigtableAutoscaling(BaseModel):
    min_nodes: int = 3
    max_nodes: int = 10
    cpu_target: int = 70
    storage_target: int | None = None


class BigtableGcPolicy(BaseModel):
    mode: str | None = None
    max_age: str | None = None
    max_version: int | None = None


class BigtableColumnQualifier(BaseModel):
    qualifier: str
    description: str | None = None
    value_type: str | None = None  # e.g. "string", "int64", "bytes"


class BigtableColumnFamily(BaseModel):
    family: str
    gc_policy: BigtableGcPolicy
    columns: list[BigtableColumnQualifier] = []


class BigtableTable(BaseModel):
    table_id: str
    split_keys: list[str] = []
    deletion_protection: str = "PROTECTED"
    column_families: list[BigtableColumnFamily]


class BigtableConfig(BaseModel):
    instance_id: str
    display_name: str | None = None
    instance_type: str = "PRODUCTION"
    deletion_protection: bool = True
    force_destroy: bool = False
    cluster: BigtableCluster
    autoscaling: BigtableAutoscaling | None = None
    tables: list[BigtableTable] = []
