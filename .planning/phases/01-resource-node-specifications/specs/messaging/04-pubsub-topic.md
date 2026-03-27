# Pub/Sub Topic - Specifics

**Node type:** `pubsub_topic`
**Terraform resource:** `google_pubsub_topic`
**Category:** Messaging
**IAM scope:** `resource` (`google_pubsub_topic_iam_member`)

---

## Overview

Pub/Sub Topic is the central message channel in the Pub/Sub trilogy. Publishers send messages to topics, and subscriptions consume from them. Topics are relatively simple resources with 5 configurable fields, all mutable after creation.

## Field Deep-Dive

### message_retention_duration

- **Default:** `"86400s"` (24 hours)
- **Range:** 600s (10 minutes) to 2,678,400s (31 days)
- **Purpose:** How long published messages are retained in the topic for replay
- **Impact:** Retained messages can be replayed by subscriptions using `seek` operations
- **Mutable:** Yes -- can increase or decrease retention without recreation
- **Cost implication:** Longer retention = higher storage costs for high-volume topics

### kms_key_name

- **Default:** `None` (Google-managed encryption)
- **Format:** Full Cloud KMS CryptoKey resource name (e.g., `projects/P/locations/L/keyRings/R/cryptoKeys/K`)
- **Purpose:** Customer-managed encryption key for messages at rest
- **Mutable:** Yes per Terraform, but changing the encryption key is operationally disruptive
- **Gotcha:** While technically mutable, switching KMS keys may cause brief message delivery interruptions. Treat as a "plan carefully" field.

### schema_settings

- **Default:** `None` (no schema validation)
- **Nested model:** `PubsubSchemaSettings`
  - `schema_` (str, alias `"schema"`): Reference to a `pubsub_schema` node via `node:schema_name.name` or direct resource name
  - `encoding` (str, default `"JSON"`): Message encoding format -- `JSON` or `BINARY`
- **Purpose:** Enforces message format validation at the Pub/Sub layer
- **Mutable:** Yes -- can add, remove, or change schema reference after topic creation
- **Dependency:** Creates an edge from this topic to the referenced pubsub_schema node

### message_storage_policy

- **Default:** `None` (messages can be stored in any region)
- **Nested model:** `PubsubMessageStoragePolicy`
  - `allowed_persistence_regions` (list[str], default `[]`): List of GCP regions where messages may be stored
- **Purpose:** Data residency compliance -- restrict message storage to specific regions
- **Mutable:** Yes

### labels

- **Default:** `{}` (no labels)
- **Purpose:** Key-value metadata for organizing and filtering topics
- **Mutable:** Yes
- **Pattern:** Commonly used to tag topics by domain, service, or environment

## Integration Points

### As a dependency target

Multiple resource types can consume from or reference topics:

| Consumer | How It Connects | Dependency Direction |
|----------|-----------------|---------------------|
| `pubsub_subscription` | `config.topic` field references the topic | subscription -> topic |
| `cloud_function` | EventTrigger references topic for event-driven invocation | function -> topic |
| `cloud_run` | Eventarc trigger references topic | service -> topic |
| Compute nodes (Emit action) | `internalGraph` step with `Emit` action | compute -> topic |

### As a dependency source

Topics can depend on:

| Dependency | Via | Direction |
|------------|-----|-----------|
| `pubsub_schema` | `schema_settings.schema_` | topic -> schema |

## Edge Cases

1. **Topic without subscriptions:** Messages published to a topic with no subscriptions are silently discarded. The platform could warn about orphan topics (Phase 2 validation).

2. **Message ordering:** Topics support message ordering via ordering keys set by publishers at publish time. This is a runtime behavior not configured on the topic resource itself. However, subscriptions must enable `enable_message_ordering` to receive messages in order.

3. **Retained message replay:** When `message_retention_duration` is set, subscriptions can seek to a past timestamp to replay messages. This is an operational feature useful for reprocessing failed messages.

4. **Schema removal:** Removing `schema_settings` from a topic stops message validation. Existing subscriptions are unaffected, but new messages will no longer be validated against the schema.

5. **Default outputs:** The topic produces `topic` (full resource name) and `id` outputs, used by subscriptions and other resources to reference it.
