---
id: S03
parent: M001
milestone: M001
provides:
  - Standalone test UI for all core package features (types, validation, terraform, DAG)
requires:
  - slice: S02
    provides: Service contract model for DAG visualization
affects:
  []
key_files:
  - packages/core/explorer/app.py
  - packages/core/explorer/static/index.html
key_decisions:
  - Single HTML file with inline JS/CSS — no npm, no build step
  - Dynamic form generation from Pydantic JSON schema at runtime
  - DAG layout uses parallel batches from core dag.py for column positioning
  - Color-coded categories: Compute=blue, Data=green, Messaging=yellow, Network=purple, Security=red, Storage=cyan, Identity=pink
patterns_established:
  - Core Explorer pattern: lightweight FastAPI app that imports core package directly and exposes its features via REST + HTML UI
observability_surfaces:
  - GET /api/types serves as a health check — returns all registered types
drill_down_paths:
  - .gsd/milestones/M001/slices/S03/tasks/T01-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-03-31T07:48:11.826Z
blocker_discovered: false
---

# S03: Archive Dead Code & Minimal Test UI

**Built Core Explorer — standalone web UI for browsing all 20 resource types, building blueprints, running validation, generating Terraform, and visualizing the DAG.**

## What Happened

Built a single-task slice delivering a standalone developer tool for exercising the entire core package. The Core Explorer is a FastAPI app (`packages/core/explorer/`) serving four API endpoints (types, validate, terraform, dag) and a single-page HTML UI with inline JS/CSS — zero build step required.

The UI provides: a resource palette showing all 20 types grouped by category (color-coded), a blueprint builder with dynamic config forms generated from Pydantic JSON schemas, a dependency editor, live validation with error/warning display, Terraform generation with per-file HCL preview, and DAG visualization using SVG with parallel-batch column layout.

Verified end-to-end: app starts, all four API endpoints return correct data, browser walkthrough confirmed a 7-node blueprint through validation → Terraform generation → DAG rendering.

## Verification

- `curl http://localhost:8100/api/types` returns all 20 resource types with config schemas ✅
- `POST /api/validate` with empty blueprint returns `{valid: true, issues: []}` ✅
- `GET /` serves the HTML UI ✅
- Browser verification: 7-node blueprint → validation → terraform → DAG (from T01) ✅

## Requirements Advanced

- R005 — Core Explorer delivers a functional UI for browsing types, building blueprints, validation, Terraform generation, and DAG visualization

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

The slice plan originally included archiving dead frontend code (R006). During planning, scope was narrowed to just the Core Explorer UI (R005). Dead code archival was not performed in this slice.

## Known Limitations

Config form only renders top-level string/number/boolean/enum fields — nested objects and arrays require manual JSON editing. The DAG endpoint and Terraform endpoint depend on core package internals that may need updates as schemas evolve.

## Follow-ups

R006 (dead code archival) still needs a dedicated slice. Nested config form rendering could be improved in a future iteration.

## Files Created/Modified

- `packages/core/explorer/__init__.py` — Package init
- `packages/core/explorer/app.py` — FastAPI app with 4 API endpoints: types, validate, terraform, dag
- `packages/core/explorer/static/index.html` — Single-page UI with resource palette, blueprint builder, validation, terraform preview, DAG visualization
