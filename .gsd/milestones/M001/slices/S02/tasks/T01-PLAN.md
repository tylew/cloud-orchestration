---
estimated_steps: 10
estimated_files: 5
skills_used: []
---

# T01: Define ServiceContract models and wire into compute configs

Create the ServiceContract Pydantic model hierarchy (ResourceRef, DataRef, SecretRef, EventRef, InvokeRef, ServiceContract) in a new `contracts.py` module. Add `contract: ServiceContract | None = None` field to CloudRunConfig, CloudRunJobConfig, and CloudFunctionConfig. Write unit tests proving models serialize/deserialize correctly and blueprints with contracts parse without error.

Steps:
1. Create `packages/core/core/schemas/contracts.py` with all 6 models per spec (ResourceRef, DataRef, SecretRef, EventRef, InvokeRef, ServiceContract). Use `Literal['read', 'write', 'read_write']` for access types. `Literal['publish', 'subscribe', 'enqueue']` for EventRef direction.
2. Add `contract: ServiceContract | None = None` to CloudRunConfig, CloudRunJobConfig, CloudFunctionConfig. Import from contracts.py.
3. Create `packages/core/tests/test_contracts.py` with tests: model instantiation with all fields, JSON round-trip, optional fields default correctly, a full Envelope with a compute node + contract parses via `resolve_config_and_validate`.
4. Run full test suite to confirm no regressions.

Constraints:
- contracts.py must NOT import from configs/ (avoid circular imports — only validation code imports both)
- DataRef extends ResourceRef with collections/tables/fields lists
- All ref models share `node: str` and `description: str = ''`

## Inputs

- ``docs/specs/service-contract.md``
- ``packages/core/core/schemas/configs/cloud_run.py``
- ``packages/core/core/schemas/configs/cloud_run_job.py``
- ``packages/core/core/schemas/configs/cloud_function.py``

## Expected Output

- ``packages/core/core/schemas/contracts.py``
- ``packages/core/tests/test_contracts.py``

## Verification

cd packages/core && python -m pytest tests/test_contracts.py tests/ -v --tb=short 2>&1 | tail -20
