# Pub/Sub Subscription - Specifics

**Node type:** `pubsub_subscription`
**Terraform resource:** `google_pubsub_subscription`
**Category:** Messaging
**IAM scope:** `resource` (`google_pubsub_subscription_iam_member`)

---

## Overview

Pub/Sub Subscription is the most complex messaging type with 14 fields and 7+ nested sub-models. It defines how messages are consumed from a topic -- via pull, push to an HTTP endpoint, export to BigQuery, or export to Cloud Storage. Subscriptions are the consumer-side counterpart to topics.

## ForceNew Fields

### filter (ForceNew)

- **Type:** `str | None`
- **Default:** `None` (no filtering -- all messages delivered)
- **Format:** CEL (Common Expression Language) filter expression
- **Example:** `attributes.type = "important"`
- **Critical behavior:** The filter expression **cannot be changed after creation**. If the filter needs to change, the subscription must be destroyed and recreated.
- **Platform implication:** The UI should clearly warn users that filter is permanent. Changing it triggers a full destroy-recreate cycle, which means:
  - Unacknowledged messages in the old subscription are lost
  - Any seek position is reset
  - The subscription ID changes in Terraform

## Delivery Types (Mutually Exclusive)

The subscription's delivery mechanism is determined by which optional config block is set:

### Pull (default)

When none of `push_config`, `bigquery_config`, or `cloud_storage_config` is set, the subscription defaults to pull delivery. Clients poll for messages using the Pub/Sub API.

### Push (push_config)

**PubsubPushConfig fields:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| push_endpoint | str | Yes | -- | HTTPS URL to receive messages (resolved via `resolve_ref` for compute node endpoints) |
| attributes | dict[str, str] | No | `{}` | Custom attributes sent with each push request |
| oidc_token | PubsubOidcToken \| None | No | `None` | OIDC authentication for secure push |
| no_wrapper | PubsubNoWrapper \| None | No | `None` | Controls raw message delivery format |

**PubsubOidcToken fields:**
- `service_account_email` (str, required): SA email for OIDC token generation
- `audience` (str | None): Target audience for the token

**PubsubNoWrapper fields:**
- `write_metadata` (bool, default `True`): Include message metadata in push payload

Push delivery is commonly used to trigger Cloud Run services or Cloud Functions via HTTP. The `push_endpoint` often references a compute node's endpoint output.

### BigQuery Export (bigquery_config)

**PubsubBigQueryConfig fields:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| table | str | Yes | -- | BigQuery table in `project.dataset.table` format |
| use_topic_schema | bool | No | `False` | Use topic's schema for BigQuery table schema |
| use_table_schema | bool | No | `False` | Use BigQuery table schema for deserialization |
| write_metadata | bool | No | `True` | Write Pub/Sub message metadata to BigQuery |
| drop_unknown_fields | bool | No | `False` | Drop fields not in the BigQuery table schema |

BigQuery export writes messages directly to a BigQuery table without requiring a consumer application. Useful for analytics pipelines.

### Cloud Storage Export (cloud_storage_config)

**PubsubCloudStorageConfig fields:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| bucket | str | Yes | -- | GCS bucket name (resolved via `resolve_ref`) |
| filename_prefix | str \| None | No | `None` | Prefix for output files |
| filename_suffix | str \| None | No | `None` | Suffix for output files |
| max_duration | str | No | `"300s"` | Max time before flushing to a new file |
| max_bytes | int \| None | No | `None` | Max bytes before flushing to a new file |
| avro_config | dict \| None | No | `None` | Avro-specific output configuration |

Cloud Storage export writes messages as files to a GCS bucket. Useful for archival and batch processing pipelines.

## Dead Letter Policy

**PubsubDeadLetterPolicy fields:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| dead_letter_topic | str | Yes | -- | Reference to another pubsub_topic node |
| max_delivery_attempts | int | No | `5` | Max delivery attempts before routing to dead letter topic |

Key behaviors:
- Creates an **implicit dependency** from this subscription to the dead letter topic (separate from the primary topic)
- After `max_delivery_attempts` failed deliveries, the message is published to the dead letter topic
- Requires IAM configuration: the Pub/Sub service agent needs `roles/pubsub.publisher` on the dead letter topic and `roles/pubsub.subscriber` on this subscription
- The dead letter topic typically has its own subscription for monitoring failed messages

## Retry Policy

**PubsubRetryPolicy fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| minimum_backoff | str | `"10s"` | Minimum delay between retries |
| maximum_backoff | str | `"600s"` | Maximum delay between retries |

Retry follows exponential backoff between min and max. Applies to push delivery and pull nack scenarios.

## Expiration Policy

**PubsubExpirationPolicy fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| ttl | str | `"2678400s"` (31 days) | Time of inactivity after which the subscription is auto-deleted |

If no messages are pulled/pushed for the TTL duration, GCP automatically deletes the subscription. Set to `""` or `never` to disable expiration.

## Key Behaviors

### enable_exactly_once_delivery

When `True`, Pub/Sub guarantees each message is delivered exactly once. This comes with trade-offs:
- Higher latency for acknowledgment processing
- More restrictive flow control
- Not compatible with all delivery types

### enable_message_ordering

When `True`, messages with the same ordering key are delivered in publish order. Requires:
- Publisher to set an ordering key on each message
- The topic to support ordering (implicit)
- Only one message per ordering key is outstanding at a time (limits throughput)

### retain_acked_messages

When `True`, acknowledged messages are retained in the subscription backlog for the `message_retention_duration`. Useful for seeking back to replay previously processed messages.

## Edge Cases

1. **Subscription without topic:** The `topic` field is required at error severity. A subscription cannot exist without a valid topic reference.

2. **Switching delivery types:** Changing from push to pull (or vice versa) is mutable -- just add/remove the relevant config block. However, switching between BigQuery/GCS export and push/pull may require additional IAM changes.

3. **Dead letter loop:** If the dead letter topic points back to the same topic (directly or indirectly), messages can loop. The platform should validate against circular dead letter chains (Phase 2).

4. **Multiple subscriptions per topic:** A single topic can have many subscriptions. Each subscription independently tracks its position in the topic's message backlog. This is the standard fan-out pattern.

5. **Acknowledgment deadline:** `ack_deadline_seconds` (10-600s) determines how long Pub/Sub waits for acknowledgment before redelivering. Too short = duplicate deliveries; too long = delayed retry on failures.
