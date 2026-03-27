# Phase 1: Resource Node Specifications - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-26
**Phase:** 01-resource-node-specifications
**Areas discussed:** Document organization, State machine depth, Child type treatment, Mutability source of truth

---

## Document Organization

| Option | Description | Selected |
|--------|-------------|----------|
| One doc per node type | 22+ separate files mirroring configs/ pattern | |
| Grouped by category | 6-7 docs grouping by REGISTRY categories | ✓ (base) |
| Single comprehensive doc | One large spec document with sections per type | |
| You decide | Let Claude choose | |

**User's choice:** Grouped by category, but with a three-tier structure:
1. Rigid template doc per category (standardized sections for every type)
2. Flexible narrative doc per category (shared patterns, quirks)
3. Specifics doc per individual resource (edge cases, GCP gotchas)

**Follow-up — Template rigidity:**

| Option | Description | Selected |
|--------|-------------|----------|
| Rigid template per type | Same sections for every node type | ✓ (tier 1) |
| Flexible per type | Sections vary by type complexity | ✓ (tier 2) |

**User's choice:** Both — rigid template as tier 1, flexible narrative as tier 2, plus per-resource specifics as tier 3.

---

## State Machine Depth

| Option | Description | Selected |
|--------|-------------|----------|
| Platform-level states only | What our Firestore status fields represent | ✓ |
| GCP-aware states | Include GCP internal intermediate states | |
| Two-layer model | Platform states mapped to GCP states | |
| You decide | Let Claude choose | |

**User's choice:** Platform-level states only

**Follow-up — Error recovery paths:**

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, include recovery paths | Document what platform does on failure | |
| Failure states only, no recovery | Mark failures, defer recovery to Phase 3-5 | ✓ |
| You decide | Let Claude choose | |

**User's choice:** Failure states only, no recovery

**Follow-up — Shared state machines:**

| Option | Description | Selected |
|--------|-------------|----------|
| Shared where identical | Define lifecycle archetypes, map types to them | |
| Every type gets its own | Redundant but unambiguous | |
| You decide | Let Claude choose | ✓ |

**User's choice:** Claude's discretion

---

## Child Type Treatment

| Option | Description | Selected |
|--------|-------------|----------|
| Inline under parent | Document within parent's specifics doc | ✓ |
| Standalone but cross-referenced | Own specifics docs with cross-refs | |
| Hybrid: shared lifecycle, own fields | Lifecycle inline, fields standalone | |
| You decide | Let Claude choose | |

**User's choice:** Inline under parent

**Follow-up — Two-level nesting (cloud_sql hierarchy):**

| Option | Description | Selected |
|--------|-------------|----------|
| Flat under cloud_sql | All three documented together | ✓ |
| Nested mirrors code | cloud_sql_database under cloud_sql, cloud_sql_table under cloud_sql_database | |
| You decide | Let Claude choose | |

**User's choice:** Flat under cloud_sql

---

## Mutability Source of Truth

| Option | Description | Selected |
|--------|-------------|----------|
| Terraform provider docs | Use ForceNew annotations | |
| GCP API behavior | Use GCP API docs | |
| Terraform first, GCP for gaps | Default to TF, fallback to GCP API | ✓ |
| You decide | Let Claude choose | |

**User's choice:** Terraform first, GCP for gaps

**Follow-up — Provider version pinning:**

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, pin provider version | Document which version used, add last verified date | ✓ |
| No, keep it generic | Classifications without version pinning | |
| You decide | Let Claude choose | |

**User's choice:** Yes, pin provider version

**Follow-up — Platform-only fields:**

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, classify everything | Including platform-mutable category | |
| TF-mapped fields only | Skip platform metadata fields | ✓ |
| You decide | Let Claude choose | |

**User's choice:** TF-mapped fields only

---

## Claude's Discretion

- State machine archetype strategy (shared archetypes vs individual per type)

## Deferred Ideas

None
