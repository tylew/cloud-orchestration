"""Dependency declaration endpoints — ARCHIVED.

The previous implementation generated clients.py and code snippets from
WorkflowDefinition refs. This has been replaced by the Service Contract model
(see docs/specs/service-contract.md).

The original implementation is preserved in archive/codegen/dependencies_handler.py.

This router is kept empty to avoid breaking the router registration in main.py.
"""

import logging
from fastapi import APIRouter

log = logging.getLogger(__name__)
router = APIRouter()
