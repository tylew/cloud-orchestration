from typing import Literal

from pydantic import BaseModel
from .cloud_run import (
    CloudRunVpcAccess,
    CloudRunVolume, CloudRunVolumeMount, CloudRunBinaryAuth,
    WorkflowDefinition,
)
from .env_vars import EnvVarEntry


class SchedulerRetryConfig(BaseModel):
    retry_count: int = 0
    max_retry_duration: str | None = None


class SchedulerTriggerConfig(BaseModel):
    schedule: str
    time_zone: str = "UTC"
    paused: bool = False
    retry_config: SchedulerRetryConfig | None = None


class CloudRunJobConfig(BaseModel):
    mode: Literal["workflow", "code_editor", "image_url"] | None = None
    image: str = ""
    cpu: str = "1000m"
    memory: str = "512Mi"
    timeout: str = "600s"
    max_retries: int = 3
    task_count: int = 1
    parallelism: int = 1
    execution_environment: str = "EXECUTION_ENVIRONMENT_GEN2"
    service_account: str = ""
    vpc_access: CloudRunVpcAccess | None = None
    env_vars: list[EnvVarEntry] = []
    volumes: list[CloudRunVolume] = []
    volume_mounts: list[CloudRunVolumeMount] = []
    command: list[str] = []
    args: list[str] = []
    labels: dict[str, str] = {}
    annotations: dict[str, str] = {}
    binary_authorization: CloudRunBinaryAuth | None = None
    scheduler_triggers: list[SchedulerTriggerConfig] = []
    workflow: WorkflowDefinition | None = None
