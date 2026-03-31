"""Pipeline handler — build orchestration for compute nodes.

The code generation endpoint has been archived. AI agents will generate code
from Service Contracts instead (see docs/specs/service-contract.md).
The build-image endpoint is retained for container image building.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


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


@router.post("/build-image", response_model=BuildImageResponse)
async def build_image(req: BuildImageRequest):
    """Simulate building a container image for a compute node.

    In production, this would trigger Cloud Build or a local Docker build.
    """
    project_id = req.global_.get("project_id", "my-project")
    image_uri = f"gcr.io/{project_id}/{req.node_name}:latest"

    return BuildImageResponse(
        image_uri=image_uri,
        status="simulated",
        message=f"Image {image_uri} would be built via Cloud Build.",
    )
