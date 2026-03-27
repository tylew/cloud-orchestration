# Cloud Task Queue - Specifics

**Node type:** `cloud_task_queue`
**Terraform resource:** `google_cloud_tasks_queue`
**Category:** Messaging
**IAM scope:** `resource` (`google_cloud_tasks_queue_iam_member`)

---

## Overview

Cloud Task Queue provides rate-limited, targeted HTTP task dispatch. Unlike Pub/Sub's fan-out messaging pattern, Cloud Tasks dispatches individual tasks to a single handler endpoint with configurable rate limiting and retry logic. The queue itself is a configuration resource -- actual tasks are created at runtime by compute nodes using the `Enqueue` action.

## ForceNew Fields

### name (implicit ForceNew)

Queue names are derived from the node name with environment prefix (e.g., `dev-my-queue`). The name is permanent -- queue names cannot be changed or reused after deletion (GCP retains deleted queue names for a period).

### location (ForceNew)

- **Type:** `str`
- **Required:** Yes (error severity)
- **Format:** GCP region string (e.g., `us-central1`)
- **Critical behavior:** Location is an identity field. Queues cannot move between regions. Changing location requires full destroy-recreate.
- **Note:** The TF template supports `resolve_ref` for location, allowing it to reference another node's region output.

## Rate Limits (rate_limits)

Rate limiting is the primary feature that differentiates Cloud Tasks from Pub/Sub.

**TaskQueueRateLimits fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| max_dispatches_per_second | float | `50` | Maximum task dispatch rate (tasks/sec) |
| max_concurrent_dispatches | int | `20` | Maximum tasks in-flight simultaneously |
| max_burst_size | int \| None | `None` | Max burst window size (GCP auto-calculates if not set) |

Key behaviors:
- `max_dispatches_per_second` is the steady-state rate limit. GCP uses token bucket algorithm.
- `max_concurrent_dispatches` limits parallelism -- useful for protecting downstream services from overload
- Together these provide backpressure: if the handler is slow, tasks queue up rather than overwhelming the target
- All rate_limits fields are **mutable** -- can be tuned after creation without recreation

### Common rate limit patterns

| Pattern | dispatches/sec | concurrent | Use case |
|---------|---------------|------------|----------|
| Conservative | 5 | 5 | Rate-limited external API calls |
| Moderate | 50 | 20 | Internal service processing |
| Aggressive | 500 | 100 | High-throughput batch jobs |
| Throttled | 1 | 1 | Sequential processing |

## Retry Configuration (retry_config)

**TaskQueueRetryConfig fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| max_attempts | int | `100` | Maximum retry attempts (set to -1 for unlimited) |
| max_retry_duration | str \| None | `None` | Maximum total retry window (e.g., `"86400s"` for 24h) |
| min_backoff | str | `"1s"` | Minimum backoff duration between retries |
| max_backoff | str | `"300s"` | Maximum backoff duration between retries |
| max_doublings | int | `16` | Number of times backoff doubles before becoming linear |

Retry follows exponential backoff:
- First retry: `min_backoff` (1s)
- Each subsequent retry doubles: 2s, 4s, 8s, 16s, ...
- After `max_doublings` (16), backoff stays at the last doubled value or `max_backoff`, whichever is less
- Retries stop after `max_attempts` or `max_retry_duration`

All retry_config fields are **mutable**.

## Stackdriver Logging (stackdriver_logging_config)

**TaskQueueLoggingConfig fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| sampling_ratio | float | `1.0` | Fraction of task dispatches to log (0.0 to 1.0) |

- `1.0` = log every dispatch (useful for debugging, expensive at scale)
- `0.1` = log 10% of dispatches (good for production monitoring)
- `0.0` = disable logging

Mutable -- can adjust logging volume without recreation.

## Queue States (GCP-internal)

Cloud Tasks queues have internal GCP states not modeled in the platform state machine (per D-03):

| GCP State | Description | How It Works |
|-----------|-------------|--------------|
| RUNNING | Queue is actively dispatching tasks | Default state after creation |
| PAUSED | Queue stops dispatching (tasks remain queued) | Triggered via GCP API, not Terraform |

The platform does not currently expose pause/resume operations. These are runtime operations that happen outside the Terraform lifecycle.

## Integration with Compute Nodes

Cloud Task Queues are the target of the `Enqueue` action type:

```
compute_node --> [Enqueue action] --> cloud_task_queue
```

- Compute nodes (Cloud Run, Cloud Function) create tasks in the queue at runtime
- The task handler is typically another compute node (HTTP endpoint)
- The queue itself does not know about the handler -- task creation specifies the target URL
- IAM: the enqueuing service account needs `roles/cloudtasks.enqueuer` on the queue

### Difference from Pub/Sub Emit

| Aspect | Enqueue (Cloud Tasks) | Emit (Pub/Sub) |
|--------|----------------------|----------------|
| Target type | cloud_task_queue | pubsub_topic |
| Delivery | Single HTTP endpoint per task | All subscriptions receive message |
| Rate control | Queue-level rate limiting | No built-in rate limiting |
| Scheduling | Tasks can be scheduled for future execution | Messages delivered immediately |
| Deduplication | Built-in task deduplication by name | No built-in deduplication |

## App Engine Routing Override

The `app_engine_routing_override` field (dict | None) is a legacy feature for queues that dispatch to App Engine handlers. It specifies the App Engine service, version, and instance to route tasks to. Most modern architectures use HTTP handlers (Cloud Run) instead.

This field is mutable and rarely used in the platform's target architecture.

## Edge Cases

1. **Queue name reuse:** Deleted queue names are retained by GCP for a period (typically days). Attempting to recreate a queue with the same name immediately after deletion will fail. The platform should handle this in the deploy engine (Phase 3-5).

2. **Empty queues:** A queue with no tasks is a valid, billable resource. The platform does not need to validate that tasks exist -- queues are infrastructure that compute nodes use at runtime.

3. **Queue with max_attempts=-1:** Unlimited retries. Tasks will retry forever (up to `max_retry_duration` if set). This can cause "stuck" tasks that consume queue capacity.

4. **Rate limit of 0:** Setting `max_dispatches_per_second=0` effectively pauses the queue (tasks queue up but never dispatch). This is different from the GCP PAUSED state but has a similar effect.

5. **Location matching:** The queue location should match the region of the compute nodes that enqueue tasks, to minimize latency. The platform could validate this (Phase 2).
