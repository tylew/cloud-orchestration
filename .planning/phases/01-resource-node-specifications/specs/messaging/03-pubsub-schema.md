# Pub/Sub Schema - Specifics

**Node type:** `pubsub_schema`
**Terraform resource:** `google_pubsub_schema`
**Category:** Messaging
**IAM scope:** None

---

## Overview

Pub/Sub Schema is the simplest messaging type with only 2 configurable fields (`type` and `definition`). It defines the message format that topics can optionally enforce on published messages. Schemas provide message validation at the Pub/Sub layer, ensuring publishers and subscribers agree on a data contract.

## Schema Types

| Type | Format | Description |
|------|--------|-------------|
| `AVRO` (default) | JSON-based schema | Apache Avro schema definition as a JSON string |
| `PROTOCOL_BUFFER` | Proto definition | Protocol Buffer `.proto` definition as a string |

The `type` field determines how the `definition` field is interpreted. Both are mutable -- the schema type and content can be updated after creation.

## Schema Versioning

Pub/Sub schemas support revisioning under the hood:

- Schema resources are identified by name (ForceNew -- name cannot change)
- Updating the `definition` field creates a new **revision** in Pub/Sub (not a new resource)
- Topics referencing the schema via `schema_settings` can pin to a specific revision or use the latest
- The platform currently does not expose revision pinning -- topics always use the latest schema definition

This means changing a schema definition is non-destructive (no Terraform destroy-recreate), but it can break publishers/subscribers if the schema change is not backward-compatible.

## Definition Content

The `definition` field contains the actual schema content:

**Avro example:**
```json
{
  "type": "record",
  "name": "MyMessage",
  "fields": [
    {"name": "id", "type": "string"},
    {"name": "timestamp", "type": "long"},
    {"name": "payload", "type": "string"}
  ]
}
```

**Protocol Buffer example:**
```protobuf
syntax = "proto3";
message MyMessage {
  string id = 1;
  int64 timestamp = 2;
  string payload = 3;
}
```

The definition can be large (multi-line strings with complex nested types). The TF template uses a heredoc (`<<-EOT`) to handle multi-line content.

## Integration with Topics

Topics reference schemas via the `schema_settings` nested block:

```
pubsub_topic.schema_settings.schema_ --> pubsub_schema.name
```

- `schema_settings.schema` is the full resource name or node reference to a pubsub_schema
- `schema_settings.encoding` specifies how messages are encoded: `JSON` or `BINARY`
- When a schema is set on a topic, all messages published to that topic must conform to the schema

## Edge Cases

1. **No required fields at error severity**: A schema with an empty definition is valid at the platform level (warning only). The actual Pub/Sub API will reject it, but the platform allows saving incomplete schemas during development.

2. **Orphan schemas**: Schemas can exist without any topic referencing them. The platform does not enforce that schemas must be used -- they serve as optional contracts.

3. **Schema deletion with active topics**: Deleting a schema that is referenced by a topic will cause the topic to fail validation. The platform should warn about this (handled by cross-node reference validation in Phase 2).

4. **Large definitions**: Schema definitions can be thousands of lines for complex Avro or Proto schemas. The platform stores the full definition in the Pydantic model and renders it via heredoc in Terraform.
