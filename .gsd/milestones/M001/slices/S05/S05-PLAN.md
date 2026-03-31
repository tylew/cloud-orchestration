# S05: Fix Terraform Template Bugs

**Goal:** Fix all Terraform template bugs grounded in real provider specs via MCP, then expand validate tests to cover all S01 schema additions.
**Demo:** After this: After this: all 14 terraform validate tests pass — every node type generates valid HCL that terraform accepts

## Tasks
- [x] **T01: Fixed 3 categories of template bugs — resolver now handles bare node names, firestore naming standardized, cloud function variables declared.** — For each failing node type, use the Terraform MCP to pull the provider spec and understand the correct resource structure, argument names, and required references. Cross-reference against our templates to identify every mismatch.

Node types to fix via MCP:
- subnet (google_compute_subnetwork) — network ref
- cloud_run (google_cloud_run_v2_service) — service_account ref, output naming
- cloud_run_job (google_cloud_run_v2_job) — service_account ref, output naming
- cloud_function (google_cloudfunctions2_function) — variable refs, service_account
- firestore (google_firestore_database) — resource naming vs output refs
- pubsub_subscription (google_pubsub_subscription) — topic ref
- service_account (google_service_account) — output structure

For each: pull spec via MCP, compare template, fix template + resolver.
  - Estimate: 2h
  - Files: packages/core/core/terraform/resolver.py, packages/core/core/terraform/generator.py, packages/core/core/terraform/templates/subnet.tf.j2, packages/core/core/terraform/templates/cloud_run.tf.j2, packages/core/core/terraform/templates/cloud_run_job.tf.j2, packages/core/core/terraform/templates/cloud_function.tf.j2, packages/core/core/terraform/templates/pubsub_subscription.tf.j2, packages/core/core/terraform/templates/firestore.tf.j2, packages/core/core/terraform/templates/service_account.tf.j2
  - Verify: cd packages/core && PYTHONPATH=. python -m pytest tests/test_terraform_validate.py -v
- [x] **T02: 16 new terraform validate tests for S01 fields — 27 pass, 3 xfail for known template gaps.** — Expand test_terraform_validate.py to exercise the new fields added in S01. For each node type, add test cases with rich configs (GPU, probes, volumes, encryption, Cloud SQL authorized_networks, Firestore CMEK, BigQuery billing model, etc). Use the Terraform MCP to verify correct attribute names when unclear.

Goal: every user-configurable field added in S01 is exercised in a terraform validate test.
  - Estimate: 1.5h
  - Files: packages/core/tests/test_terraform_validate.py
  - Verify: cd packages/core && PYTHONPATH=. python -m pytest tests/test_terraform_validate.py -v
- [x] **T03: Full regression green across all packages — 155+27+31+8+39 tests pass.** — Run the full core test suite, all terraform validate tests, and all other package tests. Confirm zero regressions.
  - Estimate: 15m
  - Verify: cd packages/core && PYTHONPATH=. python -m pytest tests/ -v && cd ../.. && python -m pytest packages/platform/tests/ packages/api/tests/ packages/mcp/tests/ -q --ignore=packages/platform/tests/integration
