# Cloud Run Job: Specifics

**Type:** cloud_run_job
**Terraform Resource:** `google_cloud_run_v2_job`
**Archetype:** Compute with Image
**Complexity:** Medium (~18 config fields, 5 nested sub-models)

---

## Overview

Cloud Run Job is a simpler variant of Cloud Run designed for batch and scheduled workloads that run to completion. Unlike Cloud Run services, jobs do not serve HTTP traffic, do not have traffic splitting, probes, or session affinity. Instead, they focus on task execution with configurable parallelism and retry behavior.

## Key Differences from Cloud Run Service

| Feature | Cloud Run Service | Cloud Run Job |
|---------|------------------|---------------|
| Traffic model | Request-based, auto-scaling | Fixed task count, run to completion |
| Traffic splitting | Yes (revisions) | No |
| Health probes | startup_probe, liveness_probe | Not applicable |
| Session affinity | Yes | Not applicable |
| Port | Required (default 8080) | Not applicable |
| Scaling | min/max instances, concurrency | task_count, parallelism |
| Scheduling | Always running (or scale-to-zero) | On-demand or cron-triggered |
| GPU support | Yes | Yes |
| Command/Args | Via Dockerfile | Explicit command/args fields |

## Task Count and Parallelism

The batch processing model is configured via two fields:

| Field | Default | Description |
|-------|---------|-------------|
| task_count | 1 | Total number of independent tasks to execute |
| parallelism | 1 | Maximum number of tasks running simultaneously |

### Execution Model

- Each task runs the same container image with the same configuration.
- Tasks are independent -- they do not communicate with each other.
- The `CLOUD_RUN_TASK_INDEX` environment variable (0-based) distinguishes tasks.
- The `CLOUD_RUN_TASK_COUNT` environment variable provides the total count.
- A job execution succeeds when ALL tasks complete successfully.
- Individual task failures are retried up to `max_retries` times.

### Parallelism Constraints

- `parallelism` must be >= 1 and <= `task_count`.
- Setting `parallelism = task_count` runs all tasks concurrently.
- Setting `parallelism = 1` runs tasks sequentially.
- Intermediate values provide controlled concurrency.

## Scheduler Triggers

Cloud Run Jobs can be triggered on a schedule via Cloud Scheduler. The `scheduler_triggers` field contains a list of `SchedulerTriggerConfig` entries.

### SchedulerTriggerConfig Model

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| schedule | string | (required) | Cron expression (e.g., "0 */6 * * *" for every 6 hours) |
| time_zone | string | `"UTC"` | IANA time zone for schedule evaluation |
| paused | bool | `false` | Whether the trigger is paused |
| retry_config | SchedulerRetryConfig or None | `None` | Retry configuration for failed triggers |

### SchedulerRetryConfig Model

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| retry_count | int | `0` | Number of retry attempts (0 = no retries) |
| max_retry_duration | string or None | `None` | Maximum duration for retries (e.g., "3600s") |

### Platform Behavior

The `scheduler_triggers` field is classified as **platform-only** because:
- Cloud Scheduler triggers generate separate `google_cloud_scheduler_job` Terraform resources (see `cloud_scheduler_job.tf.j2`), not inline configuration on the Cloud Run Job.
- Multiple scheduler triggers can reference the same job.
- Scheduler trigger lifecycle is managed independently from the job resource.

## Command and Args

Unlike Cloud Run services (which use the Dockerfile CMD/ENTRYPOINT), Cloud Run Jobs expose explicit `command` and `args` fields:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| command | list[str] | `[]` | Override container entrypoint |
| args | list[str] | `[]` | Override container arguments |

This allows the same container image to run different workloads by varying the command/args, which is useful for batch processing pipelines where different jobs share a base image.

## Volumes and VPC Access

Cloud Run Job shares the same volume and VPC access models as Cloud Run Service:

- **Volumes:** `CloudRunVolume` (secret volumes, empty_dir) with `CloudRunVolumeMount` for mount paths.
- **VPC Access:** `CloudRunVpcAccess` (connector-based) only. Direct VPC Egress (`CloudRunVpcAccessDirect`) is not currently available for Cloud Run Jobs.

## Binary Authorization

Cloud Run Job supports the same `CloudRunBinaryAuth` model as Cloud Run Service for container image verification.

## Sub-Model Summary

| Sub-Model | Used By Field | Field Count |
|-----------|--------------|-------------|
| CloudRunVpcAccess | vpc_access | 2 |
| CloudRunVolume | volumes | 3 |
| CloudRunVolumeMount | volume_mounts | 2 |
| CloudRunBinaryAuth | binary_authorization | 2 |
| SchedulerTriggerConfig | scheduler_triggers | 4 |
| SchedulerRetryConfig | scheduler_triggers[].retry_config | 2 |
| EnvVarEntry | env_vars | (shared model) |
| WorkflowDefinition | workflow | (shared model) |

## Missing from Current Model

Compared to the GCP API, the current Pydantic model does not include:
- **GPU configuration** (available for Cloud Run Jobs)
- **Execution template labels/annotations** (available at the execution level)
- **Notification config** (Pub/Sub notification on execution completion)

These may be added in future iterations as needed.

---

*References: [01-compute-template.md](01-compute-template.md), [02-compute-patterns.md](02-compute-patterns.md)*
*Phase: 01-resource-node-specifications*
