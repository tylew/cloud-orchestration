from typing import Literal

from pydantic import BaseModel

from .env_vars import EnvVarEntry


class CloudRunVpcAccess(BaseModel):
    connector: str | None = None
    egress: str = "PRIVATE_RANGES_ONLY"


class CloudRunNetworkInterface(BaseModel):
    network: str
    subnetwork: str
    tags: list[str] = []


class CloudRunVpcAccessDirect(BaseModel):
    network: str | None = None
    subnetwork: str | None = None
    network_interfaces: list[CloudRunNetworkInterface] = []


class CloudRunVolumeSecretItem(BaseModel):
    version: str = "latest"
    path: str
    mode: int | None = None


class CloudRunVolumeSecret(BaseModel):
    secret: str
    items: list[CloudRunVolumeSecretItem] = []


class CloudRunEmptyDir(BaseModel):
    medium: str | None = None
    size_limit: str | None = None


class CloudRunVolume(BaseModel):
    name: str
    secret: CloudRunVolumeSecret | None = None
    empty_dir: CloudRunEmptyDir | None = None


class CloudRunVolumeMount(BaseModel):
    name: str
    mount_path: str


class CloudRunHttpGet(BaseModel):
    path: str
    port: int | None = None


class CloudRunProbe(BaseModel):
    http_get: CloudRunHttpGet | None = None
    initial_delay_seconds: int = 0
    period_seconds: int = 10
    timeout_seconds: int = 1
    failure_threshold: int = 3


class CloudRunTraffic(BaseModel):
    type: str = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    revision: str | None = None
    percent: int = 100
    tag: str | None = None


class CloudRunBinaryAuth(BaseModel):
    breakglass_justification: str | None = None
    use_default: bool = False


class EventarcMatchingCriteria(BaseModel):
    attribute: str
    value: str
    operator: str | None = None


class EventarcTransport(BaseModel):
    pubsub_topic: str | None = None


class EventarcTriggerConfig(BaseModel):
    matching_criteria: list[EventarcMatchingCriteria] = []
    transport: EventarcTransport | None = None
    service_account_email: str | None = None
    location: str | None = None


class FieldRef(BaseModel):
    """Typed reference to a field on a storage node."""
    path: str  # e.g., "users.email" or "users/{id}/orders.total"
    access: str = "read"  # "read" | "write" | "read_write"


class WorkflowDbRef(BaseModel):
    """Structured reference to a database node with field-level detail (per D-08)."""
    node_name: str
    operation: str = ""  # "read" | "write" | "read_write"
    collections: list[str] = []  # Firestore collections or SQL tables
    fields: list[str | FieldRef] = []  # Field-level detail for schema contracts
    description: str = ""


class WorkflowSecretRef(BaseModel):
    """Structured reference to a secret mapped to env var (per D-08)."""
    secret_node: str
    env_var: str
    description: str = ""


class WorkflowTaskDispatch(BaseModel):
    """Structured task dispatch to Cloud Tasks queue (per D-08)."""
    queue_node: str
    payload_description: str = ""


class WorkflowPubSubRef(BaseModel):
    """Structured pub/sub messaging reference (per D-08)."""
    topic_node: str
    direction: str = "publish"  # "publish" | "subscribe"
    message_description: str = ""


class WorkflowInvokeRef(BaseModel):
    """Structured invocation of another compute node."""
    target_node: str
    description: str = ""


class WorkflowDefinition(BaseModel):
    """Comprehensive behavioral interface for compute nodes (per D-07).

    Structured part covers typed references to other resources.
    Free-form part captures business logic for the AI code agent (per D-10).
    """
    description: str = ""
    db_refs: list[WorkflowDbRef] = []
    secret_refs: list[WorkflowSecretRef] = []
    task_dispatches: list[WorkflowTaskDispatch] = []
    pubsub_refs: list[WorkflowPubSubRef] = []
    invoke_refs: list[WorkflowInvokeRef] = []
    behavior: str = ""  # Free-form behavioral logic (per D-10)


class CloudRunConfig(BaseModel):
    mode: Literal["workflow", "code_editor", "image_url"] | None = None
    image: str = ""
    port: int = 8080
    cpu: str = "1000m"
    memory: str = "512Mi"
    cpu_idle: bool = True
    startup_cpu_boost: bool = False
    min_instances: int = 0
    max_instances: int = 100
    timeout: str = "300s"
    max_concurrent_requests: int = 80
    execution_environment: str = "EXECUTION_ENVIRONMENT_GEN2"
    session_affinity: bool = False
    ingress: str = "INGRESS_TRAFFIC_ALL"
    vpc_access: CloudRunVpcAccess | None = None
    vpc_access_direct: CloudRunVpcAccessDirect | None = None
    env_vars: list[EnvVarEntry] = []
    volume_mounts: list[CloudRunVolumeMount] = []
    volumes: list[CloudRunVolume] = []
    liveness_probe: CloudRunProbe | None = None
    startup_probe: CloudRunProbe | None = None
    service_account: str = ""
    labels: dict[str, str] = {}
    annotations: dict[str, str] = {}
    client: str | None = None
    client_version: str | None = None
    traffic: list[CloudRunTraffic] = []
    binary_authorization: CloudRunBinaryAuth | None = None
    custom_audiences: list[str] = []
    public: bool = False
    eventarc_triggers: list[EventarcTriggerConfig] = []
    workflow: WorkflowDefinition | None = None
