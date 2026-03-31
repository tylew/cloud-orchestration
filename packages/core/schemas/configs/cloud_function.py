from typing import Literal

from pydantic import BaseModel

from .env_vars import EnvVarEntry


class CfStorageSource(BaseModel):
    bucket: str
    object: str
    generation: int | None = None


class CfRepoSource(BaseModel):
    repo_name: str
    branch_name: str | None = None
    dir: str | None = None
    tag_name: str | None = None
    commit_sha: str | None = None
    invert_regex: bool = False


class CfSource(BaseModel):
    storage_source: CfStorageSource | None = None
    repo_source: CfRepoSource | None = None


class CfSecretVolumeVersion(BaseModel):
    version: str = "latest"
    path: str


class CfSecretVolume(BaseModel):
    mount_path: str
    project_id: str | None = None
    secret: str
    versions: list[CfSecretVolumeVersion] = []


class CfSecretEnvVar(BaseModel):
    """Secret environment variable — references a secret in Secret Manager."""
    key: str
    project_id: str | None = None
    secret: str
    version: str = "latest"


class CfEventFilter(BaseModel):
    attribute: str
    value: str
    operator: str | None = None


class CfEventTrigger(BaseModel):
    trigger_region: str | None = None
    event_type: str
    pubsub_topic: str | None = None
    retry_policy: str = "RETRY_POLICY_RETRY"
    service_account_email: str | None = None
    event_filters: list[CfEventFilter] = []


class CfDirectVpcNetworkInterface(BaseModel):
    network: str | None = None
    subnetwork: str | None = None
    tags: list[str] = []


class CfBuildConfig(BaseModel):
    docker_repository: str | None = None
    worker_pool: str | None = None
    service_account: str | None = None
    environment_variables: dict[str, str] = {}
    automatic_update_policy: bool = False
    on_deploy_update_policy: bool = False


class CloudFunctionConfig(BaseModel):
    # --- Function-level ---
    description: str = ""
    runtime: str
    entry_point: str
    kms_key_name: str | None = None
    labels: dict[str, str] = {}
    source: CfSource | None = None
    # Auto-derived by pipeline — user doesn't set these
    source_bucket: str = ""
    source_object: str = "source.zip"
    # --- Service config ---
    cpu: str = "1"
    memory: str = "256Mi"
    timeout_seconds: int = 60
    min_instances: int = 0
    max_instances: int = 100
    max_concurrent_requests: int = 1
    available_cpu: str | None = None
    ingress: str = "ALLOW_ALL"
    all_traffic_on_latest_revision: bool = True
    service_account: str = ""
    vpc_connector: str | None = None
    vpc_connector_egress_settings: str = "PRIVATE_RANGES_ONLY"
    direct_vpc_network_interface: CfDirectVpcNetworkInterface | None = None
    direct_vpc_egress: str | None = None
    binary_authorization_policy: str | None = None
    # --- Env, secrets ---
    env_vars: list[EnvVarEntry] = []
    environment_variables: dict[str, str] = {}
    secret_environment_variables: list[CfSecretEnvVar] = []
    secret_volumes: list[CfSecretVolume] = []
    # --- Triggers ---
    event_trigger: CfEventTrigger | None = None
    build_config: CfBuildConfig | None = None
    # --- Platform-specific ---
    mode: Literal["workflow", "code_editor", "image_url"] | None = None
