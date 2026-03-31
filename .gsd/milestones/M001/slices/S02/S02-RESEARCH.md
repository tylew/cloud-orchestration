# Kill / Replace / Keep Plan — Unified Contract System

## File-by-File Disposition

### `packages/core/core/iam_mappings.py` — SPLIT AND MOVE

| Symbol | Lines | Action | Why |
|---|---|---|---|
| `IAM_ROLE_MAP` | 7-37 | **MOVE** to `packages/core/core/terraform/iam_registry.py` | Platform/TF concern, not core |
| `get_iam_role()` | 42-44 | **KILL** | Zero production callers. Only test. |
| `infer_iam_roles()` | 46-68 | **KILL** | Only caller is MCP update_node, which writes to a field nothing reads. Dead pipeline. |
| `PRIVATE_ACCESS_TYPES` | 39 | **KEEP in core** (move to `auto_provision.py` or `enums.py`) | Used by auto_provision.py — a core concern |

After: `iam_mappings.py` is deleted. `PRIVATE_ACCESS_TYPES` moves to where it's consumed. `IAM_ROLE_MAP` moves to terraform layer.

### `packages/core/core/terraform/resolver.py` — PARTIALLY KILL

| Symbol | Lines | Action | Why |
|---|---|---|---|
| `topological_sort()` | 50-75 | **KILL** | Replaced by BlueprintDAG.topological_sort(). Silently swallows cycles — dangerous. |
| `resolve_node_ref()` | 10-48 | **KEEP** | Useful for TF reference resolution in templates. No equivalent in BlueprintDAG. |

After: `resolver.py` keeps only `resolve_node_ref()`. Generator imports `BlueprintDAG` for ordering.

### `packages/core/core/terraform/generator.py` — REWRITE `_render_iam_bindings()`

| Symbol | Lines | Action | Why |
|---|---|---|---|
| `generate_terraform()` | 389-516 | **MODIFY** — replace `resolver.topological_sort()` call with `BlueprintDAG(envelope).topological_sort()` | Unify DAG |
| `preview_resources()` | 523-536 | **MODIFY** — same sort replacement | Consistency |
| `_render_iam_bindings()` | 165-244 | **REWRITE** — consume typed edges from BlueprintDAG, use moved IAM_ROLE_MAP, use registry `iam_scope`/`iam_terraform_resource` for correct IAM resource type | The core integration point |

The rewritten `_render_iam_bindings()` would:
1. Get typed edges from `BlueprintDAG.typed_edges()` — (source, target, target_type, access_type)
2. For contract edges: access_type comes from the contract ref (read/write/invoke/publish/etc)
3. For plain depends_on edges (no contract): default to "Read" (backward compat)
4. Look up `IAM_ROLE_MAP[(access_type, target_type)]` for the role
5. Use registry's `iam_scope` to decide: `google_project_iam_member` vs `google_bigquery_dataset_iam_member` vs resource-level IAM
6. Use registry's `iam_terraform_resource` for the TF resource type

### `packages/core/core/dag.py` — EXTEND

| Symbol | Lines | Action | Why |
|---|---|---|---|
| `BlueprintDAG.__init__()` | 16-23 | **MODIFY** — also resolve configs to read contracts | Need access to contract data |
| `_build_graph()` | 25-41 | **MODIFY** — incorporate contract ref edges alongside depends_on | Unify the graph |
| `topological_sort()` | 43-53 | **KEEP** | Already correct (graphlib, raises on cycles) |
| `validate_ordering()` | 55-75 | **KEEP** | Already correct |
| `parallel_batches()` | 77-88 | **KEEP** | Already correct |
| NEW: `typed_edges()` | — | **ADD** | Returns (source, target, target_type, access_type) for each edge. Contract edges carry their access type. Plain depends_on edges carry "Read" as default. |

### `packages/core/core/validation.py` — EXTEND

| Symbol | Lines | Action | Why |
|---|---|---|---|
| `validate_blueprint()` | ~280-350 | **MODIFY** — add `validate_contracts()` call | Validate contract refs |
| NEW: `validate_contracts()` | — | **ADD** | Validate target exists, correct type, field paths resolve. Bring back archived field_resolution.py logic. |

### `packages/core/core/schemas/contracts.py` — RE-CREATE

Same as old S02 models: ServiceContract, DataRef, SecretRef, EventRef, InvokeRef. These were fine.

### `packages/core/core/schemas/configs/cloud_run.py`, `cloud_run_job.py`, `cloud_function.py` — MODIFY

Add `contract: ServiceContract | None = None` to each. Same as old S02. Backward compatible.

### `packages/mcp/tools/nodes.py` — CLEAN UP

| Section | Lines | Action | Why |
|---|---|---|---|
| `infer_iam_roles` lazy import | 28-30 | **KILL** | Function being deleted |
| IAM inference in `update_node()` | 218-227 | **KILL** | Dead pipeline — writes to field nothing reads. IAM is now inferred at generation time only. |

### `packages/core/core/auto_provision.py` — MINOR MODIFY

| Symbol | Lines | Action | Why |
|---|---|---|---|
| `PRIVATE_ACCESS_TYPES` import | 8 | **MODIFY** — import from new location (enums.py or inline) | iam_mappings.py being deleted |

### `archive/service-contracts/field_resolution.py` — EVALUATE FOR REVIVAL

Mature field resolver. Either:
- Revive into `packages/core/core/field_resolution.py` for use by `validate_contracts()`
- Or rewrite the coarser validation from old S02 (simpler but less complete)

### New file: `packages/core/core/terraform/iam_registry.py` — CREATE

New home for `IAM_ROLE_MAP`. Also consumes registry's `iam_scope`/`iam_terraform_resource` to produce correct IAM TF resource types. Single function like `resolve_iam_binding(access_type, target_type) -> IamBinding` that returns role string + TF resource type + scope.

## Dependency Flow After Changes

```
User sets contract on compute node
  → Stored in node.config.contract (Firestore)
  → validate_blueprint() calls validate_contracts() (core)
    → Checks refs valid, types correct, fields resolve
  → BlueprintDAG._build_graph() includes contract edges (core)
    → topological_sort() orders correctly
    → typed_edges() exposes (source, target, type, access) (core)
  → generate_terraform() uses BlueprintDAG for ordering (terraform layer)
    → _render_iam_bindings() reads typed_edges() (terraform layer)
      → iam_registry.resolve_iam_binding() maps to IAM role (terraform layer)
      → registry.iam_scope decides IAM resource type (terraform layer)
      → Produces correct HCL
```

## What's NOT changing
- BaseNode.depends_on — still works, backward compatible. Contract edges are additive.
- resolve_node_ref() — still needed for TF template reference resolution
- auto_provision_for_node() — still creates SA/VPC, still mutates depends_on
- All existing TF templates — no template changes needed
- API handlers — no changes, they call generate_terraform() which gets smarter internally
- deploy_orchestrator.py — no changes, calls generate_terraform()
