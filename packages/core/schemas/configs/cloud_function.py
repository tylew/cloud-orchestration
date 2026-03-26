from typing import Literal

from pydantic import BaseModel

from .cloud_run import WorkflowDefinition
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


class CfSource(BaseModel):
    storage_source: CfStorageSource | None = None
    repo_source: CfRepoSource | None = None


class CfSecretEnvVar(BaseModel):
    key: str
    project_id: str | None = None
    secret: str
    version: str = "latest"


class CfSecretVolumeVersion(BaseModel):
    version: str = "latest"
    path: str


class CfSecretVolume(BaseModel):
    mount_path: str
    project_id: str | None = None
    secret: str
    versions: list[CfSecretVolumeVersion] = []


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


class CfBuildConfig(BaseModel):
    docker_repository: str | None = None
    worker_pool: str | None = None


class CloudFunctionConfig(BaseModel):
    runtime: str
    entry_point: str
    source: CfSource | None = None
    # Auto-derived by pipeline — user doesn't set these
    source_bucket: str = ""
    source_object: str = "source.zip"
    cpu: str = "1"
    memory: str = "256Mi"
    timeout_seconds: int = 60
    min_instances: int = 0
    max_instances: int = 100
    max_concurrent_requests: int = 1
    ingress: str = "ALLOW_ALL"
    service_account: str = ""
    vpc_connector: str | None = None
    vpc_connector_egress_settings: str = "PRIVATE_RANGES_ONLY"
    env_vars: list[EnvVarEntry] = []
    secret_volumes: list[CfSecretVolume] = []
    event_trigger: CfEventTrigger | None = None
    build_config: CfBuildConfig | None = None
    labels: dict[str, str] = {}
    mode: Literal["workflow", "code_editor", "image_url"] | None = None
    workflow: WorkflowDefinition | None = None
