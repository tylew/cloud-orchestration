from pydantic import BaseModel


class GcsVersioning(BaseModel):
    enabled: bool = False


class LifecycleAction(BaseModel):
    type: str
    storage_class: str | None = None


class LifecycleCondition(BaseModel):
    age: int | None = None
    num_newer_versions: int | None = None
    with_state: str | None = None
    created_before: str | None = None
    matches_prefix: list[str] = []
    matches_suffix: list[str] = []
    matches_storage_class: list[str] = []
    days_since_noncurrent_time: int | None = None
    days_since_custom_time: int | None = None
    custom_time_before: str | None = None
    noncurrent_time_before: str | None = None


class LifecycleRule(BaseModel):
    action: LifecycleAction
    condition: LifecycleCondition


class GcsCors(BaseModel):
    origin: list[str] = []
    method: list[str] = []
    response_header: list[str] = []
    max_age_seconds: int = 3600


class GcsRetentionPolicy(BaseModel):
    retention_period: int = 0
    is_locked: bool = False


class GcsEncryption(BaseModel):
    default_kms_key_name: str


class GcsLogging(BaseModel):
    log_bucket: str
    log_object_prefix: str | None = None


class GcsWebsite(BaseModel):
    main_page_suffix: str | None = None
    not_found_page: str | None = None


class GcsAutoclass(BaseModel):
    enabled: bool = False
    terminal_storage_class: str | None = None  # NEARLINE | ARCHIVE


class GcsSoftDeletePolicy(BaseModel):
    retention_duration_seconds: int = 604800  # 7 days default


class GcsBucketConfig(BaseModel):
    location: str
    storage_class: str = "STANDARD"
    uniform_bucket_level_access: bool = True
    public_access_prevention: str = "inherited"  # inherited | enforced
    force_destroy: bool = False
    requester_pays: bool = False
    default_event_based_hold: bool = False
    versioning: GcsVersioning | None = None
    lifecycle_rule: list[LifecycleRule] | None = None
    cors: list[GcsCors] | None = None
    retention_policy: GcsRetentionPolicy | None = None
    encryption: GcsEncryption | None = None
    logging: GcsLogging | None = None
    website: GcsWebsite | None = None
    autoclass: GcsAutoclass | None = None
    soft_delete_policy: GcsSoftDeletePolicy | None = None
    labels: dict[str, str] = {}
