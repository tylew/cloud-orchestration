"""FastAPI application — replaces the Express server."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from packages.api.middleware import LimitBodySizeMiddleware

from packages.api.handlers.health import router as health_router
from packages.api.handlers.blueprints import router as blueprints_router
from packages.api.handlers.terraform import router as terraform_router
from packages.api.handlers.pipeline import router as pipeline_router
from packages.api.handlers.gcp_check import router as gcp_check_router
from packages.api.handlers.projects import router as projects_router
from packages.api.handlers.admin import router as admin_router
from packages.api.handlers.provision import router as provision_router
from packages.api.handlers.code_files import router as code_files_router
from packages.api.handlers.builds import router as builds_router
from packages.api.handlers.secrets import router as secrets_router
from packages.api.handlers.deploy import router as deploy_router
from packages.api.handlers.dependencies import router as dependencies_router
from packages.api.handlers.ide import router as ide_router
from packages.api.handlers.nodes import router as nodes_router

app = FastAPI(title="GCP Orchestration MVP", version="0.1.0")

# ── Request body size limit ───────────────────────────────────
app.add_middleware(LimitBodySizeMiddleware)

# ── CORS — restrict to known origins ─────────────────────────
import os as _os

ALLOWED_ORIGINS = [
    "https://pl4m-host-dev.web.app",
    "https://pl4m-host-dev.firebaseapp.com",
]

if _os.environ.get("ENVIRONMENT", "").lower() in ("dev", "development", "local"):
    ALLOWED_ORIGINS += ["http://localhost:5173", "http://localhost:8080"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(blueprints_router, prefix="/api")
app.include_router(terraform_router, prefix="/api")
app.include_router(pipeline_router, prefix="/api")
app.include_router(gcp_check_router, prefix="/api")
app.include_router(projects_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(provision_router, prefix="/api")
app.include_router(code_files_router, prefix="/api")
app.include_router(builds_router, prefix="/api")
app.include_router(secrets_router, prefix="/api")
app.include_router(deploy_router, prefix="/api")
app.include_router(dependencies_router, prefix="/api", tags=["dependencies"])
app.include_router(ide_router, prefix="/api", tags=["ide"])
app.include_router(nodes_router, prefix="/api", tags=["nodes"])
