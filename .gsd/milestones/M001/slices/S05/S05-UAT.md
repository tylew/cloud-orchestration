# S05: Fix Terraform Template Bugs — UAT

**Milestone:** M001
**Written:** 2026-03-31T03:11:12.455Z

## UAT: Terraform Template Validation\n\n### Test: Every node type produces valid HCL\n1. Run `cd packages/core && PYTHONPATH=. python -m pytest tests/test_terraform_validate.py -v`\n2. Verify 27 pass, 3 xfail\n3. No failures\n\n### Test: Rich configs with new S01 fields validate\n1. Check GPU, probes, volumes, CMEK, authorized networks tests all pass\n2. These exercise the fields added during the S01 spec audit\n\n### Test: Full regression\n1. All core unit tests pass (155)\n2. All platform/api/mcp tests pass (61)"
