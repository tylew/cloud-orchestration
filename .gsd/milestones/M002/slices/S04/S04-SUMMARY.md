---
id: S04
parent: M002
milestone: M002
provides:
  - Explorer API with ref metadata, naming info, and name preview endpoints
  - Explorer UI with ref dropdowns, name preview, immutable warnings, and inline rename
requires:
  - slice: S01
    provides: UUID-based node identity enabling safe rename
  - slice: S02
    provides: RESOURCE_REFS contract for ref field metadata
  - slice: S03
    provides: Naming conventions and preview_gcp_name in registry
affects:
  []
key_files:
  - packages/core/explorer/app.py
  - packages/core/explorer/static/index.html
  - packages/core/tests/test_explorer_api.py
key_decisions:
  - (none)
patterns_established:
  - Explorer API enriches /api/types with cross-cutting metadata (refs, naming) rather than separate endpoints per concern
  - Vanilla JS explorer UI consumes typed metadata for intelligent form rendering (dropdowns, warnings)
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M002/slices/S04/tasks/T01-SUMMARY.md
  - .gsd/milestones/M002/slices/S04/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-03-31T09:14:07.897Z
blocker_discovered: false
---

# S04: Explorer UI — Reference Dropdowns, Naming Preview, Rename

**Explorer API and UI now expose ref dropdowns filtered by target type, GCP name previews, immutable-name warnings, and inline rename**

## What Happened

T01 enhanced the explorer FastAPI backend: `/api/types` now includes `refs` (from RESOURCE_REFS) and `naming` (template + immutability from ComponentDefinition) per type. A new `POST /api/preview-name` endpoint constructs a BaseNode and returns `preview_gcp_name()` output. 8 new tests cover refs metadata, naming metadata, preview, and error cases.

T02 updated the vanilla JS explorer UI (`index.html`) with four features: (1) ref config fields render as `<select>` dropdowns filtered to nodes matching the ref's `target_type`, (2) each node card shows an async GCP name preview via `/api/preview-name`, (3) immutable types display a yellow warning badge, and (4) node names are editable inline with kebab-case validation — safe because S01's UUID-based depends_on means renames don't break dependencies.

## Verification

All 8 test_explorer_api.py tests pass. Full suite: 203 passed, 0 failed. index.html contains preview-name and immutable references confirmed via grep.

## Requirements Advanced

- R005 — Explorer UI now provides intelligent config experience with ref dropdowns, name previews, and inline rename — advancing the 'dead simple test UI' goal

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

None.

## Known Limitations

List-type ref fields (is_list=true) still render in JSON editor rather than as multi-select dropdowns. Name preview requires a network round-trip per node — no client-side caching.

## Follow-ups

None.

## Files Created/Modified

- `packages/core/explorer/app.py` — Added refs and naming metadata to /api/types, added POST /api/preview-name endpoint
- `packages/core/explorer/static/index.html` — Added ref dropdowns, GCP name preview, immutable warnings, and inline rename
- `packages/core/tests/test_explorer_api.py` — New test file with 8 tests for explorer API endpoints
