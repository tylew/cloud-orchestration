"""Core Demo — standalone web UI for testing the core infra package.

Run: cd packages/core && PYTHONPATH=. python -m demo.app
"""

import json
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from core.options import OPTIONS_REGISTRY
from core.registry import REGISTRY
from core.schemas.base import Envelope
from core.schemas.configs import TYPE_TO_CONFIG
from core.schemas.enums import NodeType, COMPUTE_TYPES
from core.validation import validate_blueprint
from core.terraform.generator import generate_terraform
from core.terraform.naming import resolve_gcp_name

log = logging.getLogger(__name__)

app = FastAPI(title="Core Demo", version="0.1.0")

STATIC_DIR = Path(__file__).parent / "static"


# ── API endpoints ────────────────────────────────────────────────────

@app.get("/api/options")
def get_options():
    """Return OPTIONS_REGISTRY as {node_type: {field_path: [{value, label}]}}."""
    result = {}
    for (node_type, field_path), opts in OPTIONS_REGISTRY.items():
        nt = node_type.value
        if nt not in result:
            result[nt] = {}
        result[nt][field_path] = [{"value": o["value"], "label": o["label"]} for o in opts]
    return result


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
            "gcp_name_template": defn.gcp_name_template,
            "config_schema": schema,
        }
    return result


@app.post("/api/validate")
def validate(payload: dict):
    """Validate a blueprint envelope. Returns issues list and enriched nodes."""
    try:
        envelope = Envelope.model_validate(payload)
    except ValidationError as e:
        return {"valid": False, "parse_errors": e.errors(), "issues": [], "nodes": []}
    issues = validate_blueprint(envelope)
    env = envelope.global_.environment or "dev"
    enriched_nodes = []
    for n in envelope.nodes:
        gcp_name = resolve_gcp_name(n, env)
        enriched_nodes.append({
            "name": n.name,
            "id": n.id,
            "resource_id": n.resource_id,
            "gcp_name": gcp_name,
        })
    return {
        "valid": len([i for i in issues if i.severity == "error"]) == 0,
        "issues": [
            {"severity": i.severity, "node": i.node, "message": i.message}
            for i in issues
        ],
        "nodes": enriched_nodes,
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


@app.post("/api/terraform/validate")
def terraform_validate(payload: dict):
    """Generate HCL and run terraform validate. Returns pass/fail with diagnostics."""
    import shutil
    import subprocess
    import tempfile

    if not shutil.which("terraform"):
        raise HTTPException(501, detail="terraform CLI not on PATH")

    try:
        envelope = Envelope.model_validate(payload)
    except ValidationError as e:
        raise HTTPException(422, detail=e.errors())

    files = generate_terraform(envelope)
    if not files:
        return {"valid": True, "diagnostics": "No Terraform files generated."}

    tmpdir = tempfile.mkdtemp(prefix="explorer-tf-")
    try:
        # Write provider + variables boilerplate
        (Path(tmpdir) / "provider.tf").write_text(
            'terraform {\n  required_providers {\n'
            '    google = { source = "hashicorp/google"; version = ">= 6.0" }\n'
            '    google-beta = { source = "hashicorp/google-beta"; version = ">= 6.0" }\n'
            '  }\n}\n'
        )
        (Path(tmpdir) / "variables.tf").write_text(
            'variable "gcp_project_id" { default = "test-project" }\n'
            'variable "gcp_region" { default = "us-central1" }\n'
            'variable "environment" { default = "dev" }\n'
        )
        for name, content in files.items():
            (Path(tmpdir) / name).write_text(content)

        # terraform init
        init = subprocess.run(
            ["terraform", "init", "-backend=false", "-no-color"],
            cwd=tmpdir, capture_output=True, text=True, timeout=60,
        )
        if init.returncode != 0:
            return {"valid": False, "diagnostics": f"terraform init failed:\n{init.stderr}"}

        # terraform validate
        val = subprocess.run(
            ["terraform", "validate", "-no-color"],
            cwd=tmpdir, capture_output=True, text=True, timeout=30,
        )
        if val.returncode == 0:
            return {"valid": True, "diagnostics": val.stdout.strip()}
        else:
            return {"valid": False, "diagnostics": val.stderr.strip() or val.stdout.strip()}
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)



# ── Static files ─────────────────────────────────────────────────────

@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)
