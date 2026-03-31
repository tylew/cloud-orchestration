---
estimated_steps: 10
estimated_files: 9
skills_used: []
---

# T01: Fix templates grounded in Terraform provider specs via MCP

For each failing node type, use the Terraform MCP to pull the provider spec and understand the correct resource structure, argument names, and required references. Cross-reference against our templates to identify every mismatch.

Node types to fix via MCP:
- subnet (google_compute_subnetwork) — network ref
- cloud_run (google_cloud_run_v2_service) — service_account ref, output naming
- cloud_run_job (google_cloud_run_v2_job) — service_account ref, output naming
- cloud_function (google_cloudfunctions2_function) — variable refs, service_account
- firestore (google_firestore_database) — resource naming vs output refs
- pubsub_subscription (google_pubsub_subscription) — topic ref
- service_account (google_service_account) — output structure

For each: pull spec via MCP, compare template, fix template + resolver.

## Inputs

- `Terraform MCP provider specs for each failing type`
- `terraform validate error output from test_terraform_validate.py`

## Expected Output

- `Fixed resolver.py with proper node-name-to-TF-resource-ref resolution`
- `Fixed templates for all failing types`
- `Fixed outputs.tf generation`

## Verification

cd packages/core && PYTHONPATH=. python -m pytest tests/test_terraform_validate.py -v
