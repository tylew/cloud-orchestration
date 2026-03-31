from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, model_validator


class FirestoreFieldType(StrEnum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    MAP = "map"
    ARRAY = "array"
    TIMESTAMP = "timestamp"
    GEOPOINT = "geopoint"
    REFERENCE = "reference"
    BYTES = "bytes"
    NULL = "null"
    INTEGER = "integer"
    FLOAT = "float"


class FirestoreField(BaseModel):
    name: str
    type: FirestoreFieldType = FirestoreFieldType.STRING
    description: str = ""
    required: bool = False
    array_of: FirestoreFieldType | None = None  # type of array elements
    subfields: list[FirestoreField] = []  # nested fields for map type


class FirestoreIdStrategy(StrEnum):
    AUTO = "auto"
    UUID = "uuid"
    CUSTOM = "custom"


class FirestoreCollection(BaseModel):
    path: str
    description: str = ""
    ttl_field: str = ""
    id_strategy: FirestoreIdStrategy = FirestoreIdStrategy.AUTO
    fields: list[FirestoreField] = []
    subcollections: list[FirestoreCollection] = []


class FirestoreCollectionConfig(BaseModel):
    """Config for a flat firestore_collection node (child of a Firestore DB node)."""
    parentRef: str                          # slug of parent firestore or firestore_collection node
    name: str                               # collection name (e.g. "users")
    description: str = ""
    id_strategy: FirestoreIdStrategy = FirestoreIdStrategy.AUTO
    ttl_field: str = ""                     # must reference a timestamp field in fields[]
    fields: list[FirestoreField] = []

    @model_validator(mode="after")
    def validate_ttl_field(self):
        if self.ttl_field:
            field_names = {f.name for f in self.fields}
            if self.ttl_field not in field_names:
                raise ValueError(f"ttl_field '{self.ttl_field}' not found in fields")
            ttl_f = next(f for f in self.fields if f.name == self.ttl_field)
            if ttl_f.type != FirestoreFieldType.TIMESTAMP:
                raise ValueError(f"ttl_field '{self.ttl_field}' must be a timestamp field")
        return self


class FirestoreIndexField(BaseModel):
    field_path: str
    order: str | None = "ASCENDING"
    array_config: str | None = None


class FirestoreIndex(BaseModel):
    collection: str
    query_scope: str = "COLLECTION"
    api_scope: str = "ANY_API"
    fields: list[FirestoreIndexField]


class FirestoreCmekConfig(BaseModel):
    kms_key_name: str


class FirestoreConfig(BaseModel):
    location_id: str = ""
    type: str = "FIRESTORE_NATIVE"  # FIRESTORE_NATIVE or DATASTORE_MODE — immutable after creation
    database_edition: str | None = None  # STANDARD or ENTERPRISE
    concurrency_mode: str = "OPTIMISTIC"
    app_engine_integration_mode: str = "DISABLED"
    point_in_time_recovery_enablement: str = "POINT_IN_TIME_RECOVERY_ENABLED"
    delete_protection_state: str = "DELETE_PROTECTION_ENABLED"
    cmek_config: FirestoreCmekConfig | None = None
    tags: dict[str, str] = {}
    # Enterprise edition features
    firestore_data_access_mode: str | None = None
    mongodb_compatible_data_access_mode: str | None = None
    realtime_updates_mode: str | None = None
    # Application-level schema (platform-specific, not Terraform fields)
    collections: list[FirestoreCollection] = []
    indexes: list[FirestoreIndex] = []
