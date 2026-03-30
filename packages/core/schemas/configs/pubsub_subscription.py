from pydantic import BaseModel, model_validator
from typing import Self


class PubsubRetryPolicy(BaseModel):
    minimum_backoff: str = "10s"
    maximum_backoff: str = "600s"


class PubsubDeadLetterPolicy(BaseModel):
    dead_letter_topic: str
    max_delivery_attempts: int = 5


class PubsubExpirationPolicy(BaseModel):
    ttl: str = "2678400s"


class PubsubOidcToken(BaseModel):
    service_account_email: str
    audience: str | None = None


class PubsubNoWrapper(BaseModel):
    write_metadata: bool = True


class PubsubPushConfig(BaseModel):
    push_endpoint: str
    attributes: dict[str, str] = {}
    oidc_token: PubsubOidcToken | None = None
    no_wrapper: PubsubNoWrapper | None = None


class PubsubBigQueryConfig(BaseModel):
    table: str
    use_topic_schema: bool = False
    use_table_schema: bool = False
    write_metadata: bool = True
    drop_unknown_fields: bool = False
    service_account_email: str | None = None


class PubsubCloudStorageAvroConfig(BaseModel):
    write_metadata: bool = True
    use_topic_schema: bool = False


class PubsubCloudStorageConfig(BaseModel):
    bucket: str
    filename_prefix: str | None = None
    filename_suffix: str | None = None
    filename_datetime_format: str | None = None
    max_duration: str = "300s"
    max_bytes: int | None = None
    max_messages: int | None = None
    avro_config: PubsubCloudStorageAvroConfig | None = None
    service_account_email: str | None = None


class PubsubSubscriptionConfig(BaseModel):
    topic: str
    ack_deadline_seconds: int = 10
    message_retention_duration: str = "604800s"
    retain_acked_messages: bool = False
    enable_message_ordering: bool = False
    enable_exactly_once_delivery: bool = False
    filter: str | None = None
    retry_policy: PubsubRetryPolicy | None = None
    dead_letter_policy: PubsubDeadLetterPolicy | None = None
    expiration_policy: PubsubExpirationPolicy | None = None
    push_config: PubsubPushConfig | None = None
    bigquery_config: PubsubBigQueryConfig | None = None
    cloud_storage_config: PubsubCloudStorageConfig | None = None
    labels: dict[str, str] = {}

    @model_validator(mode="after")
    def check_mutually_exclusive_delivery(self) -> Self:
        delivery_configs = [
            self.push_config is not None,
            self.bigquery_config is not None,
            self.cloud_storage_config is not None,
        ]
        if sum(delivery_configs) > 1:
            raise ValueError(
                "Only one of push_config, bigquery_config, or cloud_storage_config may be set"
            )
        return self
