from pydantic import BaseModel, Field


class PubsubSchemaSettings(BaseModel):
    model_config = {"populate_by_name": True}

    schema_: str | None = Field(default=None, alias="schema")
    encoding: str = "JSON"


class PubsubMessageStoragePolicy(BaseModel):
    allowed_persistence_regions: list[str] = []
    enforce_in_transit: bool = False


class PubsubTopicConfig(BaseModel):
    message_retention_duration: str | None = "86400s"
    kms_key_name: str | None = None
    schema_settings: PubsubSchemaSettings | None = None
    message_storage_policy: PubsubMessageStoragePolicy | None = None
    labels: dict[str, str] = {}
