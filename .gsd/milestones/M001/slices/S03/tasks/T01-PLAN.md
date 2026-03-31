---
estimated_steps: 14
estimated_files: 2
skills_used: []
---

# T01: Build core explorer — API + single-page UI

Build a FastAPI app at packages/core/explorer/ that serves:
1. GET /api/types — all resource types from REGISTRY with config JSON schemas
2. POST /api/validate — validate an envelope, return issues
3. POST /api/terraform — generate HCL from envelope
4. POST /api/dag — return nodes + edges for DAG visualization
5. GET / — serves the single-page HTML UI

The UI (single index.html with inline JS/CSS) provides:
- Resource palette showing all 20 types by category
- Blueprint builder: click to add resources, fill config forms from JSON schema
- depends_on editor: select dependencies from existing resources
- Live validation panel showing errors/warnings
- Terraform preview panel showing generated HCL per file
- DAG visualization using a simple canvas/SVG layout

Use only: fastapi, uvicorn, core package. No npm, no build step.

## Inputs

- `core.registry.REGISTRY`
- `core.schemas.configs TYPE_TO_CONFIG`
- `core.validation.validate_blueprint`
- `core.terraform.generator.generate_terraform`
- `core.dag.BlueprintDAG`

## Expected Output

- `packages/core/explorer/__init__.py`
- `packages/core/explorer/app.py`
- `packages/core/explorer/static/index.html`

## Verification

cd packages/core && PYTHONPATH=. python -m explorer.app & sleep 2 && curl -s http://localhost:8100/api/types | python -m json.tool | head -5 && kill %1
