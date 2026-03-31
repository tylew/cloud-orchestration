---
id: T01
parent: S05
milestone: M001
provides: []
requires: []
affects: []
key_files: ["packages/core/core/terraform/resolver.py", "packages/core/core/terraform/generator.py", "packages/core/core/terraform/templates/firestore.tf.j2", "packages/core/tests/test_terraform_validate.py"]
key_decisions: ["Enhanced resolve_node_ref to handle bare node names → TF resource references", "Standardized Firestore template to use node.name as resource name (consistent with all other templates)", "Variables.tf now conditionally declares cb_source_bucket when cloud functions present"]
patterns_established: []
drill_down_paths: []
observability_surfaces: []
duration: ""
verification_result: "14/14 terraform validate tests pass. 126 unit tests pass."
completed_at: 2026-03-31T02:57:56.306Z
blocker_discovered: false
---

# T01: Fixed 3 categories of template bugs — resolver now handles bare node names, firestore naming standardized, cloud function variables declared.

> Fixed 3 categories of template bugs — resolver now handles bare node names, firestore naming standardized, cloud function variables declared.

## What Happened
---
id: T01
parent: S05
milestone: M001
key_files:
  - packages/core/core/terraform/resolver.py
  - packages/core/core/terraform/generator.py
  - packages/core/core/terraform/templates/firestore.tf.j2
  - packages/core/tests/test_terraform_validate.py
key_decisions:
  - Enhanced resolve_node_ref to handle bare node names → TF resource references
  - Standardized Firestore template to use node.name as resource name (consistent with all other templates)
  - Variables.tf now conditionally declares cb_source_bucket when cloud functions present
duration: ""
verification_result: passed
completed_at: 2026-03-31T02:57:56.306Z
blocker_discovered: false
---

# T01: Fixed 3 categories of template bugs — resolver now handles bare node names, firestore naming standardized, cloud function variables declared.

**Fixed 3 categories of template bugs — resolver now handles bare node names, firestore naming standardized, cloud function variables declared.**

## What Happened

Fixed three categories of template bugs:\n1. Node reference resolution — enhanced resolve_node_ref to handle bare node names, not just node:X.Y syntax. This fixed subnet network ref, pubsub subscription topic ref.\n2. Firestore resource naming — template used config.database_id as resource name but outputs used node.name. Standardized to node.name.\n3. Cloud Function variables — cb_source_bucket variable now conditionally declared.\n\nAll 14 terraform validate tests pass. 126 unit tests unaffected.

## Verification

14/14 terraform validate tests pass. 126 unit tests pass.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd packages/core && PYTHONPATH=. python -m pytest tests/test_terraform_validate.py -v` | 0 | ✅ pass | 34400ms |
| 2 | `cd packages/core && PYTHONPATH=. python -m pytest tests/ -q -k 'not test_terraform_validate'` | 0 | ✅ pass | 220ms |


## Deviations

Didn't need the Terraform MCP for most fixes — the errors were clear from terraform validate output. The resolver enhancement was the key fix covering most failures. Test fixture account_ids were too short (5 chars vs GCP 6+ minimum).

## Known Issues

None.

## Files Created/Modified

- `packages/core/core/terraform/resolver.py`
- `packages/core/core/terraform/generator.py`
- `packages/core/core/terraform/templates/firestore.tf.j2`
- `packages/core/tests/test_terraform_validate.py`


## Deviations
Didn't need the Terraform MCP for most fixes — the errors were clear from terraform validate output. The resolver enhancement was the key fix covering most failures. Test fixture account_ids were too short (5 chars vs GCP 6+ minimum).

## Known Issues
None.
