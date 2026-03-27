# GCS Bucket: Specifics

**Node Type:** `gcs_bucket`
**Terraform Resource:** `google_storage_bucket`
**Category:** Storage
**Archetype:** Simple CRUD
**Children:** None
**Provider version:** ~5.0
**Last verified:** 2026-03-26

---

## Overview

Google Cloud Storage (GCS) is GCP's object storage service. Buckets are the fundamental containers for objects (files, blobs). The platform models GCS buckets with 10 config fields covering storage class, lifecycle management, versioning, CORS, retention, encryption, and logging.

GCS Bucket has the most ForceNew fields that are "identity-like" -- both `name` and `location` are implicit ForceNew fields because they form the bucket's permanent identity. Bucket names are globally unique across all of GCP.

## Globally Unique Naming

GCS bucket names are globally unique across ALL GCP projects. The TF template prefixes bucket names with the environment: `${var.environment}-{{ node.name }}`.

The platform includes GCS buckets in `GLOBAL_UNIQUE_TYPES` (from validation.py), which generates a warning: "gcs_bucket names must be globally unique in GCP."

Naming constraints:
- 3-63 characters
- Lowercase letters, numbers, hyphens, underscores, dots
- Must start and end with a letter or number
- Cannot resemble IP addresses
- Cannot start with "goog" or contain "google"

## ForceNew Fields

### name (implicit identity)

The bucket name (environment-prefixed) is the permanent identity. Changing it creates a new bucket and destroys the old one. ALL objects in the old bucket are lost unless manually copied.

### location (implicit identity)

Bucket location is permanent. Determines:
- Data residency (compliance)
- Availability and durability characteristics
- Latency to consumers
- Pricing tier

Location types:
- Multi-region: `US`, `EU`, `ASIA` (highest availability, highest cost)
- Dual-region: e.g., `US-EAST1+US-WEST1` (custom dual-region for specific DR needs)
- Region: e.g., `us-east1`, `europe-west1` (lowest latency, lowest cost)

### hierarchical_namespace

Explicit ForceNew per TF provider docs. Enables hierarchical namespace (folder-like organization within the bucket). Once enabled, cannot be disabled without recreating the bucket.

### custom_placement_config.data_locations

Explicit ForceNew. Used for dual-region buckets -- specifies which two regions to use. Cannot be changed after creation.

## Storage Class Transitions

The `storage_class` field is mutable and determines the default storage class for new objects:

| Class | Access Pattern | Min Storage Duration | Use Case |
|-------|---------------|---------------------|----------|
| STANDARD | Frequent (hot) | None | Active data, frequently accessed |
| NEARLINE | Monthly | 30 days | Backups accessed monthly |
| COLDLINE | Quarterly | 90 days | DR data accessed quarterly |
| ARCHIVE | Yearly | 365 days | Long-term archives, compliance |

**Cost implications:** Transitioning to a colder class reduces storage cost but increases retrieval cost. Objects already stored are not automatically reclassified -- use lifecycle rules for automatic transitions.

## Lifecycle Rules

Lifecycle rules automate object management based on conditions. Each rule has an action and a condition:

### Actions

| Action Type | Description | storage_class |
|-------------|-------------|---------------|
| Delete | Delete matching objects | N/A |
| SetStorageClass | Move to different storage class | Target class |
| AbortIncompleteMultipartUpload | Clean up incomplete uploads | N/A |

### Conditions

| Condition | Type | Description |
|-----------|------|-------------|
| age | int | Days since object creation |
| num_newer_versions | int | Number of newer versions (with versioning) |
| with_state | string | LIVE, ARCHIVED, or ANY |
| created_before | string | Date string (YYYY-MM-DD) |
| matches_prefix | list[str] | Object name prefix filter |
| matches_suffix | list[str] | Object name suffix filter |

Example patterns:
- Auto-archive after 30 days: `{action: {type: "SetStorageClass", storage_class: "NEARLINE"}, condition: {age: 30}}`
- Delete old versions: `{action: {type: "Delete"}, condition: {num_newer_versions: 3}}`
- Clean up temp files: `{action: {type: "Delete"}, condition: {age: 1, matches_prefix: ["tmp/"]}}`

## Versioning

When `versioning.enabled = true`:
- Old versions of objects are preserved when overwritten or deleted
- Enables point-in-time recovery of individual objects
- Combined with lifecycle rules, can auto-delete old versions after N newer versions
- Important for audit trails and compliance
- Increases storage costs (all versions count toward storage)

Default: `false` (versioning disabled).

## CORS Configuration

Needed when buckets serve web content or are accessed from browsers:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| origin | list[str] | [] | Allowed origins (e.g., ["https://app.example.com"]) |
| method | list[str] | [] | Allowed HTTP methods (e.g., ["GET", "PUT"]) |
| response_header | list[str] | [] | Exposed response headers |
| max_age_seconds | int | 3600 | How long browser can cache CORS response |

Multiple CORS rules can be defined for different origin/method combinations.

## Retention Policy

The `retention_policy` configuration controls object retention:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| retention_period | int | 0 | Minimum retention in seconds |
| is_locked | bool | false | Lock the retention policy (IRREVERSIBLE) |

**CRITICAL WARNING:** `is_locked = true` is IRREVERSIBLE:
- The retention policy cannot be removed or shortened
- The bucket cannot be deleted until EVERY object meets the retention period
- Objects cannot be deleted until they meet the retention period
- This is a compliance feature -- once locked, even project owners cannot override it

The platform should surface a strong warning before allowing `is_locked = true`.

## force_destroy Behavior

The `force_destroy` field controls whether non-empty buckets can be deleted:
- `false` (default): `terraform destroy` will FAIL if the bucket contains any objects
- `true`: `terraform destroy` will delete all objects and then the bucket

This is GCS's version of deletion protection. The default (false) prevents accidental data loss. The platform's delete flow should:
1. Check if bucket is empty
2. If not empty and force_destroy=false, warn the user
3. Either set force_destroy=true (with confirmation) or require user to empty the bucket first

## uniform_bucket_level_access

When enabled (default: true in the platform config):
- ACLs are disabled -- ALL access control goes through IAM
- Cannot use object-level ACLs (google_storage_object_access_control)
- Simplifies access management
- Recommended by Google for most use cases

Once enabled for 90 days, this becomes permanent and cannot be disabled.

## Encryption

Default: Google-managed encryption (no configuration needed). For customer-managed encryption keys (CMEK):

```
encryption:
  default_kms_key_name: "projects/PROJECT/locations/LOCATION/keyRings/RING/cryptoKeys/KEY"
```

The KMS key must be in the same location as the bucket.

## Logging

Access logs can be sent to another GCS bucket:

| Field | Type | Description |
|-------|------|-------------|
| log_bucket | string | Bucket to receive access logs |
| log_object_prefix | string | Optional prefix for log objects |

**Note:** The log destination bucket must already exist and the GCS service account must have write access to it.

## Terraform Template Analysis

The `gcs_bucket.tf.j2` template generates a single `google_storage_bucket` resource:
- `name`: Environment-prefixed: `${var.environment}-{{ node.name }}`
- `location`, `storage_class`, `uniform_bucket_level_access`, `force_destroy`: Direct field mappings
- `labels {}`: Rendered as map
- `versioning {}`: Conditional block
- `lifecycle_rule {}`: Loop over rules with `action {}` and `condition {}` sub-blocks
- `cors {}`: Loop over CORS configurations

**Not rendered in template:** `retention_policy`, `encryption`, `logging` -- these exist in the Pydantic model but are not in the current TF template. These would need to be added for full coverage.

## Integration Points

- **Service accounts:** GCS uses resource-level IAM (`google_storage_bucket_iam_member`). Common roles: `roles/storage.objectViewer`, `roles/storage.objectCreator`, `roles/storage.objectAdmin`.
- **Cloud Functions:** Can trigger on bucket events (object create, delete, archive, metadata update) via Eventarc/Cloud Functions event triggers.
- **Cloud Run:** Can mount buckets as volumes (via Cloud Storage FUSE) for file-based workloads.
- **Cloud Build:** Uses GCS for build source tarballs (the platform's own `CB_SOURCE_BUCKET`).
- **Terraform state:** The platform uses GCS buckets for Terraform state backends (`tf_bucket` in environment config).

## Validation Rules (from validation.py)

Required fields:
- `location` (error): "Location is required"

Additional validation:
- Global uniqueness warning: "gcs_bucket names must be globally unique in GCP"
