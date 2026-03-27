# Messaging Category - Rigid Template

**Category:** Messaging
**Node types:** pubsub_schema, pubsub_topic, pubsub_subscription, cloud_task_queue
**Lifecycle archetype:** Simple CRUD (see 00-lifecycle-archetypes.md)

---

## pubsub_schema

### Terraform Resource

- Resource: `google_pubsub_schema`
- Provider version: ~5.0
- Last verified: 2026-03-26

### State Machine

Archetype: **Simple CRUD**

| Current State | Event | Next State | Notes |
|---------------|-------|------------|-------|
| (none) | create | draft | Initial node creation in blueprint |
| draft | deploy | deploying | TF apply submitted |
| deploying | success | deployed | TF apply completed |
| deploying | failure | failed | TF apply errored |
| deployed | update (mutable) | updating | In-place TF apply |
| deployed | update (immutable) | destroying | Destroy-recreate cycle (name change) |
| updating | success | deployed | |
| updating | failure | failed | |
| deployed | delete | destroying | TF destroy submitted |
| destroying | success | destroyed | |
| destroying | failure | failed | |
| failed | retry | deploying/updating/destroying | Deferred to Phase 3-5 |

### Field Classification

| Field | Type | Required | Default | Mutable | TF Argument | Validation |
|-------|------|----------|---------|---------|-------------|------------|
| type | str | No | `"AVRO"` | Yes | `type` | `AVRO` or `PROTOCOL_BUFFER` |
| definition | str | No (warning) | `""` | Yes | `definition` | Schema content string (Avro JSON or protobuf definition) |

**Total: 2 fields, 2 TF-mapped, 0 platform-only**

### Required Fields (error-level)

None.

### Warning Fields

- `definition`: Schema definition not set (empty string default)

### Notes

- `name` is derived from node name with environment prefix -- implicit identity field (ForceNew)
- Simplest messaging type with only 2 configurable fields
- No IAM scope (`iam_scope=None` in REGISTRY)

---

## pubsub_topic

### Terraform Resource

- Resource: `google_pubsub_topic`
- Provider version: ~5.0
- Last verified: 2026-03-26

### State Machine

Archetype: **Simple CRUD** (identical to pubsub_schema above)

### Field Classification

| Field | Type | Required | Default | Mutable | TF Argument | Validation |
|-------|------|----------|---------|---------|-------------|------------|
| message_retention_duration | str \| None | No | `"86400s"` | Yes | `message_retention_duration` | Duration string; 10 minutes to 31 days |
| kms_key_name | str \| None | No | `None` | Yes | `kms_key_name` | Full resource name of Cloud KMS CryptoKey |
| schema_settings | PubsubSchemaSettings \| None | No | `None` | Yes | `schema_settings` | Nested: schema reference + encoding |
| message_storage_policy | PubsubMessageStoragePolicy \| None | No | `None` | Yes | `message_storage_policy` | Nested: allowed_persistence_regions list |
| labels | dict[str, str] | No | `{}` | Yes | `labels` | Key-value pairs |

**Nested sub-models:**

- **PubsubSchemaSettings**: `schema_` (str, alias `"schema"`, reference to pubsub_schema node) + `encoding` (str, default `"JSON"`, values: `JSON` or `BINARY`)
- **PubsubMessageStoragePolicy**: `allowed_persistence_regions` (list[str], default `[]`)

**Total: 5 fields, 5 TF-mapped, 0 platform-only**

**ForceNew fields:** None from config model. `name` is identity (implicit ForceNew). Research notes `tags` as ForceNew but tags are not in the current Pydantic model.

### Required Fields (error-level)

None. Pub/Sub Topic has sensible defaults for all fields.

### Warning Fields

None.

### Notes

- IAM scope: `resource` (supports `google_pubsub_topic_iam_member`)
- Action target: `Emit` action type targets pubsub_topic (from `ACTION_VALID_TARGETS`)
- `schema_settings.schema_` uses Field alias `"schema"` for JSON compatibility with `populate_by_name=True`

---

## pubsub_subscription

### Terraform Resource

- Resource: `google_pubsub_subscription`
- Provider version: ~5.0
- Last verified: 2026-03-26

### State Machine

Archetype: **Simple CRUD** (identical to pubsub_schema above)

Additional note: Subscriptions have a special `filter` field that is **ForceNew** -- changing the filter requires destroy-recreate.

### Field Classification

| Field | Type | Required | Default | Mutable | TF Argument | Validation |
|-------|------|----------|---------|---------|-------------|------------|
| topic | str | **Yes (error)** | -- | No (identity ref) | `topic` | Reference to pubsub_topic node (resolved via `resolve_ref`) |
| ack_deadline_seconds | int | No | `10` | Yes | `ack_deadline_seconds` | 10-600 seconds |
| message_retention_duration | str | No | `"604800s"` | Yes | `message_retention_duration` | Duration string; 10 minutes to 7 days |
| retain_acked_messages | bool | No | `False` | Yes | `retain_acked_messages` | -- |
| enable_message_ordering | bool | No | `False` | Yes | `enable_message_ordering` | -- |
| enable_exactly_once_delivery | bool | No | `False` | Yes | `enable_exactly_once_delivery` | -- |
| filter | str \| None | No | `None` | **No (ForceNew)** | `filter` | CEL filter expression; cannot be changed after creation |
| retry_policy | PubsubRetryPolicy \| None | No | `None` | Yes | `retry_policy` | Nested: minimum_backoff, maximum_backoff |
| dead_letter_policy | PubsubDeadLetterPolicy \| None | No | `None` | Yes | `dead_letter_policy` | Nested: dead_letter_topic (ref), max_delivery_attempts |
| expiration_policy | PubsubExpirationPolicy \| None | No | `None` | Yes | `expiration_policy` | Nested: ttl duration |
| push_config | PubsubPushConfig \| None | No | `None` | Yes | `push_config` | Nested: push_endpoint, oidc_token, no_wrapper |
| bigquery_config | PubsubBigQueryConfig \| None | No | `None` | Yes | `bigquery_config` | Nested: table, use_topic_schema, etc. |
| cloud_storage_config | PubsubCloudStorageConfig \| None | No | `None` | Yes | `cloud_storage_config` | Nested: bucket, filename_prefix/suffix, etc. |
| labels | dict[str, str] | No | `{}` | Yes | `labels` | Key-value pairs |

**Nested sub-models (7):**

1. **PubsubRetryPolicy**: `minimum_backoff` (str, default `"10s"`) + `maximum_backoff` (str, default `"600s"`)
2. **PubsubDeadLetterPolicy**: `dead_letter_topic` (str, required -- reference to another topic) + `max_delivery_attempts` (int, default `5`)
3. **PubsubExpirationPolicy**: `ttl` (str, default `"2678400s"` = 31 days)
4. **PubsubOidcToken**: `service_account_email` (str, required) + `audience` (str \| None)
5. **PubsubNoWrapper**: `write_metadata` (bool, default `True`)
6. **PubsubPushConfig**: `push_endpoint` (str, required) + `attributes` (dict) + `oidc_token` (PubsubOidcToken) + `no_wrapper` (PubsubNoWrapper)
7. **PubsubBigQueryConfig**: `table` (str, required) + `use_topic_schema` (bool) + `use_table_schema` (bool) + `write_metadata` (bool) + `drop_unknown_fields` (bool)
8. **PubsubCloudStorageConfig**: `bucket` (str, required) + `filename_prefix` (str) + `filename_suffix` (str) + `max_duration` (str) + `max_bytes` (int) + `avro_config` (dict)

**Total: 14 fields (12 top-level config + topic + labels), 14 TF-mapped, 0 platform-only**

**ForceNew fields:** `filter` (cannot modify after creation). `name` is identity (implicit ForceNew). Research notes `tags` as ForceNew but tags are not in the current Pydantic model.

**Mutual exclusivity:** Only one of `push_config`, `bigquery_config`, or `cloud_storage_config` may be set (enforced by `@model_validator`). If none is set, the subscription defaults to pull delivery.

### Required Fields (error-level)

- `topic`: Topic reference is required (subscription must know which topic to consume from)

### Warning Fields

None.

### Notes

- IAM scope: `resource` (supports `google_pubsub_subscription_iam_member`)
- Most complex messaging type: 14 fields, 7+ nested sub-models
- Delivery type determined by which config is set: pull (default), push, BigQuery export, or Cloud Storage export
- `dead_letter_policy.dead_letter_topic` creates an implicit dependency edge to another pubsub_topic node

---

## cloud_task_queue

### Terraform Resource

- Resource: `google_cloud_tasks_queue`
- Provider version: ~5.0
- Last verified: 2026-03-26

### State Machine

Archetype: **Simple CRUD** (identical to pubsub_schema above)

Additional note: Both `name` and `location` are ForceNew (identity fields). Queue names are permanent.

### Field Classification

| Field | Type | Required | Default | Mutable | TF Argument | Validation |
|-------|------|----------|---------|---------|-------------|------------|
| location | str | **Yes (error)** | -- | **No (ForceNew)** | `location` | GCP region string (identity field) |
| rate_limits | TaskQueueRateLimits \| None | No | `None` | Yes | `rate_limits` | Nested: max_dispatches_per_second, max_concurrent_dispatches, max_burst_size |
| retry_config | TaskQueueRetryConfig \| None | No | `None` | Yes | `retry_config` | Nested: max_attempts, min/max_backoff, etc. |
| stackdriver_logging_config | TaskQueueLoggingConfig \| None | No | `None` | Yes | `stackdriver_logging_config` | Nested: sampling_ratio |
| app_engine_routing_override | dict \| None | No | `None` | Yes | `app_engine_routing_override` | App Engine routing for App Engine task handlers |

**Nested sub-models (3):**

1. **TaskQueueRateLimits**: `max_dispatches_per_second` (float, default `50`) + `max_concurrent_dispatches` (int, default `20`) + `max_burst_size` (int \| None)
2. **TaskQueueRetryConfig**: `max_attempts` (int, default `100`) + `max_retry_duration` (str \| None) + `min_backoff` (str, default `"1s"`) + `max_backoff` (str, default `"300s"`) + `max_doublings` (int, default `16`)
3. **TaskQueueLoggingConfig**: `sampling_ratio` (float, default `1.0`)

**Total: 5 fields, 5 TF-mapped, 0 platform-only**

**ForceNew fields:** `name` (implicit identity, derived from node name) and `location` (identity field -- queues cannot move between regions).

### Required Fields (error-level)

- `location`: Location is required (queue region must be specified)

### Warning Fields

None.

### Notes

- IAM scope: `resource` (supports `google_cloud_tasks_queue_iam_member`)
- Action target: `Enqueue` action type targets cloud_task_queue (from `ACTION_VALID_TARGETS`)
- Queue has internal GCP states (RUNNING, PAUSED) not modeled in platform state machine per D-03
- Rate limiting is the primary feature differentiating Cloud Tasks from Pub/Sub
