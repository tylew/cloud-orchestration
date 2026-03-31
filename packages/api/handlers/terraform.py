"""Terraform generation handlers."""
import logging

from dataclasses import asdict

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from packages.core.schemas.base import Envelope
from packages.core.terraform.generator import generate_terraform, preview_resources

log = logging.getLogger(__name__)
router = APIRouter()


@router.post("/terraform/generate")
async def generate_terraform_endpoint(payload: dict):
    try:
        envelope = Envelope.model_validate(payload)
    except ValidationError as e:
        log.warning("terraform/generate validation failed: %s", [err.get('loc', []) for err in e.errors()])
        raise HTTPException(status_code=422, detail=[{**err, 'ctx': {k: str(v) for k, v in err.get('ctx', {}).items()}} for err in e.errors()])

    files = generate_terraform(envelope)
    return {"files": files}


@router.post("/terraform/preview")
async def preview_terraform_endpoint(payload: dict):
    try:
        envelope = Envelope.model_validate(payload)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=[{**err, 'ctx': {k: str(v) for k, v in err.get('ctx', {}).items()}} for err in e.errors()])

    resources = preview_resources(envelope)
    return {"resources": resources}
