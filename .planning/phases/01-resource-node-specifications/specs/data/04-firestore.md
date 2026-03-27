# Firestore: Specifics

**Node Type:** `firestore`
**Terraform Resource:** `google_firestore_database`
**Category:** Data
**Archetype:** Parent-Child Composite
**Children:** firestore_collection (platform-only)
**Provider version:** ~5.0
**Last verified:** 2026-03-26

---

## Overview

Firestore is GCP's serverless document database. The platform models Firestore databases with optional collection schema documentation. The key architectural decisions center around the `type` field (FIRESTORE_NATIVE vs DATASTORE_MODE) and the `location_id` field, both of which are permanently immutable after creation.

The Pydantic model `FirestoreConfig` has 8 fields: 6 Terraform-mapped and 2 platform-only (collections, indexes).

## Critical ForceNew Fields

### type (FIRESTORE_NATIVE vs DATASTORE_MODE)

This is the most critical choice when creating a Firestore database. The `type` field determines the entire data model and query capabilities:

| Aspect | FIRESTORE_NATIVE | DATASTORE_MODE |
|--------|-----------------|----------------|
| Data model | Collections and documents | Kinds and entities |
| Query capabilities | Full Firestore query API, real-time listeners | Datastore query API, GQL support |
| Client libraries | firebase-admin, @google-cloud/firestore | @google-cloud/datastore |
| Real-time updates | Yes (onSnapshot) | No |
| Indexes | Automatic single-field, manual composite | All indexes must be defined |

**This field is immutable after creation.** The comment in the Pydantic model explicitly states: "immutable after creation". Changing this value triggers a full destroy-recreate cycle, losing ALL data.

The platform default is `FIRESTORE_NATIVE`, which matches the platform's own use of Firestore (the platform stores its own data in Firestore Native mode).

### location_id

Cannot move a Firestore database after creation. The location determines:
- Data residency (compliance implications)
- Latency to the application
- Available features (some features are region-specific)

Valid locations include multi-region identifiers (nam5, eur3) and single regions (us-east1, europe-west1, etc.).

### database_id

Defaults to "(default)". GCP allows multiple named databases per project (GA since 2023). The "(default)" database is included in the free tier; additional named databases require a paid Blaze plan.

The platform's `validate_firestore_free_tier()` function warns when `database_id != "(default)"`.

### tags

ForceNew per TF provider docs. Uncommon to use but worth noting.

## Mutable Fields

### concurrency_mode

Controls how Firestore handles concurrent writes:
- `OPTIMISTIC` (default): Uses optimistic concurrency control. Transactions may fail and retry on conflict.
- `PESSIMISTIC`: Uses pessimistic locking. Lower throughput but guaranteed consistency.
- `OPTIMISTIC_WITH_ENTITY_GROUPS`: Legacy Datastore-style entity groups (only valid with DATASTORE_MODE type).

This can be changed after creation without data loss.

### point_in_time_recovery_enablement

Enables point-in-time recovery (PITR) for the database. Can be enabled or disabled after creation.
- `POINT_IN_TIME_RECOVERY_ENABLED` (default in platform config)
- `POINT_IN_TIME_RECOVERY_DISABLED`

### delete_protection_state

Controls whether the database can be deleted:
- `DELETE_PROTECTION_ENABLED` (default): Database CANNOT be deleted via Terraform or API
- `DELETE_PROTECTION_DISABLED`: Database can be deleted

The platform must handle this in the deletion flow: first update to disable protection, then perform the delete.

## Terraform Template Analysis

The `firestore.tf.j2` template generates three types of resources:

### 1. google_firestore_database

The primary database resource. Uses `config.database_id` (with parentheses stripped) as the TF resource name. All 6 TF-mapped fields are rendered.

### 2. google_firestore_index (from config.indexes)

For each entry in `config.indexes[]`, generates a separate index resource with:
- `collection`: The collection to index
- `database`: References the parent database
- `query_scope`: COLLECTION or COLLECTION_GROUP
- `fields[]`: field_path + order (ASCENDING/DESCENDING) or array_config (CONTAINS)

### 3. google_firestore_field (TTL configuration)

For collections with a `ttl_field` defined, generates a field-level resource that enables TTL (time-to-live) auto-deletion:
- `collection`: The collection name
- `field`: The timestamp field used for TTL
- `ttl_config {}`: Empty block enables TTL
- `index_config {}`: Empty block (required by API)

This is notable because it means firestore_collection (a platform-only type) DOES influence Terraform output indirectly through the TTL field mechanism.

## Integration Points

- **Service accounts:** Firestore uses project-level IAM (`google_project_iam_member`). Common roles: `roles/datastore.user` (read/write), `roles/datastore.viewer` (read-only).
- **Cloud Run / Cloud Function:** Typically connect via `@google-cloud/firestore` client library using the database name.
- **Security rules:** `firestore.rules` file defines client-side access control (separate from server-side IAM). The platform manages rules in `firestore.rules` at the project level.
- **Real-time listeners:** Frontend subscribes to Firestore documents via `onSnapshot` -- this is the platform's own mechanism for real-time provisioning status updates.

## Validation Rules (from validation.py)

Required fields:
- `location_id` (error): "Location is required"
- `database_id` (warning): "Database ID not set (defaults to '(default)')"

Additional validation:
- Free tier check: Warns when database_id != "(default)"
- FirestoreCollectionConfig validates ttl_field references an existing timestamp field in fields[]

---

## Child: firestore_collection (Detailed)

### Overview

Represents a collection within a Firestore database. This is purely platform-level metadata -- Firestore is schemaless, so collections do not need to be pre-defined. The platform tracks expected collection structure for documentation, validation, and future code generation.

### Pydantic Model: FirestoreCollectionConfig

```
parentRef: str                          -- slug of parent firestore node (required)
name: str                               -- collection name (e.g., "users")
description: str                        -- default ""
id_strategy: FirestoreIdStrategy        -- default AUTO (auto, uuid, custom)
ttl_field: str                          -- default "" (must reference a timestamp field)
fields: list[FirestoreField]            -- default []
```

### FirestoreField Sub-Model

Each field supports:
- `name` (str): Field name
- `type` (FirestoreFieldType): 12 supported types -- string, number, boolean, map, array, timestamp, geopoint, reference, bytes, null, integer, float
- `description` (str): Default ""
- `required` (bool): Default false (informational -- Firestore doesn't enforce schemas)
- `array_of` (FirestoreFieldType | None): Type of array elements (when type is array)
- `subfields` (list[FirestoreField]): Nested fields for map type (recursive structure)

### FirestoreIdStrategy

Controls how document IDs are generated:
- `AUTO` (default): Firestore auto-generates IDs
- `UUID`: Platform generates UUID v4 IDs
- `CUSTOM`: User defines ID format (useful for natural keys)

### TTL Field Behavior

When `ttl_field` is set:
1. The referenced field must exist in `fields[]` and must be type `timestamp` (validated by Pydantic model)
2. The parent Firestore template generates a `google_firestore_field` resource with `ttl_config {}`
3. Documents with a timestamp in the past for this field are automatically deleted by Firestore

This is the ONE case where a platform-only child type influences Terraform output.

### Inline vs Flat Node

Collections can be defined two ways:
1. **Inline on parent:** `FirestoreConfig.collections[]` uses the `FirestoreCollection` model (includes subcollections for nesting)
2. **Flat child node:** `firestore_collection` node type uses `FirestoreCollectionConfig` model

The `reconstruct_collection_tree()` function in `validation.py` converts flat child nodes back into the nested `FirestoreCollection` structure on the parent config. This enables the TF template to access collection data (particularly TTL fields) through the parent config.

### Subcollection Support

The `FirestoreCollection` model (used for inline definitions) supports `subcollections: list[FirestoreCollection]` for nested collection hierarchies. However, the flat `FirestoreCollectionConfig` model does not have subcollections -- nesting is expressed by setting `parentRef` to a firestore_collection node (not just a firestore node).

### All Fields Always Mutable

Per D-09, all fields on platform-only types are always mutable. No Terraform lifecycle concern since no direct TF resource is generated (only the TTL field resource, which is managed through the parent).
