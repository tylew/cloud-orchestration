# S01: resource_id on BaseNode + Registry Naming Templates — UAT

**Milestone:** M003
**Written:** 2026-03-31T16:48:47.299Z

## UAT: resource_id on BaseNode + Registry Naming Templates

### Preconditions
- Python 3.12+ with packages/core installed in editable mode
- Working directory: packages/core

### Test 1: resource_id Auto-Generation
1. `python -c "from core.schemas.base import BaseNode; n = BaseNode(slug='test', name='test', type='cloud_run', config={}); print(n.id, n.resource_id); assert len(n.resource_id) == 8; assert n.resource_id == n.id.replace('-','')[:8]"`
2. **Expected:** Prints UUID and 8-char hex resource_id derived from it

### Test 2: resource_id Determinism
1. `python -c "from core.schemas.base import BaseNode; n1 = BaseNode(slug='a', name='a', type='cloud_run', config={}, id='550e8400-e29b-41d4-a716-446655440000'); n2 = BaseNode(slug='b', name='b', type='cloud_run', config={}, id='550e8400-e29b-41d4-a716-446655440000'); assert n1.resource_id == n2.resource_id; print('PASS:', n1.resource_id)"`
2. **Expected:** Same id produces same resource_id: `550e8400`

### Test 3: resolve_gcp_name Patterns
1. `python -c "from core.terraform.naming import resolve_gcp_name; from core.registry import REGISTRY; from core.schemas.base import BaseNode; n = BaseNode(slug='api', name='api', type='cloud_run', config={}); print(resolve_gcp_name(n, 'dev', REGISTRY))"`
2. **Expected:** Output matches `dev-{8-char-hex}` pattern

### Test 4: Service Account Prefix
1. `python -c "from core.terraform.naming import resolve_gcp_name; from core.registry import REGISTRY; from core.schemas.base import BaseNode; n = BaseNode(slug='sa', name='sa', type='service_account', config={}); name = resolve_gcp_name(n, 'dev', REGISTRY); assert name.startswith('sa-'); print('PASS:', name)"`
2. **Expected:** Name starts with `sa-`

### Test 5: Config ID Fields Removed
1. `python -c "from core.schemas.configs.service_account import ServiceAccountConfig; from core.schemas.configs.bigquery import BigQueryConfig; assert 'account_id' not in ServiceAccountConfig.model_fields; assert 'dataset_id' not in BigQueryConfig.model_fields; print('PASS: ID fields removed')"`
2. **Expected:** PASS — fields no longer exist

### Test 6: Backward Compatibility (extra=ignore)
1. `python -c "from core.schemas.configs.bigquery import BigQueryConfig; c = BigQueryConfig(dataset_id='old-value'); print('PASS: old field silently ignored')"`
2. **Expected:** No validation error — extra fields ignored

### Test 7: Full Test Suite
1. `cd packages/core && python -m pytest tests/ --ignore=tests/test_terraform_validate.py -x -q`
2. **Expected:** 137 passed

### Test 8: Terraform Validate
1. `cd packages/core && python -m pytest tests/test_terraform_validate.py -x -q`
2. **Expected:** 27 passed, 3 xfailed
