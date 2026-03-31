---
estimated_steps: 1
estimated_files: 7
skills_used: []
---

# T05: Audit & update Security + Storage types (Service Account, Secret Manager, GCS Bucket)

Use Terraform MCP to pull full specs for google_service_account, google_secret_manager_secret, google_storage_bucket. Service Account and Secret Manager are thin (~13 lines each). GCS Bucket is moderate (~40 lines). Fill gaps.

## Inputs

- `Terraform MCP specs for 3 security/storage resources`

## Expected Output

- `Updated schemas and templates for 3 types`
- `New tests`

## Verification

pytest packages/tests/test_terraform.py -v
