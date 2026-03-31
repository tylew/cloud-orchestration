# S02: Reference Contract — Type-Safe Cross-Resource Wiring

**Goal:** Every cross-resource reference field is declared in a typed RESOURCE_REFS contract; validation catches broken refs with type checking; auto-depends_on inferred from refs.
**Demo:** After this: After this: every cross-resource reference field is declared in a contract; validation catches broken refs with type checking; templates resolve refs from the contract; auto-depends_on inferred from refs

## Tasks
- [x] **T01: Created typed RESOURCE_REFS contract covering 12 node types and 30+ cross-resource reference fields with full dot-path validation against Pydantic config models** — Create `packages/core/core/refs.py` with a `FieldRef` dataclass and `RESOURCE_REFS` dict mapping NodeType to lists of FieldRef entries. Each entry declares: field (dot-path into config), target_type (NodeType the ref must point to), tf_attribute (what TF attribute to resolve to, e.g. 'email', 'id'), and is_list (whether the field is in a list like env_vars). Also add a `get_nested()` helper for safe dot-path access on Pydantic models.

The contract must cover all ~30 ref fields identified in the research audit: cloud_run (service_account, vpc_access.connector, env_vars[].secret), cloud_run_job (same pattern), cloud_function (service_account, vpc_connector, event_trigger.pubsub_topic, env_vars[].secret), subnet (network), vpc_connector (network, subnet), cloud_sql (ip_configuration.private_network), cloud_dns (vpc refs), external_lb (default_backend.cloud_run_service), pubsub_subscription (topic, dead_letter_policy.dead_letter_topic, push_config.push_endpoint, push_config.oidc_token.service_account_email, bigquery_config.service_account_email, cloud_storage_config.bucket, cloud_storage_config.service_account_email), eventarc_trigger (transport.pubsub_topic), cloud_task_queue (http_target.oidc_token.service_account_email, http_target.oauth_token.service_account_email), pubsub_topic (schema_settings.schema_), gcs_bucket (logging.log_bucket).

Write a basic test in test_refs.py that verifies every NodeType with known refs appears in the contract and every FieldRef.field dot-path resolves to a real config field.
  - Estimate: 1h
  - Files: packages/core/core/refs.py, packages/core/tests/test_refs.py
  - Verify: cd packages/core && PYTHONPATH=. python -m pytest tests/test_refs.py -v
- [x] **T02: Added validate_refs() that validates all cross-resource reference fields from RESOURCE_REFS contract, checking target existence and type correctness** — Add `validate_refs()` function to `packages/core/core/validation.py` that walks RESOURCE_REFS, extracts field values from each node's config using the `get_nested()` helper from refs.py, parses `node:name.attribute` format values, looks up target nodes (by name or id in the node map), and checks the target node's type matches the FieldRef.target_type. For list fields (env_vars[].secret), iterate the list and validate each entry. Skip None/empty values (optional refs). Return list[ValidationIssue] with severity 'error'.

Wire `validate_refs()` into `validate_blueprint()` alongside existing `validate_depends_on()` call.

Add tests to test_refs.py: (1) valid refs pass with no issues, (2) ref to non-existent node produces error, (3) ref to wrong-type node produces error, (4) optional empty ref field is skipped, (5) env_var secret refs validated in list context.

IMPORTANT: The node lookup must support both id-based and name-based lookups since ref values use `node:<name>.attribute` format where `<name>` is the node name, not the UUID id. Build a name-keyed lookup for ref resolution.
  - Estimate: 1h
  - Files: packages/core/core/validation.py, packages/core/tests/test_refs.py
  - Verify: cd packages/core && PYTHONPATH=. python -m pytest tests/test_refs.py tests/test_validation.py -v
- [x] **T03: Add _infer_ref_edges() to BlueprintDAG for auto-dependency inference from RESOURCE_REFS contract** — Add `infer_ref_edges()` method to BlueprintDAG in `packages/core/core/dag.py` that walks RESOURCE_REFS for each node, extracts populated ref field values, resolves target node names to node ids, and adds implicit edges to `self._graph`. Call this from `__init__` after `_build_graph()` so the inferred edges are included in topological sort, cycle detection, and parallel batches.

The method must: (1) import RESOURCE_REFS and get_nested from refs.py, (2) for each node, iterate its FieldRef entries, (3) parse `node:name.attribute` values to extract target name, (4) look up target node by name to get its id, (5) add edge: graph[node.id].add(target.id). Skip refs where the target isn't found (already caught by validation).

Add tests to test_refs.py: (1) Cloud Run with `service_account: 'node:my-sa.email'` auto-depends on the SA node, (2) multiple refs create multiple edges, (3) bare non-ref values don't create edges, (4) env_var secret refs create edges to secret_manager nodes.

Run full test suite to confirm no regressions: all 155+ existing tests plus new tests pass.
  - Estimate: 45m
  - Files: packages/core/core/dag.py, packages/core/tests/test_refs.py
  - Verify: cd packages/core && PYTHONPATH=. python -m pytest tests/ -v
