---
estimated_steps: 2
estimated_files: 7
skills_used: []
---

# T01: Audit & update Compute types (Cloud Run, Cloud Run Job, Cloud Function)

Use Terraform MCP to pull full specs for google_cloud_run_v2_service, google_cloud_run_v2_job, google_cloudfunctions2_function. Compare against CloudRunConfig, CloudRunJobConfig, CloudFunctionConfig. Add missing fields to schemas. Update Jinja2 templates. Add tests for new fields.

These are the most complex types (~80-120 lines each) and the most critical for the platform.

## Inputs

- `Terraform MCP: google_cloud_run_v2_service, google_cloud_run_v2_job, google_cloudfunctions2_function specs`

## Expected Output

- `Updated schema configs for 3 compute types`
- `Updated Jinja2 templates for 3 compute types`
- `New/updated tests`

## Verification

pytest packages/tests/test_terraform.py -v && pytest packages/tests/test_validation.py -v
