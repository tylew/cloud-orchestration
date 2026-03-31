# S02: Unified Contract System — Slice Context

## Decisions
- D008: IAM role mapping belongs in platform/terraform layer, not core
- D009: Three-layer separation — core surfaces typed edges, platform owns role registry, generator combines them

## Design

### Task Order (7 tasks, ~5h30m total)

**T01: Create ServiceContract models** (30m)
- contracts.py with ResourceRef, DataRef, SecretRef, EventRef, InvokeRef, ServiceContract
- Wire `contract: ServiceContract | None = None` into CloudRunConfig, CloudRunJobConfig, CloudFunctionConfig
- contracts.py must NOT import from configs/ (circular dep avoidance)
- Tests: model instantiation, JSON round-trip, Envelope integration, backward compat

**T02: Extend BlueprintDAG** (45m)
- _build_graph(): add contract ref edges as REAL ordering edges (resolve config via TYPE_TO_CONFIG)
- typed_edges(): returns (source, target, target_type, access_type) tuples
- Contract access types: DataRef=ref.access, SecretRef='read', EventRef=ref.direction, InvokeRef='invoke'
- Plain depends_on edges default to 'read'. Overlap: contract wins.
- Tests: ordering, typed_edges, overlap, cycles

**T03: Create iam_registry.py** (30m)  
- Move IAM_ROLE_MAP to packages/core/core/terraform/iam_registry.py
- Normalize access types: read→Read, write→Write, read_write→Write, publish→Emit, subscribe→Read, enqueue→Enqueue, invoke→Invoke
- IamBinding dataclass: role, tf_resource_type, iam_scope
- resolve_iam_binding() uses IAM_ROLE_MAP + REGISTRY iam_scope/iam_terraform_resource
- Move PRIVATE_ACCESS_TYPES to enums.py, fix auto_provision import
- Don't delete iam_mappings.py yet (T05 does that)

**T04: Rewrite generator.py** (1h30m) — CRITICAL
- Replace resolver.topological_sort() with BlueprintDAG
- Rewrite _render_iam_bindings(dag, nodes) to use typed_edges() + resolve_iam_binding()
- Resource-scope IAM: use _IAM_SCOPE_ATTR mapping for correct TF attribute per resource type
- Backward compat: depends_on without contract → 'read' → same Read roles as before
- Note: resource-scope targets now get resource-level IAM (more correct, may change TF output)

**T05: Delete dead code** (30m)
- Delete iam_mappings.py entirely
- Delete topological_sort() from resolver.py (keep resolve_node_ref)
- Remove MCP tools/nodes.py dead IAM write block
- Delete test_iam_mappings.py

**T06: Revive field_resolution + validate_contracts** (1h)
- Copy archive/service-contracts/field_resolution.py, fix imports
- validate_contracts(): DataRef→DATA_TYPES, SecretRef→secret_manager, EventRef→MESSAGING_TYPES, InvokeRef→COMPUTE_TYPES
- Field validation via field_resolution.resolve_field_ref()
- Wire into validate_blueprint()
- Revive archived tests, write new contract validation tests

**T07: Integration test** (45m)
- Full pipeline: contract blueprint → validation → DAG ordering → TF generation with correct IAM
- Backward compat test
- Overlap test (contract wins)
- Terraform validate (xfail if no terraform)

## Key Files Reference
- Current generator.py: packages/core/core/terraform/generator.py (536 lines, _render_iam_bindings at ~165)
- Current dag.py: packages/core/core/dag.py (88 lines, BlueprintDAG class)
- Current iam_mappings.py: packages/core/core/iam_mappings.py (68 lines, TO BE DELETED)
- Current resolver.py: packages/core/core/terraform/resolver.py (75 lines, topological_sort TO BE DELETED)
- Registry: packages/core/core/registry.py (has iam_scope/iam_terraform_resource — NEVER CONSUMED currently)
- Archived field_resolution: archive/service-contracts/field_resolution.py (170 lines, mature)
- MCP nodes: packages/mcp/tools/nodes.py (dead IAM write at ~218-227)
- Auto provision: packages/core/core/auto_provision.py (imports PRIVATE_ACCESS_TYPES from iam_mappings)
