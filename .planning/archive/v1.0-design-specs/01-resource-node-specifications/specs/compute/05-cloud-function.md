# Cloud Function: Specifics

**Type:** cloud_function
**Terraform Resource:** `google_cloudfunctions2_function`
**Archetype:** Compute with Image
**Complexity:** Medium (~17 config fields, 5 nested sub-models)
**Generation:** 2nd gen (Cloud Functions v2, backed by Cloud Run)

---

## Overview

Cloud Function is a source-based compute type -- users provide function source code rather than container images. The platform handles source upload, build, and deployment. Under the hood, 2nd gen Cloud Functions are backed by Cloud Run services, but the abstraction hides this complexity. Cloud Function has the most ForceNew fields of any compute type (6 total), particularly in the build_config and event_trigger areas.

## Source Upload Lifecycle

Unlike Cloud Run (container-based), Cloud Function uses a source upload model.

### CfSource Model

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| storage_source | CfStorageSource or None | `None` | GCS-based source |
| repo_source | CfRepoSource or None | `None` | Cloud Source Repository-based source |

### CfStorageSource Model

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| bucket | string | (required) | GCS bucket containing source archive |
| object | string | (required) | GCS object name (e.g., "source.zip") |
| generation | int or None | `None` | Specific GCS object generation |

### CfRepoSource Model

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| repo_name | string | (required) | Cloud Source Repository name |
| branch_name | string or None | `None` | Branch to build from |
| dir | string or None | `None` | Directory within the repo |
| tag_name | string or None | `None` | Tag to build from |
| commit_sha | string or None | `None` | Specific commit SHA |

### Platform Source Pipeline

The platform's deploy pipeline automates source upload:
1. User writes source code in the code editor (mode="code_editor") or provides a source reference.
2. The platform packages the source into a ZIP archive.
3. The archive is uploaded to the `source_bucket` (platform-derived, auto-populated).
4. The `source_object` field defaults to `"source.zip"`.
5. The Terraform template references the GCS source in `build_config.source.storage_source`.

The `source_bucket` and `source_object` fields are platform-only -- they are auto-derived by the deploy pipeline and not set by users directly.

## Event Triggers

Cloud Functions can be triggered by HTTP requests (default) or by events via Eventarc.

### CfEventTrigger Model

| Field | Type | Default | Mutable | Description |
|-------|------|---------|---------|-------------|
| event_type | string | (required) | **No (ForceNew)** | Event type (e.g., "google.cloud.pubsub.topic.v1.messagePublished") |
| trigger_region | string or None | `None` | **No (ForceNew)** | Region where the trigger is deployed |
| pubsub_topic | string or None | `None` | Yes | Pub/Sub topic for Pub/Sub triggers (node reference supported) |
| retry_policy | string | `"RETRY_POLICY_RETRY"` | Yes | RETRY_POLICY_RETRY or RETRY_POLICY_DO_NOT_RETRY |
| service_account_email | string or None | `None` | Yes | SA for the trigger invocation |
| event_filters | list[CfEventFilter] | `[]` | Yes | Additional event filter criteria |

### CfEventFilter Model

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| attribute | string | (required) | Filter attribute name |
| value | string | (required) | Filter attribute value |
| operator | string or None | `None` | Comparison operator |

### ForceNew Impact

Changing `event_type` or `trigger_region` destroys and recreates the entire function. This means:
- Switching a function from HTTP-triggered to Pub/Sub-triggered requires recreation.
- Moving a trigger to a different region requires recreation.
- The platform must warn users about these destructive changes.

### Eventarc Integration

A separate `eventarc_trigger.tf.j2` template exists alongside the Cloud Function template. For complex event routing, the platform may generate both `google_cloudfunctions2_function` and `google_eventarc_trigger` resources.

## Build Config

### CfBuildConfig Model

| Field | Type | Default | Mutable | Description |
|-------|------|---------|---------|-------------|
| docker_repository | string or None | `None` | **No (ForceNew)** | Artifact Registry repository for built images |
| worker_pool | string or None | `None` | **No (ForceNew)** | Cloud Build worker pool for the build |

### ForceNew Impact

Both `docker_repository` and `worker_pool` are ForceNew:
- Once a function is created pointing to a specific Artifact Registry repository, it cannot be changed.
- Once a function is created using a specific Cloud Build worker pool, it cannot be changed.
- These decisions are effectively permanent for the lifetime of the function resource.

### Build Process

The build process for Cloud Functions is:
1. Source code is uploaded to GCS.
2. Cloud Build pulls the source and builds a container image.
3. The built image is stored in the specified `docker_repository` (or the default one).
4. Cloud Functions serves the built container.

The `runtime` and `entry_point` fields are part of the build config in Terraform:
- `build_config.runtime`: Language runtime (e.g., "python312", "nodejs20", "go122").
- `build_config.entry_point`: Function name to execute.

## ForceNew Fields Summary

Cloud Function has the most ForceNew fields of any compute type:

| Field | Level | Why ForceNew |
|-------|-------|-------------|
| name | Identity | Resource identifier |
| location | Identity | GCP region |
| build_config.docker_repository | Build | Artifact Registry repo is baked into the build pipeline |
| build_config.worker_pool | Build | Cloud Build worker pool is baked into the build pipeline |
| event_trigger.event_type | Trigger | Event routing is fundamental to the function's architecture |
| event_trigger.trigger_region | Trigger | Trigger region determines event delivery infrastructure |

### Mutability Confidence

**HIGH confidence ForceNew:** name, location, docker_repository, worker_pool, event_type, trigger_region -- these are well-documented in Terraform provider ~5.0.

**MEDIUM confidence mutable:** `runtime` and `entry_point` (Open Question 3 from RESEARCH.md). The raw Terraform docs are ambiguous. The GCP API for 2nd gen Cloud Functions typically allows updating runtime and entry_point. The current classification marks these as **mutable** but recommends verification against the actual Terraform provider source or a `terraform plan` test.

## Secret Volumes

Cloud Functions use a different secret volume model than Cloud Run:

### CfSecretVolume Model

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| mount_path | string | (required) | Filesystem path to mount the secret |
| project_id | string or None | `None` | GCP project containing the secret (defaults to function's project) |
| secret | string | (required) | Secret Manager secret name or node reference |
| versions | list[CfSecretVolumeVersion] | `[]` | Specific versions to mount |

### CfSecretVolumeVersion Model

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| version | string | `"latest"` | Secret version number or "latest" |
| path | string | (required) | Filename within the mount path |

## Differences from Cloud Run

| Feature | Cloud Run | Cloud Function |
|---------|-----------|---------------|
| Deployment unit | Container image | Source code |
| Scaling unit | Concurrent requests | Per-invocation (default) |
| VPC access | Connector-based + Direct VPC Egress | Connector-based only |
| Volume model | CloudRunVolume (secrets, emptyDir, GCS, SQL) | CfSecretVolume (secrets only) |
| Traffic splitting | Yes (revision-based) | No (single active version) |
| Probes | startup_probe, liveness_probe | Not configurable |
| Session affinity | Yes | No |
| ForceNew count | 2 (name, location) | 6 (name, location, + 4 build/trigger fields) |
| Event triggers | Via separate Eventarc resource | Inline event_trigger field |

## Sub-Model Summary

| Sub-Model | Used By Field | Field Count |
|-----------|--------------|-------------|
| CfSource | source | 2 |
| CfStorageSource | source.storage_source | 3 |
| CfRepoSource | source.repo_source | 5 |
| CfEventTrigger | event_trigger | 6 |
| CfEventFilter | event_trigger.event_filters | 3 |
| CfBuildConfig | build_config | 2 |
| CfSecretVolume | secret_volumes | 4 |
| CfSecretVolumeVersion | secret_volumes[].versions | 2 |
| EnvVarEntry | env_vars | (shared model) |
| WorkflowDefinition | workflow | (shared model) |

---

*References: [01-compute-template.md](01-compute-template.md), [02-compute-patterns.md](02-compute-patterns.md)*
*Phase: 01-resource-node-specifications*
