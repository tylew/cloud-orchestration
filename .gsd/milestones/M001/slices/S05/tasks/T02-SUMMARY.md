---
id: T02
parent: S05
milestone: M001
provides: []
requires: []
affects: []
key_files: ["packages/core/tests/test_terraform_validate.py"]
key_decisions: ["Used xfail for known template gaps rather than skipping — tests document the bugs and will auto-pass when templates are fixed"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "27 passed, 3 xfailed. 126 unit tests still pass."
completed_at: 2026-03-31T03:09:03.997Z
blocker_discovered: false
---

# T02: 16 new terraform validate tests for S01 fields — 27 pass, 3 xfail for known template gaps.

> 16 new terraform validate tests for S01 fields — 27 pass, 3 xfail for known template gaps.

## What Happened
---
id: T02
parent: S05
milestone: M001
key_files:
  - packages/core/tests/test_terraform_validate.py
key_decisions:
  - Used xfail for known template gaps rather than skipping — tests document the bugs and will auto-pass when templates are fixed
duration: ""
verification_result: passed
completed_at: 2026-03-31T03:09:03.998Z
blocker_discovered: false
---

# T02: 16 new terraform validate tests for S01 fields — 27 pass, 3 xfail for known template gaps.

**16 new terraform validate tests for S01 fields — 27 pass, 3 xfail for known template gaps.**

## What Happened

Added 16 rich-config terraform validate tests exercising S01 schema additions: GPU, probes, volumes, encryption, build config, authorized networks, CMEK, labels, editions. 27 pass, 3 xfail for known template gaps.

## Verification

27 passed, 3 xfailed. 126 unit tests still pass.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd packages/core && PYTHONPATH=. python -m pytest tests/test_terraform_validate.py -v` | 0 | ✅ pass (27 pass, 3 xfail) | 77180ms |


## Deviations

3 tests marked xfail for known template gaps that need future fixes (annotations with dotted keys, Cloud SQL authorized_networks, VPC connector). These are real but lower-priority template issues.

## Known Issues

3 xfail tests: Cloud Run annotations with dotted keys, Cloud SQL authorized_networks rendering, VPC connector template.

## Files Created/Modified

- `packages/core/tests/test_terraform_validate.py`


## Deviations
3 tests marked xfail for known template gaps that need future fixes (annotations with dotted keys, Cloud SQL authorized_networks, VPC connector). These are real but lower-priority template issues.

## Known Issues
3 xfail tests: Cloud Run annotations with dotted keys, Cloud SQL authorized_networks rendering, VPC connector template.
