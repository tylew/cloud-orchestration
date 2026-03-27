# Compute Category: Rigid Template

**Category:** Compute
**Types:** cloud_run, cloud_run_job, cloud_function
**Archetype:** Compute with Image (see [00-lifecycle-archetypes.md](../00-lifecycle-archetypes.md))
**Provider version:** Google Terraform Provider ~5.0
**Last verified:** 2026-03-26

---

## Cloud Run (`cloud_run`)

### Terraform Resource

- Resource: `google_cloud_run_v2_service`
- Provider version: ~5.0
- Last verified: 2026-03-26
- REGISTRY category: Compute
- is_compute: true
- iam_scope: resource
- iam_terraform_resource: `google_cloud_run_v2_service_iam_member`

### State Machine

Uses **Compute with Image** archetype. See [00-lifecycle-archetypes.md](../00-lifecycle-archetypes.md).

Key behavior: Image changes and template config changes create new revisions without destroying the resource. Only `name` and `location` are true ForceNew fields.

### Field Classification

#### Terraform-Mapped Fields

| Field | Type | Required | Default | Mutable | TF Argument | Validation |
|-------|------|----------|---------|---------|-------------|------------|
| image | string | Yes (error) | `""` | Yes (creates new revision) | `template.containers.image` | Non-empty when deploying |
| port | int | Warning | `8080` | Yes (creates new revision) | `template.containers.ports.container_port` | Valid port number |
| cpu | string | Warning | `"1000m"` | Yes (creates new revision) | `template.containers.resources.limits.cpu` | Valid CPU unit |
| memory | string | Warning | `"512Mi"` | Yes (creates new revision) | `template.containers.resources.limits.memory` | Valid memory unit |
| cpu_idle | bool | No | `true` | Yes (creates new revision) | `template.containers.resources.cpu_idle` | |
| startup_cpu_boost | bool | No | `false` | Yes (creates new revision) | `template.containers.resources.startup_cpu_boost` | |
| min_instances | int | No | `0` | Yes | `template.scaling.min_instance_count` | >= 0 |
| max_instances | int | No | `100` | Yes | `template.scaling.max_instance_count` | >= 1 |
| timeout | string | No | `"300s"` | Yes (creates new revision) | `template.timeout` | Valid duration |
| max_concurrent_requests | int | No | `80` | Yes (creates new revision) | `template.max_instance_request_concurrency` | >= 1 |
| execution_environment | string | No | `"EXECUTION_ENVIRONMENT_GEN2"` | Yes (creates new revision) | `template.execution_environment` | GEN1 or GEN2 |
| session_affinity | bool | No | `false` | Yes (creates new revision) | `template.session_affinity` | |
| ingress | string | No | `"INGRESS_TRAFFIC_ALL"` | Yes | `ingress` | Valid ingress setting |
| service_account | string | Yes (error) | `""` | Yes (creates new revision) | `template.service_account` | Must reference valid SA |
| labels | dict[str, str] | No | `{}` | Yes | `labels` | Valid label key/value |
| annotations | dict[str, str] | No | `{}` | Yes | `annotations` | Valid annotation key/value |
| client_version | string | No | `None` | Yes | `client_version` | |
| env_vars | list[EnvVarEntry] | No | `[]` | Yes (creates new revision) | `template.containers.env` | Valid env var entries |
| vpc_access | CloudRunVpcAccess | No | `None` | Yes (creates new revision) | `template.vpc_access` | Valid connector ref |
| vpc_access_direct | CloudRunVpcAccessDirect | No | `None` | Yes (creates new revision) | `template.vpc_access.network_interfaces` | Valid network/subnet |
| volume_mounts | list[CloudRunVolumeMount] | No | `[]` | Yes (creates new revision) | `template.containers.volume_mounts` | Valid mount names |
| volumes | list[CloudRunVolume] | No | `[]` | Yes (creates new revision) | `template.volumes` | Valid volume config |
| liveness_probe | CloudRunProbe | No | `None` | Yes (creates new revision) | `template.containers.liveness_probe` | Valid probe config |
| startup_probe | CloudRunProbe | No | `None` | Yes (creates new revision) | `template.containers.startup_probe` | Valid probe config |
| traffic | list[CloudRunTraffic] | No | `[]` | Yes | `traffic` | Percents must sum to 100 |
| binary_authorization | CloudRunBinaryAuth | No | `None` | Yes | `binary_authorization` | |
| custom_audiences | list[str] | No | `[]` | Yes | `custom_audiences` | Valid audience URIs |
| eventarc_triggers | list[EventarcTriggerConfig] | No | `[]` | Yes | (separate `google_eventarc_trigger` resource) | Valid Eventarc config |

**ForceNew fields (name, location):** These identity fields are not in the Pydantic config model -- they come from the node's `name` field and the global config `region`. Changing them destroys and recreates the entire Cloud Run service.

#### Platform-Only Fields (always mutable per D-09)

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| mode | Literal["workflow", "code_editor", "image_url"] or None | `None` | UI mode selector for how the user configures this service |
| workflow | WorkflowDefinition or None | `None` | Behavioral interface definition (db_refs, secret_refs, invoke_refs, etc.) |
| client | string or None | `None` | Client identifier for revision tracking |

### Required Fields (error-level)

- **image**: Container image is required. Cannot deploy without a container image reference.
- **service_account**: Service account is required. All compute types must run under a specific SA.

### Warning Fields

- **cpu**: CPU not set (defaults to 1000m). Warning to prompt explicit configuration.
- **memory**: Memory not set (defaults to 512Mi). Warning to prompt explicit configuration.
- **port**: Port not set (defaults to 8080). Warning to prompt explicit configuration.

---

## Cloud Run Job (`cloud_run_job`)

### Terraform Resource

- Resource: `google_cloud_run_v2_job`
- Provider version: ~5.0
- Last verified: 2026-03-26
- REGISTRY category: Compute
- is_compute: true
- iam_scope: project
- iam_terraform_resource: `google_project_iam_member`

### State Machine

Uses **Compute with Image** archetype. See [00-lifecycle-archetypes.md](../00-lifecycle-archetypes.md).

Key behavior: Image changes and template config changes create new job revisions. Only `name` and `location` are true ForceNew fields.

### Field Classification

#### Terraform-Mapped Fields

| Field | Type | Required | Default | Mutable | TF Argument | Validation |
|-------|------|----------|---------|---------|-------------|------------|
| image | string | Yes (error) | `""` | Yes (creates new revision) | `template.template.containers.image` | Non-empty when deploying |
| cpu | string | No | `"1000m"` | Yes (creates new revision) | `template.template.containers.resources.limits.cpu` | Valid CPU unit |
| memory | string | No | `"512Mi"` | Yes (creates new revision) | `template.template.containers.resources.limits.memory` | Valid memory unit |
| timeout | string | No | `"600s"` | Yes (creates new revision) | `template.template.timeout` | Valid duration |
| max_retries | int | No | `3` | Yes (creates new revision) | `template.template.max_retries` | >= 0 |
| task_count | int | No | `1` | Yes | `template.task_count` | >= 1 |
| parallelism | int | No | `1` | Yes | `template.parallelism` | >= 1, <= task_count |
| execution_environment | string | No | `"EXECUTION_ENVIRONMENT_GEN2"` | Yes (creates new revision) | `template.template.execution_environment` | GEN1 or GEN2 |
| service_account | string | Yes (error) | `""` | Yes (creates new revision) | `template.template.service_account` | Must reference valid SA |
| vpc_access | CloudRunVpcAccess | No | `None` | Yes (creates new revision) | `template.template.vpc_access` | Valid connector ref |
| env_vars | list[EnvVarEntry] | No | `[]` | Yes (creates new revision) | `template.template.containers.env` | Valid env var entries |
| volumes | list[CloudRunVolume] | No | `[]` | Yes (creates new revision) | `template.template.volumes` | Valid volume config |
| volume_mounts | list[CloudRunVolumeMount] | No | `[]` | Yes (creates new revision) | `template.template.containers.volume_mounts` | Valid mount names |
| command | list[str] | No | `[]` | Yes (creates new revision) | `template.template.containers.command` | |
| args | list[str] | No | `[]` | Yes (creates new revision) | `template.template.containers.args` | |
| labels | dict[str, str] | No | `{}` | Yes | `labels` | Valid label key/value |
| annotations | dict[str, str] | No | `{}` | Yes | `annotations` | Valid annotation key/value |
| binary_authorization | CloudRunBinaryAuth | No | `None` | Yes | `binary_authorization` | |

**ForceNew fields (name, location):** Identity fields from node name and global config region. Changing them destroys and recreates the job.

#### Platform-Only Fields (always mutable per D-09)

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| mode | Literal["workflow", "code_editor", "image_url"] or None | `None` | UI mode selector |
| workflow | WorkflowDefinition or None | `None` | Behavioral interface definition |
| scheduler_triggers | list[SchedulerTriggerConfig] | `[]` | Cloud Scheduler cron triggers (generates separate TF resources) |

### Required Fields (error-level)

- **image**: Container image is required.
- **service_account**: Service account is required.

### Warning Fields

None defined in REQUIRED_FIELDS.

---

## Cloud Function (`cloud_function`)

### Terraform Resource

- Resource: `google_cloudfunctions2_function`
- Provider version: ~5.0
- Last verified: 2026-03-26
- REGISTRY category: Compute
- is_compute: true
- iam_scope: resource
- iam_terraform_resource: `google_cloudfunctions2_function_iam_member`

### State Machine

Uses **Compute with Image** archetype. See [00-lifecycle-archetypes.md](../00-lifecycle-archetypes.md).

Key behavior: Source code uploads create new function versions. Cloud Function has MORE ForceNew fields than Cloud Run/Job -- notably in build_config and event_trigger.

### Field Classification

#### Terraform-Mapped Fields

| Field | Type | Required | Default | Mutable | TF Argument | Validation |
|-------|------|----------|---------|---------|-------------|------------|
| runtime | string | Yes (error) | (none - required) | Yes (MEDIUM confidence -- likely mutable in GCP API, verify against provider source) | `build_config.runtime` | Valid runtime string (e.g., "python312", "nodejs20") |
| entry_point | string | Yes (error) | (none - required) | Yes (MEDIUM confidence -- likely mutable in GCP API, verify against provider source) | `build_config.entry_point` | Non-empty function name |
| source | CfSource | No | `None` | Yes (creates new version) | `build_config.source` | Valid storage_source or repo_source |
| cpu | string | No | `"1"` | Yes | `service_config.available_cpu` | Valid CPU unit |
| memory | string | No | `"256Mi"` | Yes | `service_config.available_memory` | Valid memory unit |
| timeout_seconds | int | No | `60` | Yes | `service_config.timeout_seconds` | 1-540 for HTTP, 1-3600 for event |
| min_instances | int | No | `0` | Yes | `service_config.min_instance_count` | >= 0 |
| max_instances | int | No | `100` | Yes | `service_config.max_instance_count` | >= 1 |
| max_concurrent_requests | int | No | `1` | Yes | `service_config.max_instance_request_concurrency` | >= 1 |
| ingress | string | No | `"ALLOW_ALL"` | Yes | `service_config.ingress_settings` | Valid ingress setting |
| service_account | string | Yes (error) | `""` | Yes | `service_config.service_account_email` | Must reference valid SA |
| vpc_connector | string | No | `None` | Yes | `service_config.vpc_connector` | Valid connector ref |
| vpc_connector_egress_settings | string | No | `"PRIVATE_RANGES_ONLY"` | Yes | `service_config.vpc_connector_egress_settings` | PRIVATE_RANGES_ONLY or ALL_TRAFFIC |
| env_vars | list[EnvVarEntry] | No | `[]` | Yes | `service_config.environment_variables` / `secret_environment_variables` | Valid env var entries |
| secret_volumes | list[CfSecretVolume] | No | `[]` | Yes | `service_config.secret_volumes` | Valid secret refs |
| event_trigger | CfEventTrigger | No | `None` | Partially (see below) | `event_trigger` | Valid event trigger config |
| build_config | CfBuildConfig | No | `None` | Partially (see below) | `build_config` | Valid build config |
| labels | dict[str, str] | No | `{}` | Yes | `labels` | Valid label key/value |

**ForceNew fields:**
- **name, location**: Identity fields (from node name and global config region). Changing destroys and recreates.
- **build_config.docker_repository**: ForceNew. Cannot change the Artifact Registry repository after creation.
- **build_config.worker_pool**: ForceNew. Cannot change the Cloud Build worker pool after creation.
- **event_trigger.event_type**: ForceNew. Cannot change the event type (e.g., from Pub/Sub to GCS) after creation.
- **event_trigger.trigger_region**: ForceNew. Cannot change the trigger region after creation.

**MEDIUM confidence fields (Open Question 3 from RESEARCH.md):**
- `runtime` and `entry_point` are listed as potentially immutable in raw Terraform docs, but the GCP API for 2nd gen Cloud Functions typically allows updating these. Mark as likely mutable but verify against provider source before finalizing.

#### Platform-Only Fields (always mutable per D-09)

| Field | Type | Default | Purpose |
|-------|------|---------|---------|
| mode | Literal["workflow", "code_editor", "image_url"] or None | `None` | UI mode selector |
| workflow | WorkflowDefinition or None | `None` | Behavioral interface definition |
| source_bucket | string | `""` | Auto-derived by pipeline -- GCS bucket for source upload. User does not set this directly. |
| source_object | string | `"source.zip"` | Auto-derived by pipeline -- GCS object name for source upload. |

### Required Fields (error-level)

- **runtime**: Runtime is required. Specifies the language runtime (e.g., "python312", "nodejs20").
- **entry_point**: Entry point is required. The function name to execute.
- **service_account**: Service account is required. All compute types must run under a specific SA.

### Warning Fields

None defined in REQUIRED_FIELDS.

---

*Referenced by: compute/02-compute-patterns.md, compute/03-cloud-run.md, compute/04-cloud-run-job.md, compute/05-cloud-function.md*
*Phase: 01-resource-node-specifications*
