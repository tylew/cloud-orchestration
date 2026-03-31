"""Pipeline handler — code generation and build orchestration for compute nodes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from packages.core.codegen.code_generator import generate_compute_code, GeneratedCode

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


# ── Request / Response models ────────────────────────────────────────

class CodeGenRequest(BaseModel):
    """Request to generate code for a single compute node."""
    model_config = ConfigDict(populate_by_name=True)

    node: dict
    all_nodes: list[dict] = []
    global_: dict = {}

    def __init__(self, **data):
        if "global" in data and "global_" not in data:
            data["global_"] = data.pop("global")
        super().__init__(**data)


class CodeGenResponse(BaseModel):
    files: dict[str, str]
    image_uri: str
    summary: str


class BuildImageRequest(BaseModel):
    """Request to build a container image for a compute node."""
    model_config = ConfigDict(populate_by_name=True)

    node_name: str
    node_type: str
    global_: dict = {}

    def __init__(self, **data):
        if "global" in data and "global_" not in data:
            data["global_"] = data.pop("global")
        super().__init__(**data)


class BuildImageResponse(BaseModel):
    image_uri: str
    status: str
    message: str


# ── Endpoints ────────────────────────────────────────────────────────

@router.post("/generate-code", response_model=CodeGenResponse)
async def generate_code(req: CodeGenRequest):
    """Generate application code for a compute node based on its internal graph.

    Takes a node definition with internalGraph steps and produces:
    - Application source code with GCP client libraries
    - Dockerfile for containerization
    - Dependency manifest (requirements.txt or package.json)
    """
    node = req.node
    node_type = node.get("type", "")

    if node_type not in ("cloud_run", "cloud_run_job", "cloud_function"):
        raise HTTPException(
            status_code=400,
            detail=f"Code generation only applies to compute nodes, got: {node_type}",
        )

    steps = (node.get("internalGraph") or {}).get("steps", [])
    if not steps:
        raise HTTPException(
            status_code=400,
            detail=f"Node '{node.get('name', '?')}' has no internal graph steps",
        )

    result: GeneratedCode = generate_compute_code(
        node=node,
        all_nodes=req.all_nodes,
        global_config=req.global_,
    )

    return CodeGenResponse(
        files=result.files,
        image_uri=result.image_uri,
        summary=result.summary,
    )


@router.post("/build-image", response_model=BuildImageResponse)
async def build_image(req: BuildImageRequest):
    """Simulate building a container image for a compute node.

    In production, this would trigger Cloud Build or a local Docker build.
    For the MVP, returns the target image URI and a simulated success.
    """
    project_id = req.global_.get("project_id", "my-project")
    image_uri = f"gcr.io/{project_id}/{req.node_name}:latest"

    return BuildImageResponse(
        image_uri=image_uri,
        status="simulated",
        message=f"Image {image_uri} would be built via Cloud Build. "
                f"In production, this triggers: gcloud builds submit --tag {image_uri}",
    )
