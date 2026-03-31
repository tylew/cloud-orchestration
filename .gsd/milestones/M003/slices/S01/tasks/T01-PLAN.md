---
estimated_steps: 46
estimated_files: 4
skills_used: []
---

# T01: Add id/resource_id to BaseNode, gcp_name_template to registry, and resolve_gcp_name()

## Why
This task builds the schema foundation: BaseNode gets UUID-based identity, the registry gets per-type naming templates, and a pure function resolves GCP names. All downstream work (templates, generator) depends on these.

## Steps
1. In `packages/core/core/schemas/base.py`, add to BaseNode:
   - `id: str = Field(default_factory=lambda: str(uuid4()))` — stable UUID identity
   - `resource_id: str = ""` — 8-char hex derived from id
   - A `model_validator(mode='after')` that computes `resource_id = self.id[:8].replace('-', '')` if resource_id is empty (take first 8 hex chars of UUID, which is 8 chars before the first dash)
   - Import `uuid4` from `uuid`
2. In `packages/core/core/registry.py`, add `gcp_name_template: str = ""` to ComponentDefinition dataclass. Then set templates for all 24 types:
   - cloud_run: `"{env}-{rid}"` 
   - cloud_run_job: `"{env}-{rid}"`
   - cloud_function: `"{env}-{rid}"`
   - gcs_bucket: `"{env}-{rid}"`
   - pubsub_topic: `"{env}-{rid}"`
   - pubsub_subscription: `"{env}-{rid}"`
   - pubsub_schema: `"{env}-{rid}"`
   - cloud_task_queue: `"{env}-{rid}"`
   - cloud_dns: `"{env}-{rid}"`
   - external_lb: `"{env}-{rid}"`
   - vpc: `"{rid}"`
   - subnet: `"{rid}"`
   - vpc_connector: `"{rid}"`
   - secret_manager: `"{rid}"`
   - service_account: `"sa-{rid}"` (SA max 30 chars, must start with letter)
   - bigquery: `"bq_{rid}"` (BQ requires underscores, no hyphens)
   - bigtable: `"bt-{rid}"`
   - firestore: `"(default)"` (special: Firestore default DB)
   - cloud_sql: `"{env}-{rid}"`
   - cloud_sql_database: `"{rid}"`
   - cloud_sql_table: `""` (no TF resource)
   - firestore_collection: `""` (no TF resource)
   - bigquery_table: `""` (embedded in parent)
   - third_party_api: `""` (no TF resource)
3. Create `packages/core/core/terraform/naming.py` with `resolve_gcp_name(node, env, registry)` that:
   - Looks up `gcp_name_template` from registry for node.type
   - Substitutes `{rid}` → node.resource_id, `{env}` → env string, `{name}` → node.name
   - Returns the resolved string
4. Write unit tests in `packages/core/tests/test_naming.py`:
   - Test resource_id auto-generation on BaseNode construction
   - Test resource_id is deterministic (same id → same resource_id)
   - Test resolve_gcp_name for each naming pattern category (env-prefixed, sa-prefixed, bq-underscore, firestore-default, bare rid)
   - Test that existing BaseNode construction without id/resource_id still works (defaults kick in)

## Constraints
- resource_id must be deterministic from id — derive from UUID hex, don't generate separately
- BaseNode defaults must not break existing test fixtures that don't provide id/resource_id
- Firestore template is special: "(default)" is a literal GCP name, not a pattern

## Inputs

- ``packages/core/core/schemas/base.py``
- ``packages/core/core/registry.py``

## Expected Output

- ``packages/core/core/schemas/base.py``
- ``packages/core/core/registry.py``
- ``packages/core/core/terraform/naming.py``
- ``packages/core/tests/test_naming.py``

## Verification

cd packages/core && python -m pytest tests/test_naming.py -x -v
