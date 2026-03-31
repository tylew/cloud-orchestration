from typing import Literal

from pydantic import BaseModel
from .cloud_run import (
    CloudRunVpcAccess,
    CloudRunVpcAccessDirect,
    CloudRunNetworkInterface,
    CloudRunVolume, CloudRunVolumeMount, CloudRunBinaryAuth,
    CloudRunProbe, CloudRunNodeSelector,
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
    # --- Container fields ---
    container_name: str | None = None
    command: list[str] = []
    args: list[str] = []
    working_dir: str | None = None
    container_depends_on: list[str] = []
    # --- Resources ---
    cpu: str = "1000m"
    memory: str = "512Mi"
    gpu: str | None = None
    # --- Task template ---
    timeout: str = "600s"
    max_retries: int = 3
    task_count: int = 1
    parallelism: int = 1
    execution_environment: str = "EXECUTION_ENVIRONMENT_GEN2"
    encryption_key: str | None = None
    service_account: str = ""
    # --- Networking ---
    vpc_access: CloudRunVpcAccess | None = None
    vpc_access_direct: CloudRunVpcAccessDirect | None = None
    # --- GPU ---
    node_selector: CloudRunNodeSelector | None = None
    gpu_zonal_redundancy_disabled: bool = False
    # --- Env, volumes, probes ---
    env_vars: list[EnvVarEntry] = []
    volumes: list[CloudRunVolume] = []
    volume_mounts: list[CloudRunVolumeMount] = []
    startup_probe: CloudRunProbe | None = None
    # --- Job-level ---
    labels: dict[str, str] = {}
    annotations: dict[str, str] = {}
    client: str | None = None
    client_version: str | None = None
    launch_stage: str | None = None
    binary_authorization: CloudRunBinaryAuth | None = None
    scheduler_triggers: list[SchedulerTriggerConfig] = []
