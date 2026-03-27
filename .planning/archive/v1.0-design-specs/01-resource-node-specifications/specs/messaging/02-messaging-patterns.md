# Messaging Category - Patterns & Shared Behaviors

**Category:** Messaging
**Node types:** pubsub_schema, pubsub_topic, pubsub_subscription, cloud_task_queue

---

## Pub/Sub Trilogy Relationship

The three Pub/Sub types form a strict dependency chain:

```
pubsub_schema --> pubsub_topic --> pubsub_subscription
```

1. **Schema** defines the message format (Avro JSON or Protocol Buffer definition)
2. **Topic** is the message channel; optionally references a schema via `schema_settings.schema`
3. **Subscription** is the consumer endpoint; references a topic via `topic` field

This ordering is critical for deploy sequencing (Phase 3): schemas must be deployed before topics that reference them, and topics must be deployed before their subscriptions.

### Dependency Edges

- `pubsub_topic.schema_settings.schema_` -> `pubsub_schema` (optional, creates dependency if set)
- `pubsub_subscription.topic` -> `pubsub_topic` (required, always creates dependency)
- `pubsub_subscription.dead_letter_policy.dead_letter_topic` -> `pubsub_topic` (optional, creates implicit dependency to a separate topic)
- `pubsub_subscription.push_config.push_endpoint` -> compute node (optional, resolved via `resolve_ref`)

## Cloud Tasks vs Pub/Sub

Cloud Tasks and Pub/Sub serve different messaging patterns despite being in the same category:

| Aspect | Pub/Sub | Cloud Tasks |
|--------|---------|-------------|
| Pattern | Fan-out publish/subscribe | Targeted task dispatch |
| Delivery | One-to-many (topic -> N subscriptions) | One-to-one (queue -> handler) |
| Rate control | Subscription-level flow control | Queue-level rate limiting (max_dispatches_per_second) |
| Target | Pull, push, BigQuery, GCS | HTTP endpoint or App Engine |
| Use case | Event broadcasting, streaming | Work queues, rate-limited API calls |
| Ordering | Optional (per ordering key) | FIFO within queue |

Both are in the Messaging category because they handle asynchronous inter-service communication, but they are never interchangeable.

## IAM Scope

| Type | IAM Scope | IAM TF Resource | Notes |
|------|-----------|-----------------|-------|
| pubsub_schema | None | -- | No resource-level IAM; access controlled at project level |
| pubsub_topic | `resource` | `google_pubsub_topic_iam_member` | Publisher/subscriber roles per topic |
| pubsub_subscription | `resource` | `google_pubsub_subscription_iam_member` | Subscriber/viewer roles per subscription |
| cloud_task_queue | `resource` | `google_cloud_tasks_queue_iam_member` | Enqueuer/viewer roles per queue |

Notable: `pubsub_schema` is the only messaging type without resource-level IAM. Schema access is controlled at the project level.

## Action Types (from ACTION_VALID_TARGETS)

| Action | Target Type | Description |
|--------|-------------|-------------|
| `Emit` | `pubsub_topic` | Compute node publishes a message to a topic |
| `Enqueue` | `cloud_task_queue` | Compute node creates a task in a queue |

These action types create dependency edges in the blueprint graph from compute nodes to messaging nodes. The action determines which IAM role the compute node's service account needs:

- `Emit` -> `roles/pubsub.publisher` on the target topic
- `Enqueue` -> `roles/cloudtasks.enqueuer` on the target queue

## Subscription Delivery Types

A subscription's delivery mechanism is determined by which config block is set (mutually exclusive):

| Delivery Type | Config Field | How It Works |
|---------------|-------------|--------------|
| Pull (default) | None set | Client polls for messages using the Pub/Sub API |
| Push | `push_config` | Pub/Sub sends HTTP POST to `push_endpoint` |
| BigQuery export | `bigquery_config` | Pub/Sub writes directly to a BigQuery table |
| Cloud Storage export | `cloud_storage_config` | Pub/Sub writes to a GCS bucket |

The Pydantic model enforces mutual exclusivity via `@model_validator`: only one of `push_config`, `bigquery_config`, or `cloud_storage_config` may be set.

Push delivery supports OIDC authentication (`oidc_token` with service account email) for secure endpoint verification.

## Dead Letter Topics

Subscriptions can define a `dead_letter_policy` that routes messages after `max_delivery_attempts` failed deliveries to a separate "dead letter" topic. This creates:

1. An **implicit dependency edge** from the subscription to the dead letter topic (separate from the primary topic dependency)
2. A requirement for the subscription's service account to have `roles/pubsub.publisher` on the dead letter topic
3. A requirement for the Pub/Sub service agent to have `roles/pubsub.subscriber` on the subscription

The dead letter topic is a regular `pubsub_topic` node that typically has its own subscription for monitoring/alerting on failed messages.

## Shared Lifecycle Characteristics

All four messaging types follow the **Simple CRUD** archetype:

- **Create**: Terraform creates the resource with all specified fields
- **Update (mutable fields)**: In-place update via Terraform apply
- **Update (ForceNew fields)**: Destroy and recreate via Terraform
- **Delete**: Terraform destroys the resource

Key differences from other categories:
- No parent-child relationships (unlike Data types)
- No image/revision lifecycle (unlike Compute types)
- No reverse-dependency concerns on delete (unlike Network types)
- All fields are TF-mapped (0 platform-only fields across all 4 types)

## Deploy Ordering Implications (Phase 3)

Messaging types form their own deploy layer, separate from compute and data:

1. **Layer 1**: Deploy `pubsub_schema` resources (no dependencies within messaging)
2. **Layer 2**: Deploy `pubsub_topic` and `cloud_task_queue` (topics may depend on schemas)
3. **Layer 3**: Deploy `pubsub_subscription` (depends on topics)

This layering integrates with the broader deploy DAG: messaging infrastructure should be deployed after networking/IAM but before compute nodes that reference these resources via action types.
