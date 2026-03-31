---
id: T02
parent: S04
milestone: M002
provides: []
requires: []
affects: []
key_files: ["packages/core/explorer/static/index.html"]
key_decisions: []
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "pytest tests/test_explorer_api.py (8 passed), grep confirmed preview-name and immutable strings present in index.html"
completed_at: 2026-03-31T09:13:15.415Z
blocker_discovered: false
---

# T02: Explorer UI now renders ref fields as filtered dropdowns, shows GCP name preview per node, displays immutable-name warnings, and supports inline rename

> Explorer UI now renders ref fields as filtered dropdowns, shows GCP name preview per node, displays immutable-name warnings, and supports inline rename

## What Happened
---
id: T02
parent: S04
milestone: M002
key_files:
  - packages/core/explorer/static/index.html
key_decisions:
  - (none)
duration: ""
verification_result: passed
completed_at: 2026-03-31T09:13:15.415Z
blocker_discovered: false
---

# T02: Explorer UI now renders ref fields as filtered dropdowns, shows GCP name preview per node, displays immutable-name warnings, and supports inline rename

**Explorer UI now renders ref fields as filtered dropdowns, shows GCP name preview per node, displays immutable-name warnings, and supports inline rename**

## What Happened

Updated index.html with four features: ref field dropdowns filtered by target_type, async GCP name preview via /api/preview-name, immutable name warning badges, and inline rename with kebab-case validation.

## Verification

pytest tests/test_explorer_api.py (8 passed), grep confirmed preview-name and immutable strings present in index.html

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd packages/core && PYTHONPATH=. python -m pytest tests/test_explorer_api.py -v` | 0 | ✅ pass | 410ms |
| 2 | `grep -q 'preview-name' explorer/static/index.html` | 0 | ✅ pass | 10ms |
| 3 | `grep -q 'immutable' explorer/static/index.html` | 0 | ✅ pass | 10ms |


## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `packages/core/explorer/static/index.html`


## Deviations
None.

## Known Issues
None.
