# Cloud Run: Specifics

**Type:** cloud_run
**Terraform Resource:** `google_cloud_run_v2_service`
**Archetype:** Compute with Image
**Complexity:** Highest of all compute types (~28 config fields, 11+ nested sub-models)

---

## Overview

Cloud Run is the most complex compute type in the platform. It supports long-running HTTP services with auto-scaling, traffic splitting across revisions, health probes, volume mounts, GPU acceleration, session affinity, binary authorization, and Eventarc triggers. The Pydantic model `CloudRunConfig` has approximately 28 fields and references 11 nested sub-models.

## Traffic Splitting

Cloud Run uniquely supports traffic splitting across revisions via the `traffic` field (list of `CloudRunTraffic` entries).

### CloudRunTraffic Model

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| type | string | `"TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"` | LATEST or REVISION |
| revision | string or None | `None` | Specific revision name (required when type=REVISION) |
| percent | int | `100` | Traffic percentage to this target |
| tag | string or None | `None` | URL tag for this traffic target |

### Traffic Splitting Patterns

- **Default (100% latest):** All traffic goes to the most recent revision. This is the default for new services and the simplest deployment pattern.
- **Canary deployment:** Split traffic between the latest revision and the previous one (e.g., 90% old, 10% new) to validate changes before full rollout.
- **Gradual rollout:** Incrementally shift traffic from old to new revision (10% -> 25% -> 50% -> 100%).
- **Tag-based routing:** Assign URL tags to revisions for direct access (e.g., `https://canary---service-name.run.app`).

### Constraints

- Traffic percentages across all entries must sum to 100.
- At most one entry can use `TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST`.
- Revision names must reference existing revisions of the service.

## Health Probes

Cloud Run supports startup and liveness probes to determine container health.

### CloudRunProbe Model

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| http_get | CloudRunHttpGet or None | `None` | HTTP GET probe configuration |
| initial_delay_seconds | int | `0` | Seconds to wait before first probe |
| period_seconds | int | `10` | Seconds between probes |
| timeout_seconds | int | `1` | Seconds before probe times out |
| failure_threshold | int | `3` | Consecutive failures before marking unhealthy |

### CloudRunHttpGet Model

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| path | string | (required) | HTTP path to probe (e.g., "/healthz") |
| port | int or None | `None` | Port to probe (defaults to container port) |

### Probe Types

- **startup_probe:** Determines when the container is ready to receive traffic. Runs once at startup. If it fails `failure_threshold` times, the container is killed and restarted.
- **liveness_probe:** Runs periodically after the container is started. If it fails, the container is restarted.

### Notes

- Cloud Run also supports TCP and gRPC probes at the GCP level, but the current Pydantic model only captures HTTP GET probes.
- Probes are revision-level configuration -- changing probe settings creates a new revision.

## Volume Mounts

Cloud Run supports mounting various volume types into the container filesystem.

### CloudRunVolume Model

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| name | string | (required) | Volume name (referenced by volume_mounts) |
| secret | CloudRunVolumeSecret or None | `None` | Mount a Secret Manager secret as files |
| empty_dir | CloudRunEmptyDir or None | `None` | Ephemeral in-memory or disk storage |

### CloudRunVolumeSecret Model

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| secret | string | (required) | Secret Manager secret name or node reference |
| items | list[CloudRunVolumeSecretItem] | `[]` | Specific secret versions/paths to mount |

### CloudRunVolumeMount Model

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| name | string | (required) | Must match a volume name |
| mount_path | string | (required) | Container filesystem path |

### Supported Volume Types

The Pydantic model captures:
- **Secret volumes:** Mount Secret Manager secrets as files in the container. Integration point with `secret_manager` nodes.
- **EmptyDir volumes:** Ephemeral storage. `medium` can be `None` (disk-backed) or `"Memory"` (tmpfs/RAM). `size_limit` controls maximum size.

At the GCP level, Cloud Run v2 also supports:
- **Cloud SQL instances:** Mounting the Cloud SQL proxy socket.
- **GCS buckets:** FUSE-based GCS bucket mounts.
- **NFS volumes:** Network file system mounts.

These additional volume types are not yet modeled in the Pydantic config.

## GPU Support

Cloud Run supports GPU-enabled instances for ML inference workloads.

The current Pydantic model does not include a `gpu` field, but the GCP API supports:
- GPU type selection (e.g., `nvidia-l4`)
- GPU count
- Requires `cpu_idle=false` and specific machine types

GPU support may be added to the config model in a future iteration.

## Session Affinity

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| session_affinity | bool | `false` | Sticky sessions -- route requests from the same client to the same instance |

Session affinity is useful for stateful applications (WebSocket connections, in-memory caches). When enabled, Cloud Run uses a cookie to route subsequent requests from the same client to the same container instance.

## Binary Authorization

### CloudRunBinaryAuth Model

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| breakglass_justification | string or None | `None` | Justification for bypassing binary auth policy |
| use_default | bool | `false` | Use the project's default binary authorization policy |

Binary authorization verifies that container images are signed and approved before deployment. This is a security control for production environments.

## VPC Access Models

Cloud Run has two VPC access approaches (see [02-compute-patterns.md](02-compute-patterns.md) for details):

### CloudRunVpcAccess (Connector-Based)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| connector | string or None | `None` | VPC connector name or node reference |
| egress | string | `"PRIVATE_RANGES_ONLY"` | PRIVATE_RANGES_ONLY or ALL_TRAFFIC |

### CloudRunVpcAccessDirect (Direct VPC Egress)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| network | string or None | `None` | VPC network name |
| subnetwork | string or None | `None` | Subnet name |
| network_interfaces | list[CloudRunNetworkInterface] | `[]` | Network interface configs |

Direct VPC Egress avoids the VPC connector entirely. Note: This model exists in the codebase but is not yet rendered in the `cloud_run.tf.j2` template.

## Eventarc Integration

Cloud Run services can receive events via Eventarc triggers. The `eventarc_triggers` field (list of `EventarcTriggerConfig`) configures event routing.

### EventarcTriggerConfig Model

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| matching_criteria | list[EventarcMatchingCriteria] | `[]` | Event filter criteria |
| transport | EventarcTransport or None | `None` | Transport configuration (Pub/Sub topic) |
| service_account_email | string or None | `None` | SA for the trigger |
| location | string or None | `None` | Trigger location |

Eventarc triggers generate separate `google_eventarc_trigger` Terraform resources (see `eventarc_trigger.tf.j2`), not inline configuration on the Cloud Run service.

## External LB Integration

The `external_lb.tf.j2` template references Cloud Run services as backends for load balancing:
- Cloud Run services can be backends for `google_compute_backend_service` via serverless NEGs.
- This creates a dependency: External LB nodes depend on Cloud Run service nodes.
- The integration is handled at the Terraform template level, not in the Cloud Run config model.

## Sub-Model Summary

| Sub-Model | Used By Field | Field Count |
|-----------|--------------|-------------|
| CloudRunVpcAccess | vpc_access | 2 |
| CloudRunVpcAccessDirect | vpc_access_direct | 3 |
| CloudRunNetworkInterface | vpc_access_direct.network_interfaces | 3 |
| CloudRunVolume | volumes | 3 |
| CloudRunVolumeSecret | volumes[].secret | 2 |
| CloudRunVolumeSecretItem | volumes[].secret.items | 3 |
| CloudRunEmptyDir | volumes[].empty_dir | 2 |
| CloudRunVolumeMount | volume_mounts | 2 |
| CloudRunProbe | startup_probe, liveness_probe | 5 |
| CloudRunHttpGet | probes[].http_get | 2 |
| CloudRunTraffic | traffic | 4 |
| CloudRunBinaryAuth | binary_authorization | 2 |
| EventarcTriggerConfig | eventarc_triggers | 4 |
| EventarcMatchingCriteria | eventarc_triggers[].matching_criteria | 3 |
| EventarcTransport | eventarc_triggers[].transport | 1 |
| EnvVarEntry | env_vars | (shared model) |
| WorkflowDefinition | workflow | (shared model) |

---

*References: [01-compute-template.md](01-compute-template.md), [02-compute-patterns.md](02-compute-patterns.md)*
*Phase: 01-resource-node-specifications*
