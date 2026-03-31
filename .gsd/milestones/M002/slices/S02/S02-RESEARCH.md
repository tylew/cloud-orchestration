# S02 — Reference Contract: Type-Safe Cross-Resource Wiring — Research

## Summary

S02 introduces a `RESOURCE_REFS` contract declaring every cross-resource reference field across all 20+ node types. Currently, ~34 `resolve_ref()` calls in templates handle references ad-hoc — each template knows which fields are refs and applies `startswith('node:')` checks inline. There's no validation that ref targets exist or are the correct type, no auto-dependency inference from refs, and no metadata for UI dropdowns.

The work is **targeted** — known patterns, known code, moderate complexity from the sheer number of ref fields (~30) across 10+ templates. The S01 UUID foundation is in place: `BaseNode.id`, `tf_resource_label`, id-keyed DAG/resolver. The resolver already handles `node:X.attribute` and bare-name formats, producing TF resource references with `tf_resource_label`. The contract needs to formalize what's already happening ad-hoc.

## Recommendation

Build the `RESOURCE_REFS` contract as a pure-data dict in a new `packages/core/core/refs.py` module. Add validation that checks ref fields exist and target the correct type. Update the resolver to use the contract for attribute resolution. Update the DAG to auto-infer `depends_on` from ref fields. Do NOT rewrite templates in this slice — the existing `resolve_ref()` calls work and template changes are high-risk. Instead, make the contract the source of truth for validation and auto-deps, leaving template refactoring as optional follow-up.

**Requirements targeted:** R002 (Deep DAG — logical data flow, partially advanced by auto-dep inference from refs).

## Implementation Landscape

### Key Files

- `packages/core/core/refs.py` — **NEW**. The `RESOURCE_REFS` dict mapping `NodeType` → list of `FieldRef` entries. Each entry: `field` (dot-path), `target_type` (NodeType), `tf_attribute` (what TF attr to resolve to), `format` ("ref" or "string").
- `packages/core/core/validation.py` — Add `validate_refs()` that walks `RESOURCE_REFS`, extracts field values from node configs, checks target node exists and has correct type. Currently has `validate_depends_on()` — the new function is parallel.
- `packages/core/core/dag.py` — `BlueprintDAG` needs method to auto-infer depends_on edges from ref fields (walk `RESOURCE_REFS`, find populated refs, add edges).
- `packages/core/core/terraform/resolver.py` — `resolve_node_ref()` currently resolves to `.id` for bare refs. The contract specifies the correct `tf_attribute` per field (e.g. `.email` for SA, `.self_link` for VPC). Update resolver to accept optional tf_attribute override.
- `packages/core/core/schemas/base.py` — No changes needed (BaseNode is fine as-is).
- `packages/core/core/terraform/generator.py` — Expose ref metadata for explorer API (optional). May add auto-depends_on injection before TF generation.
- `packages/core/tests/test_refs.py` — **NEW**. Unit tests for ref validation and auto-dep inference.

### Current Ref Patterns in Templates (all 34 resolve_ref calls)

| Template | Field | Target Type | TF Attribute |
|----------|-------|-------------|-------------|
| cloud_run | config.service_account | service_account | email |
| cloud_run | config.vpc_access.connector | vpc_connector | id |
| cloud_run | config.image | (external) | — |
| cloud_run | env secrets | secret_manager | secret_id |
| cloud_run_job | config.service_account | service_account | email |
| cloud_run_job | config.vpc_access.connector | vpc_connector | id |
| cloud_run_job | config.image | (external) | — |
| cloud_run_job | env secrets | secret_manager | secret_id |
| cloud_function | config.service_account | service_account | email |
| cloud_function | config.vpc_connector | vpc_connector | id |
| cloud_function | config.event_trigger.pubsub_topic | pubsub_topic | id |
| cloud_function | env secrets | secret_manager | secret_id |
| subnet | config.network | vpc | id |
| vpc_connector | config.network | vpc | id |
| vpc_connector | config.subnet.name | subnet | id |
| cloud_sql | config.ip_configuration.private_network | vpc | id |
| cloud_dns | config.peering_config... | vpc | id |
| external_lb | config.default_backend.cloud_run_service | cloud_run | id |
| pubsub_topic | (none direct) | — | — |
| eventarc_trigger | transport.pubsub_topic | pubsub_topic | id |
| cloud_task_queue | config.http_target.oidc_token.service_account_email | service_account | email |
| cloud_task_queue | config.http_target.oauth_token.service_account_email | service_account | email |
| gcs_bucket | (log bucket ref) | gcs_bucket | name |

### Build Order

1. **T01: Define `RESOURCE_REFS` contract** (`refs.py`) — Pure data, no behavior. List every ref field from the template audit above. Include `FieldRef` model. This is the foundation everything else reads.

2. **T02: Ref validation** (`validation.py`, `test_refs.py`) — Walk the contract, extract nested field values from node configs, validate target exists and has correct type. Wire into `validate_blueprint_by_id()`. Test with broken refs, wrong types, missing targets.

3. **T03: Auto-dependency inference** (`dag.py`, test) — `BlueprintDAG` method walks `RESOURCE_REFS`, finds populated ref fields, adds implicit edges. Test that a Cloud Run node with `service_account: "node:my-sa.email"` auto-depends on the SA node.

4. **T04: Resolver contract integration** (optional) — Update `resolve_node_ref` to accept tf_attribute from contract rather than always defaulting to `.id`. This makes the resolver contract-aware but doesn't change template behavior.

### Verification Approach

- `cd packages/core && PYTHONPATH=. python -m pytest tests/ -q` — all 155+ existing tests still pass
- New `test_refs.py` tests: contract completeness (every ref field in RESOURCE_REFS maps to a real config field), validation catches broken/wrong-type refs, auto-deps inferred correctly
- `PYTHONPATH=. python -m pytest tests/test_terraform_validate.py -v` — TF validate still passes (templates untouched)

## Constraints

- Templates must NOT be modified in this slice — they work, and changes risk TF validation regressions. The contract provides metadata; templates continue using `resolve_ref()` as-is.
- `resolve_node_ref()` uses a dual-keyed node_map (id + name) — ref values in configs may use either `node:name.attr` format or bare names. The contract must support both lookup patterns.
- Env var refs (`env_vars[].secret`) are in list fields with dynamic length — contract needs to handle list iteration, not just static dot-paths.

## Common Pitfalls

- **Nested field access on Pydantic models** — Dot-paths like `config.vpc_access.connector` require recursive getattr that handles None intermediaries. Use a safe `get_nested()` helper.
- **Optional ref fields** — Many ref fields are optional (e.g. `service_account` on Cloud Run). Validation must skip empty/None values, not treat them as broken refs.
- **`node:` prefix format** — Current refs use `node:name.attribute` prefix. The contract's `field` is the config dot-path, but the *value* at that path uses the `node:` format. Validation must parse the value to extract the target node name.
