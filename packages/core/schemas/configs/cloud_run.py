from typing import Literal

from pydantic import BaseModel

from .env_vars import EnvVarEntry


# ── VPC Access ───────────────────────────────────────────────────────

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


# ── Volumes ──────────────────────────────────────────────────────────

class CloudRunVolumeSecretItem(BaseModel):
    version: str = "latest"
    path: str
    mode: int | None = None


class CloudRunVolumeSecret(BaseModel):
    secret: str
    default_mode: int | None = None
    items: list[CloudRunVolumeSecretItem] = []


class CloudRunEmptyDir(BaseModel):
    medium: str | None = None
    size_limit: str | None = None


class CloudRunCloudSqlInstance(BaseModel):
    instances: list[str] = []


class CloudRunGcsVolume(BaseModel):
    bucket: str
    read_only: bool = False
    mount_options: list[str] = []


class CloudRunNfsVolume(BaseModel):
    server: str
    path: str = ""
    read_only: bool = False


class CloudRunVolume(BaseModel):
    name: str
    secret: CloudRunVolumeSecret | None = None
    empty_dir: CloudRunEmptyDir | None = None
    cloud_sql_instance: CloudRunCloudSqlInstance | None = None
    gcs: CloudRunGcsVolume | None = None
    nfs: CloudRunNfsVolume | None = None


class CloudRunVolumeMount(BaseModel):
    name: str
    mount_path: str
    sub_path: str | None = None


# ── Probes ───────────────────────────────────────────────────────────

class CloudRunHttpHeader(BaseModel):
    name: str
    value: str = ""


class CloudRunHttpGet(BaseModel):
    path: str = "/"
    port: int | None = None
    http_headers: list[CloudRunHttpHeader] = []


class CloudRunGrpcProbe(BaseModel):
    port: int | None = None
    service: str | None = None


class CloudRunTcpSocket(BaseModel):
    port: int


class CloudRunProbe(BaseModel):
    http_get: CloudRunHttpGet | None = None
    grpc: CloudRunGrpcProbe | None = None
    tcp_socket: CloudRunTcpSocket | None = None
    initial_delay_seconds: int = 0
    period_seconds: int = 10
    timeout_seconds: int = 1
    failure_threshold: int = 3


class CloudRunReadinessProbe(BaseModel):
    """Readiness probe — slightly different fields from liveness/startup."""
    http_get: CloudRunHttpGet | None = None
    grpc: CloudRunGrpcProbe | None = None
    timeout_seconds: int = 1
    period_seconds: int = 10
    failure_threshold: int = 3
    success_threshold: int = 2


# ── Traffic & Auth ───────────────────────────────────────────────────

class CloudRunTraffic(BaseModel):
    type: str = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    revision: str | None = None
    percent: int = 100
    tag: str | None = None


class CloudRunBinaryAuth(BaseModel):
    breakglass_justification: str | None = None
    use_default: bool = False
    policy: str | None = None


# ── Service-level scaling ────────────────────────────────────────────

class CloudRunServiceScaling(BaseModel):
    """Service-level scaling (separate from template revision scaling)."""
    max_instance_count: int | None = None


# ── Node selector / GPU ──────────────────────────────────────────────

class CloudRunNodeSelector(BaseModel):
    accelerator: str


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
    # --- Service-level fields ---
    description: str = ""
    image: str = ""
    port: int = 8080
    ingress: str = "INGRESS_TRAFFIC_ALL"
    launch_stage: str | None = None
    default_uri_disabled: bool = False
    invoker_iam_disabled: bool = False
    iap_enabled: bool = False
    labels: dict[str, str] = {}
    annotations: dict[str, str] = {}
    client: str | None = None
    client_version: str | None = None
    scaling: CloudRunServiceScaling | None = None
    binary_authorization: CloudRunBinaryAuth | None = None
    custom_audiences: list[str] = []
    traffic: list[CloudRunTraffic] = []
    public: bool = False
    # --- Template / revision fields ---
    cpu: str = "1000m"
    memory: str = "512Mi"
    gpu: str | None = None
    cpu_idle: bool = True
    startup_cpu_boost: bool = False
    min_instances: int = 0
    max_instances: int = 100
    timeout: str = "300s"
    max_concurrent_requests: int = 80
    execution_environment: str = "EXECUTION_ENVIRONMENT_GEN2"
    session_affinity: bool = False
    encryption_key: str | None = None
    health_check_disabled: bool = False
    gpu_zonal_redundancy_disabled: bool = False
    node_selector: CloudRunNodeSelector | None = None
    service_account: str = ""
    # --- Container fields ---
    container_name: str | None = None
    command: list[str] = []
    args: list[str] = []
    working_dir: str | None = None
    base_image_uri: str | None = None
    container_depends_on: list[str] = []
    # --- Networking ---
    vpc_access: CloudRunVpcAccess | None = None
    vpc_access_direct: CloudRunVpcAccessDirect | None = None
    # --- Env, volumes, probes ---
    env_vars: list[EnvVarEntry] = []
    volume_mounts: list[CloudRunVolumeMount] = []
    volumes: list[CloudRunVolume] = []
    liveness_probe: CloudRunProbe | None = None
    startup_probe: CloudRunProbe | None = None
    readiness_probe: CloudRunReadinessProbe | None = None
    # --- Eventarc ---
    eventarc_triggers: list[EventarcTriggerConfig] = []
    # --- Workflow (platform-specific) ---
    workflow: WorkflowDefinition | None = None
