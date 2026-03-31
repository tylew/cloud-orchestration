---
estimated_steps: 3
estimated_files: 2
skills_used: []
---

# T01: Define RESOURCE_REFS contract and FieldRef model

Create `packages/core/core/refs.py` with a `FieldRef` dataclass and `RESOURCE_REFS` dict mapping NodeType to lists of FieldRef entries. Each entry declares: field (dot-path into config), target_type (NodeType the ref must point to), tf_attribute (what TF attribute to resolve to, e.g. 'email', 'id'), and is_list (whether the field is in a list like env_vars). Also add a `get_nested()` helper for safe dot-path access on Pydantic models.

The contract must cover all ~30 ref fields identified in the research audit: cloud_run (service_account, vpc_access.connector, env_vars[].secret), cloud_run_job (same pattern), cloud_function (service_account, vpc_connector, event_trigger.pubsub_topic, env_vars[].secret), subnet (network), vpc_connector (network, subnet), cloud_sql (ip_configuration.private_network), cloud_dns (vpc refs), external_lb (default_backend.cloud_run_service), pubsub_subscription (topic, dead_letter_policy.dead_letter_topic, push_config.push_endpoint, push_config.oidc_token.service_account_email, bigquery_config.service_account_email, cloud_storage_config.bucket, cloud_storage_config.service_account_email), eventarc_trigger (transport.pubsub_topic), cloud_task_queue (http_target.oidc_token.service_account_email, http_target.oauth_token.service_account_email), pubsub_topic (schema_settings.schema_), gcs_bucket (logging.log_bucket).

Write a basic test in test_refs.py that verifies every NodeType with known refs appears in the contract and every FieldRef.field dot-path resolves to a real config field.

## Inputs

- `packages/core/core/schemas/enums.py`
- `packages/core/core/schemas/configs/__init__.py`
- `packages/core/core/schemas/configs/cloud_run.py`
- `packages/core/core/schemas/configs/cloud_function.py`
- `packages/core/core/schemas/configs/subnet.py`
- `packages/core/core/schemas/configs/vpc_connector.py`
- `packages/core/core/schemas/configs/cloud_sql.py`
- `packages/core/core/schemas/configs/cloud_dns.py`
- `packages/core/core/schemas/configs/external_lb.py`
- `packages/core/core/schemas/configs/pubsub_subscription.py`
- `packages/core/core/schemas/configs/eventarc_trigger.py`
- `packages/core/core/schemas/configs/cloud_task_queue.py`
- `packages/core/core/schemas/configs/pubsub_topic.py`
- `packages/core/core/schemas/configs/gcs_bucket.py`

## Expected Output

- `packages/core/core/refs.py`
- `packages/core/tests/test_refs.py`

## Verification

cd packages/core && PYTHONPATH=. python -m pytest tests/test_refs.py -v
