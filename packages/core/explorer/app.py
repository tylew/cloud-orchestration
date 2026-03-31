"""Core Explorer — standalone web UI for testing the core infra package.

Run: cd packages/core && PYTHONPATH=. python -m explorer.app
"""

import json
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from core.registry import REGISTRY
from core.schemas.base import Envelope
from core.schemas.configs import TYPE_TO_CONFIG
from core.schemas.enums import NodeType, COMPUTE_TYPES
from core.validation import validate_blueprint
from core.terraform.generator import generate_terraform
from core.dag import BlueprintDAG

log = logging.getLogger(__name__)

app = FastAPI(title="Core Explorer", version="0.1.0")

STATIC_DIR = Path(__file__).parent / "static"


# ── API endpoints ────────────────────────────────────────────────────

@app.get("/api/types")
def get_types():
    """Return all resource types with metadata and config JSON schemas."""
    result = {}
    for node_type, defn in REGISTRY.items():
        config_cls = TYPE_TO_CONFIG.get(node_type)
        schema = config_cls.model_json_schema() if config_cls else {}
        result[node_type.value] = {
            "label": defn.label,
            "category": defn.category,
            "is_compute": defn.is_compute,
            "terraform_resource": defn.terraform_resource,
            "config_schema": schema,
        }
    return result


@app.post("/api/validate")
def validate(payload: dict):
    """Validate a blueprint envelope. Returns issues list."""
    try:
        envelope = Envelope.model_validate(payload)
    except ValidationError as e:
        return {"valid": False, "parse_errors": e.errors(), "issues": []}
    issues = validate_blueprint(envelope)
    return {
        "valid": len([i for i in issues if i.severity == "error"]) == 0,
        "issues": [
            {"severity": i.severity, "node": i.node, "message": i.message}
            for i in issues
        ],
    }


@app.post("/api/terraform")
def terraform(payload: dict):
    """Generate Terraform HCL from a blueprint envelope."""
    try:
        envelope = Envelope.model_validate(payload)
    except ValidationError as e:
        raise HTTPException(422, detail=e.errors())
    files = generate_terraform(envelope)
    return {"files": files}


@app.post("/api/dag")
def dag(payload: dict):
    """Return DAG nodes and edges for visualization."""
    try:
        envelope = Envelope.model_validate(payload)
    except ValidationError as e:
        raise HTTPException(422, detail=e.errors())
    dag = BlueprintDAG(envelope)

    nodes = []
    for n in envelope.nodes:
        defn = REGISTRY.get(n.type)
        nodes.append({
            "name": n.name,
            "type": n.type.value,
            "label": defn.label if defn else n.type.value,
            "category": defn.category if defn else "Unknown",
            "is_compute": defn.is_compute if defn else False,
        })

    edges = []
    for n in envelope.nodes:
        for dep in n.depends_on:
            edges.append({"from": dep, "to": n.name})

    # Get parallel batches for layout hints
    try:
        batches = dag.parallel_batches()
        batch_list = [list(b) for b in batches]
    except Exception:
        batch_list = []

    return {"nodes": nodes, "edges": edges, "batches": batch_list}


# ── Static files ─────────────────────────────────────────────────────

@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)
