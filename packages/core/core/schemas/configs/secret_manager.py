from pydantic import BaseModel


class SecretTopic(BaseModel):
    name: str  # projects/*/topics/*


class SecretManagerConfig(BaseModel):
    secret_id: str = ""
    description: str = ""
    replication: str = "auto"  # auto | user_managed
    replication_locations: list[str] = []  # for user_managed
    rotation_period: str = ""  # e.g. "7776000s" (90 days)
    expire_time: str = ""  # RFC3339 timestamp
    ttl: str = ""  # e.g. "86400s"
    version_aliases: dict[str, str] = {}  # alias -> version number
    version_destroy_ttl: str = ""  # e.g. "2592000s" (30 days)
    annotations: dict[str, str] = {}
    topics: list[SecretTopic] = []
    labels: dict[str, str] = {}
    # Secret value management
    value: str = ""  # the actual secret value (stored locally, never in TF)
    value_provided: bool = False  # whether the value has been set
    pending_email: str = ""  # email to send secure link for value provision
