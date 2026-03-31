from pydantic import BaseModel


class TaskQueueRateLimits(BaseModel):
    max_dispatches_per_second: float = 50
    max_concurrent_dispatches: int = 20
    max_burst_size: int | None = None


class TaskQueueRetryConfig(BaseModel):
    max_attempts: int = 100
    max_retry_duration: str | None = None
    min_backoff: str = "1s"
    max_backoff: str = "300s"
    max_doublings: int = 16


class TaskQueueLoggingConfig(BaseModel):
    sampling_ratio: float = 1.0


class TaskQueueAppEngineRouting(BaseModel):
    service: str | None = None
    version: str | None = None
    instance: str | None = None


class TaskQueueHttpTargetPathOverride(BaseModel):
    path: str = ""


class TaskQueueHttpTargetQueryOverride(BaseModel):
    query_params: str = ""


class TaskQueueHttpTargetUriOverride(BaseModel):
    scheme: str | None = None
    host: str | None = None
    port: int | None = None
    path_override: TaskQueueHttpTargetPathOverride | None = None
    query_override: TaskQueueHttpTargetQueryOverride | None = None
    uri_override_enforce_mode: str = "ALWAYS"


class TaskQueueHttpTargetHeader(BaseModel):
    key: str
    value: str


class TaskQueueHttpTargetHeaderOverride(BaseModel):
    header: TaskQueueHttpTargetHeader


class TaskQueueHttpTargetOAuthToken(BaseModel):
    service_account_email: str
    scope: str | None = None


class TaskQueueHttpTargetOidcToken(BaseModel):
    service_account_email: str
    audience: str | None = None


class TaskQueueHttpTarget(BaseModel):
    http_method: str | None = None
    uri_override: TaskQueueHttpTargetUriOverride | None = None
    header_overrides: list[TaskQueueHttpTargetHeaderOverride] = []
    oauth_token: TaskQueueHttpTargetOAuthToken | None = None
    oidc_token: TaskQueueHttpTargetOidcToken | None = None


class CloudTaskQueueConfig(BaseModel):
    location: str
    rate_limits: TaskQueueRateLimits | None = None
    retry_config: TaskQueueRetryConfig | None = None
    stackdriver_logging_config: TaskQueueLoggingConfig | None = None
    app_engine_routing_override: TaskQueueAppEngineRouting | None = None
    http_target: TaskQueueHttpTarget | None = None
    desired_state: str | None = None
