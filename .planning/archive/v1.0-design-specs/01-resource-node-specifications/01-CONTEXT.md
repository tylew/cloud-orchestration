# Phase 1: Resource Node Specifications - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Document lifecycle state machines, mutability rules, and validation constraints for all 22+ node types in the platform. This is a design specification phase — no code changes. The deliverable is a set of documents that downstream phases (deploy engine, IAM, networking, database lifecycle) can reference to understand exactly what each resource type does on create, update, and delete.

</domain>

<decisions>
## Implementation Decisions

### Document Organization
- **D-01:** Organize specs by category (Compute, Data, Messaging, Network, Security, External) using a three-tier structure per category:
  1. **Rigid template doc** — standardized sections (state machine, field table, defaults, validation) applied identically to every node type in the category
  2. **Flexible narrative doc** — category-level patterns, shared behaviors, quirks that don't fit the rigid template
  3. **Specifics doc per resource** — deep-dive per individual node type for edge cases, GCP-specific gotchas, and things unique to that resource
- **D-02:** Categories follow the existing REGISTRY categories: Compute, Data, Messaging, Network, Security/Identity, External

### State Machine Depth
- **D-03:** Use platform-level states only (draft → deploying → deployed → updating → failed → destroying → destroyed). Do not model GCP internal intermediate states.
- **D-04:** Document failure states (that transitions can fail) but defer recovery design to deploy engine phases (Phase 3-5). Keep Phase 1 focused on happy path + failure markers.

### Child Type Treatment
- **D-05:** Document child types (firestore_collection, bigquery_table, cloud_sql_database, cloud_sql_table) inline under their parent's specifics doc, not as standalone specs.
- **D-06:** For the two-level nesting (cloud_sql → cloud_sql_database → cloud_sql_table), document all three flat under the cloud_sql specifics doc. One place to understand the full Cloud SQL hierarchy.

### Mutability Source of Truth
- **D-07:** Use Terraform provider's ForceNew annotations as the primary source for mutability classification. Fall back to GCP API docs only for fields where Terraform docs are ambiguous.
- **D-08:** Pin and document the Google Terraform provider version (e.g., ~5.0) used for mutability research. Add a "last verified" date per category doc so classifications can be re-validated when the provider updates.
- **D-09:** Only classify fields that map to actual Terraform arguments. Platform-level metadata fields (Firestore-only) are always mutable by definition and don't need classification.

### Claude's Discretion
- State machine archetype strategy: Claude may define shared lifecycle archetypes (simple CRUD, parent-child, compute with image, network with dependencies) and map types to archetypes where lifecycles are identical, or document each type individually — whichever reduces redundancy without sacrificing clarity.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core Schemas & Registry
- `packages/core/schemas/enums.py` — NodeType enum (all 22 types), ActionType, CHILD_PARENT_MAP hierarchy
- `packages/core/schemas/base.py` — Envelope, BaseNode, GlobalConfig Pydantic models
- `packages/core/registry.py` — REGISTRY dict mapping NodeType → ComponentDefinition (terraform_resource, category, iam_scope, default_outputs)
- `packages/core/schemas/configs/__init__.py` — TYPE_TO_CONFIG mapping

### Per-Type Config Models
- `packages/core/schemas/configs/` — 22 Pydantic config model files, one per node type (defines current field definitions)

### Validation & DAG
- `packages/core/validation.py` — Existing cross-node validation rules and REQUIRED_FIELDS
- `packages/core/dag.py` — BlueprintDAG class (topological sort, cycle detection)

### Terraform Templates
- `packages/core/terraform/templates/` — 18 Jinja2 .tf.j2 templates showing current TF resource generation per type

### Infrastructure
- `infra/host/main.tf` — Host project Terraform config (google provider ~5.0 — use this version for mutability research)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `packages/core/schemas/configs/`: 22 per-type Pydantic config models already define all config fields with types and optional/required markers. These are the starting point for field inventories.
- `packages/core/registry.py`: REGISTRY already defines terraform_resource, category, is_compute, iam_scope, and default_outputs for every type. This metadata informs the rigid template sections.
- `packages/core/schemas/enums.py`: CHILD_PARENT_MAP defines the parent-child hierarchy. COMPUTE_TYPES and ACTION_VALID_TARGETS define behavioral categories.

### Established Patterns
- One config model per node type in `packages/core/schemas/configs/` — field names use camelCase with `# noqa: N815` for Pydantic/frontend JSON compatibility
- `extra="allow"` on BaseNode means nodes can carry arbitrary fields — specs should note which fields are spec'd vs pass-through
- `ComponentDefinition` is frozen dataclass — registry entries are immutable at runtime

### Integration Points
- Downstream Phase 2 (Dependency & Convention Rules) will reference these specs for inter-resource dependency edges
- Phase 3-5 (Deploy Engine) will reference state machines for deploy sequencing
- Phase 6 (IAM) will reference iam_scope and iam_terraform_resource fields
- Phase 7 (Networking) will reference network category types specifically

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for document structure and formatting within the three-tier framework.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-resource-node-specifications*
*Context gathered: 2026-03-26*
