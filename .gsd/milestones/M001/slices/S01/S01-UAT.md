# S01: Terraform Spec Audit & Schema Completeness — UAT

**Milestone:** M001
**Written:** 2026-03-30T23:17:28.577Z

## UAT: Terraform Spec Audit\n\n### Test: Schema backward compatibility\n1. Create a Cloud Run node config with only `image` and `service_account`\n2. Verify it parses without error\n3. Verify all new fields have sensible defaults\n\n### Test: New fields accepted\n1. Create a Cloud Run config with `gpu: '1'`, `readiness_probe`, `description`\n2. Verify it parses and all fields accessible\n\n### Test: Template rendering\n1. Generate Terraform for a Cloud Run service with new fields\n2. Verify HCL includes the new fields in correct positions\n\n### Test: Full regression\n- `pytest packages/tests/ -q --ignore=packages/tests/integration` → 225 passed
