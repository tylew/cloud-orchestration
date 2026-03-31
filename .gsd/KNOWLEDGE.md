# Knowledge

## Project Rules

- Backend must remain stateless — all state in Firestore — for Cloud Run horizontal scaling
- Blueprint schema changes require migration path; cannot break existing format
- `AUTH_DISABLED=true` + `ENVIRONMENT=dev` enables local dev without Firebase tokens
- Codegen infrastructure exists in `packages/core/codegen/` — `code_generator.py` (full app gen from internal graph) and `client_generator.py` (LRU-cached factory functions from dependencies)
- `field_resolution.py` already resolves field references across Firestore, Cloud SQL, and BigQuery schemas
- Firestore schema model is the most mature — has collections, subcollections, fields with types, TTL, indexes, ID strategies
- Frontend uses `@/` path alias mapping to `./src/*`
- Dev tenant: `yBi9vPkZ5HXNw7zyfSr7zltjojC2`, dev email: `tyler@pl4m.com`
- The InsightBoard, insight-store, and insight/* components may be dead code — verify before archiving

## Patterns

- Node config schemas live in `packages/core/schemas/configs/` — one file per node type
- Terraform templates in `packages/core/terraform/templates/` — Jinja2 `.tf.j2` files
- `TYPE_TO_CONFIG` in `packages/core/schemas/configs/__init__.py` maps NodeType → config Pydantic model
- Registry in `packages/core/registry.py` maps NodeType → ComponentDefinition with metadata
- Validation in `packages/core/validation.py` produces `ValidationIssue` results

## Lessons Learned

- Ref values in config are plain node name slugs (e.g. `"my-sa"`), not `node:name.attribute` format. The `node:name.attribute` pattern from the original spec was not implemented — validation and DAG inference both do direct name lookup.
- `packages/core/core/refs.py` RESOURCE_REFS contract uses `[]` notation in dot-paths (e.g. `env_vars[].secret`) to mark list-iteration fields. `get_nested()` handles this at runtime; `field_exists_on_model()` validates at test time.
- Python 3.12+ `types.UnionType` (from `X | Y` syntax) is not `typing.Union` — `field_exists_on_model()` in refs.py handles both for Pydantic config model introspection.
- `terraform validate` tests in test_terraform_validate.py take ~100s — they dominate test suite runtime. Use targeted test files (e.g. `tests/test_refs.py`) for fast iteration.

- Zero HCL diff as a verification strategy: wiring resolve_gcp_name into templates was validated by checking terraform validate output didn't change — proves refactoring correctness without inspecting every template.
- Building contracts (RESOURCE_REFS, naming conventions) as data structures rather than scattered logic enables multiple consumers (validation, DAG, UI, templates) from one source of truth.
- UUID-based identity decouples three concerns (stable identity, display name, GCP resource name) that were previously conflated — makes rename safe and simplifies cross-references.
- Building a subsystem in isolation without wiring it into real consumers leads to revert. Wire into at least one real consumer (e.g., terraform generator) in the same slice.
- `terraform validate` as test oracle catches real template bugs that unit tests miss — use it as the primary regression safety net for HCL generation.
- HashiCorp Terraform MCP server is effective for schema audits against provider specs.
- Package split (monolith → core/api/platform) under `packages/` — each has own `pyproject.toml` and test suite. Core packages now at `packages/core/core/` (note the double `core`).
- Slice completion artifacts can diverge from code reality if code is reverted post-completion — milestone verification must check actual code state.
- GCP resource names have per-type constraints (must start with letter, underscore vs hyphen) — naming templates must encode these per-type, not use a universal pattern.
- `extra='ignore'` on Pydantic config models provides backward compatibility when removing fields from schemas with existing Firestore documents.
- Root conftest.py with `collect_ignore_glob` prevents pytest from collecting archived code in `archive/`.
