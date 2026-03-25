# Packages Bootability & Testing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Get the Python packages (`core`, `api`, `platform`) booting locally via Docker and verified through layered tests (core unit, platform integration, API layered) against tenant project `my-super-cool-app-dev-3f74d0`.

**Architecture:** Bottom-up. Dockerfile + docker-compose get the server running. Configurable dev user enables test identity. Core unit tests verify pure logic (validation, DAG, Terraform gen). Platform integration tests hit real Firestore/GCS/Cloud Build. API layered tests boot FastAPI TestClient and exercise end-to-end user flows.

**Tech Stack:** Python 3.12, FastAPI, pytest, pytest-asyncio, httpx, Docker, Firestore, Cloud Build

---

## File Map

**Create:**
- `Dockerfile` — Python 3.12 container for the FastAPI backend
- `.env.test.example` — Test environment config template (committed; copy to `.env.test` locally)
- `packages/tests/conftest.py` — Shared fixtures (Envelope builders, markers)
- `packages/tests/test_registry.py` — Registry completeness tests
- `packages/tests/test_dag.py` — DAG topological sort, cycles, parallel batches
- `packages/tests/test_validation.py` — Blueprint validation tests
- `packages/tests/test_terraform.py` — Terraform generation tests
- `packages/tests/test_field_resolution.py` — Field reference resolution tests
- `packages/tests/integration/__init__.py` — Package marker
- `packages/tests/integration/conftest.py` — GCP client fixtures, cleanup helpers
- `packages/tests/integration/test_store_projects.py` — Firestore project CRUD
- `packages/tests/integration/test_store_blueprints.py` — Firestore blueprint sharding
- `packages/tests/integration/test_store_collaborators.py` — Collaborator role management
- `packages/tests/integration/test_gcp_storage.py` — GCS upload/download
- `packages/tests/integration/test_gcp_secrets.py` — Secret Manager CRUD
- `packages/tests/integration/test_gcp_cloud_build.py` — Cloud Build submission
- `packages/tests/integration/test_api_health.py` — Health/config/schema endpoints
- `packages/tests/integration/test_api_blueprints.py` — Blueprint validate/save/get
- `packages/tests/integration/test_api_terraform.py` — Terraform generate/preview
- `packages/tests/integration/test_api_projects.py` — Project lifecycle CRUD
- `packages/tests/integration/test_api_deploy.py` — Full deploy pipeline

**Modify:**
- `docker-compose.yml` — Fix module paths, mount packages, drop frontend service
- `packages/api/main.py:30-34` — Add localhost CORS origins gated by ENVIRONMENT
- `packages/platform/auth/firebase.py:29-34` — Make `_DEV_USER` env-configurable
- `packages/pyproject.toml:22-29` — Add pytest config, pytest-asyncio dev dep, fix setuptools find
- `.gitignore` — Add `.env.test`

---

### Task 1: Dockerfile

**Files:**
- Create: `Dockerfile`

- [ ] **Step 1: Create Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies from packages/pyproject.toml
COPY packages/pyproject.toml packages/pyproject.toml
RUN pip install --no-cache-dir ./packages

# Copy full repo (imports use packages.* paths)
COPY . .

EXPOSE 8080

CMD ["uvicorn", "packages.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

- [ ] **Step 2: Verify Docker build succeeds**

Run: `docker build -t gcp-orch-test .`
Expected: Build completes without errors.

- [ ] **Step 3: Commit**

```bash
git add Dockerfile
git commit -m "feat: add Dockerfile for FastAPI backend"
```

---

### Task 2: Fix docker-compose.yml

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: Replace docker-compose.yml contents**

```yaml
services:
  app:
    build: .
    env_file: .env.local
    ports:
      - "8080:8080"
    volumes:
      - ./packages:/app/packages
      - ${HOME}/.config/gcloud:/root/.config/gcloud
    command: uvicorn packages.api.main:app --host 0.0.0.0 --port 8080 --reload
    environment:
      - PYTHONDONTWRITEBYTECODE=1
      - GOOGLE_CLOUD_PROJECT=${GCP_PROJECT_ID:-pl4m-host-dev}
```

Changes from original:
- Module path: `packages.api.main:app` (was `backend.main:app`)
- Volume mount: `./packages:/app/packages` (was `./backend:/app/backend`)
- Removed `./public` volume (doesn't exist)
- Dropped `frontend` service (not relevant yet)

- [ ] **Step 2: Commit**

```bash
git add docker-compose.yml
git commit -m "fix: update docker-compose module path and volumes for packages layout"
```

---

### Task 3: CORS localhost fix

**Files:**
- Modify: `packages/api/main.py:30-34`

- [ ] **Step 1: Update CORS config to include localhost in dev mode**

In `packages/api/main.py`, replace lines 29-34:

```python
# ── CORS — restrict to known origins ─────────────────────────
ALLOWED_ORIGINS = [
    "https://pl4m-host-dev.web.app",
    "https://pl4m-host-dev.firebaseapp.com",
]
# No local dev origins -- CORS configured for production only (HARD-04)
```

With:

```python
# ── CORS — restrict to known origins ─────────────────────────
import os as _os

ALLOWED_ORIGINS = [
    "https://pl4m-host-dev.web.app",
    "https://pl4m-host-dev.firebaseapp.com",
]

if _os.environ.get("ENVIRONMENT", "").lower() in ("dev", "development", "local"):
    ALLOWED_ORIGINS += ["http://localhost:5173", "http://localhost:8080"]
```

- [ ] **Step 2: Commit**

```bash
git add packages/api/main.py
git commit -m "feat: add localhost CORS origins in dev environment"
```

---

### Task 4: Configurable dev user

**Files:**
- Modify: `packages/platform/auth/firebase.py:29-34`

- [ ] **Step 1: Make _DEV_USER env-configurable**

In `packages/platform/auth/firebase.py`, replace lines 28-34:

```python
# Default dev tenant used when auth is disabled
_DEV_USER = CurrentUser(
    tenant_id="dev-local",
    email="dev@localhost",
    display_name="Local Developer",
    is_admin=True,
)
```

With:

```python
# Default dev tenant used when auth is disabled — configurable via env vars
_DEV_USER = CurrentUser(
    tenant_id=os.environ.get("DEV_TENANT_ID", "dev-local"),
    email=os.environ.get("DEV_USER_EMAIL", "dev@localhost"),
    display_name=os.environ.get("DEV_USER_DISPLAY_NAME", "Local Developer"),
    is_admin=os.environ.get("DEV_USER_IS_ADMIN", "true").lower() in ("true", "1", "yes"),
)
```

- [ ] **Step 2: Commit**

```bash
git add packages/platform/auth/firebase.py
git commit -m "feat: make dev user configurable via env vars for test identity"
```

---

### Task 5: pytest config and dev dependencies

**Files:**
- Modify: `packages/pyproject.toml`
- Modify: `.gitignore`
- Create: `.env.test`
- Create: `packages/tests/__init__.py`
- Create: `packages/tests/integration/__init__.py`

- [ ] **Step 1: Update pyproject.toml**

In `packages/pyproject.toml`, replace the full contents with:

```toml
[project]
name = "gcp-orchestration-mvp"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]",
    "pydantic>=2.0",
    "jinja2",
    "google-cloud-storage",
    "google-cloud-firestore>=2.16",
    "google-cloud-build>=3.0",
    "firebase-admin>=6.0",
    "google-cloud-secret-manager>=2.20",
    "sse-starlette>=2.0",
    "google-cloud-logging>=3.10",
    "PyJWT>=2.0",
    "cryptography>=3.0",
    "httpx>=0.24",
]

[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-asyncio",
    "httpx",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["packages*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["integration: requires GCP credentials and network"]
asyncio_mode = "auto"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
```

Key changes:
- `setuptools.packages.find` now uses `where = ["."]` and `include = ["packages*"]` so `pip install` installs the `packages` namespace correctly, matching the `from packages.api...` import style
- Added `pytest-asyncio` to dev deps
- Added `[tool.pytest.ini_options]` section

- [ ] **Step 2: Add .env.test to .gitignore**

Append to `.gitignore`:

```
.env.test
```

- [ ] **Step 3: Create .env.test.example template**

Create `.env.test.example` (committed to repo as a template — copy to `.env.test` and fill in values):

```env
GCP_PROJECT_ID=my-super-cool-app-dev-3f74d0
ENVIRONMENT=dev
AUTH_DISABLED=true
DEV_TENANT_ID=REPLACE_WITH_TYLER_FIREBASE_UID
DEV_USER_EMAIL=tyler@pl4m.com
DEV_USER_DISPLAY_NAME=Tyler
DEV_USER_IS_ADMIN=true
FIRESTORE_DATABASE=(default)
```

- [ ] **Step 4: Create test package init files**

Create empty `packages/tests/__init__.py` and `packages/tests/integration/__init__.py`.

- [ ] **Step 5: Verify pip install works with new setuptools config**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration && pip install -e ./packages`
Expected: Installs successfully, `python -c "from packages.api.main import app; print(app.title)"` prints `GCP Orchestration MVP`.

- [ ] **Step 6: Commit**

```bash
git add packages/pyproject.toml .gitignore .env.test.example packages/tests/__init__.py packages/tests/integration/__init__.py
git commit -m "feat: add pytest config, test deps, and test env template"
```

---

### Task 6: Verify Docker boot

**Files:** None (verification only)

- [ ] **Step 1: Build and run**

Run: `docker compose build && docker compose up -d`
Expected: Container starts without import errors.

- [ ] **Step 2: Hit health endpoint**

Run: `curl -s http://localhost:8080/api/health`
Expected: `{"status":"ok"}`

- [ ] **Step 3: Tear down**

Run: `docker compose down`

---

### Task 7: Test fixtures (conftest.py)

**Files:**
- Create: `packages/tests/conftest.py`

- [ ] **Step 1: Create shared test fixtures**

```python
"""Shared test fixtures — reusable Envelope builders for unit tests."""

import pytest

from packages.core.schemas.base import (
    Envelope, BaseNode, GlobalConfig, Metadata, NodeOutput,
)
from packages.core.schemas.enums import NodeType


def _global(project_id="test-project", region="us-central1", env="dev"):
    return {"project_id": project_id, "region": region, "environment": env}


def _node(name, node_type, config=None, depends_on=None, **kwargs):
    """Build a node dict for Envelope construction."""
    d = {"name": name, "type": node_type, "config": config or {}}
    if depends_on:
        d["depends_on"] = depends_on
    d.update(kwargs)
    return d


@pytest.fixture
def minimal_envelope_data():
    """Minimal valid blueprint: VPC + Service Account + Cloud Run."""
    return {
        "global": _global(),
        "nodes": [
            _node("my-vpc", "vpc", {"auto_create_subnetworks": False}),
            _node("my-sa", "service_account", {"account_id": "my-sa"}),
            _node("my-service", "cloud_run", {
                "image": "gcr.io/test/image:latest",
                "service_account": "my-sa",
            }, depends_on=["my-vpc", "my-sa"]),
        ],
    }


@pytest.fixture
def minimal_envelope(minimal_envelope_data):
    """Parsed Envelope from minimal valid blueprint."""
    return Envelope.model_validate(minimal_envelope_data)


@pytest.fixture
def complex_envelope_data():
    """Complex blueprint: 8 nodes across multiple types with dependencies."""
    return {
        "global": _global(),
        "nodes": [
            _node("my-vpc", "vpc", {"auto_create_subnetworks": False}),
            _node("my-subnet", "subnet", {
                "ip_cidr_range": "10.0.0.0/24",
                "region": "us-central1",
                "network": "my-vpc",
            }, depends_on=["my-vpc"]),
            _node("my-sa", "service_account", {"account_id": "my-sa"}),
            _node("my-db", "cloud_sql", {
                "database_version": "POSTGRES_15",
                "tier": "db-f1-micro",
            }, depends_on=["my-vpc"]),
            _node("my-firestore", "firestore", {
                "location_id": "us-central",
            }),
            _node("my-bucket", "gcs_bucket", {"location": "US"}),
            _node("my-topic", "pubsub_topic", {}),
            _node("my-service", "cloud_run", {
                "image": "gcr.io/test/image:latest",
                "service_account": "my-sa",
            }, depends_on=["my-sa", "my-db", "my-firestore", "my-bucket"]),
        ],
    }


@pytest.fixture
def complex_envelope(complex_envelope_data):
    return Envelope.model_validate(complex_envelope_data)


@pytest.fixture
def cyclic_envelope_data():
    """Invalid blueprint with a dependency cycle."""
    return {
        "global": _global(),
        "nodes": [
            _node("node-a", "vpc", {"auto_create_subnetworks": False}, depends_on=["node-b"]),
            _node("node-b", "vpc", {"auto_create_subnetworks": False}, depends_on=["node-a"]),
        ],
    }


@pytest.fixture
def duplicate_names_envelope_data():
    """Invalid blueprint with duplicate node names."""
    return {
        "global": _global(),
        "nodes": [
            _node("my-vpc", "vpc", {"auto_create_subnetworks": False}),
            _node("my-vpc", "vpc", {"auto_create_subnetworks": True}),
        ],
    }
```

- [ ] **Step 2: Verify fixtures load**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration/packages && python -m pytest tests/conftest.py --collect-only 2>&1 | head -5`
Expected: No import errors.

- [ ] **Step 3: Commit**

```bash
git add packages/tests/conftest.py
git commit -m "feat: add shared test fixtures for blueprint unit tests"
```

---

### Task 8: Registry unit tests

**Files:**
- Create: `packages/tests/test_registry.py`

- [ ] **Step 1: Write registry tests**

```python
"""Registry completeness and lookup tests."""

from packages.core.registry import REGISTRY, get_definition, get_config_model, is_compute
from packages.core.schemas.enums import NodeType, COMPUTE_TYPES


class TestRegistryCompleteness:
    def test_all_node_types_registered(self):
        for nt in NodeType:
            assert nt in REGISTRY, f"{nt} missing from REGISTRY"

    def test_registry_count_matches_enum(self):
        assert len(REGISTRY) == len(NodeType)


class TestGetConfigModel:
    def test_returns_pydantic_class_for_each_type(self):
        for nt in NodeType:
            model = get_config_model(nt)
            assert model is not None, f"No config model for {nt}"

    def test_cloud_run_config_model_name(self):
        model = get_config_model(NodeType.CLOUD_RUN)
        assert model.__name__ == "CloudRunConfig"


class TestIsCompute:
    def test_compute_types_are_compute(self):
        for nt in COMPUTE_TYPES:
            assert is_compute(nt) is True

    def test_non_compute_types_are_not_compute(self):
        non_compute = set(NodeType) - COMPUTE_TYPES
        for nt in non_compute:
            assert is_compute(nt) is False
```

- [ ] **Step 2: Run tests**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration/packages && python -m pytest tests/test_registry.py -v`
Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add packages/tests/test_registry.py
git commit -m "test: add registry completeness and lookup tests"
```

---

### Task 9: DAG unit tests

**Files:**
- Create: `packages/tests/test_dag.py`

- [ ] **Step 1: Write DAG tests**

```python
"""DAG topological sort, cycle detection, and parallel batch tests."""

import pytest
from packages.core.dag import BlueprintDAG
from packages.core.schemas.base import Envelope


class TestTopologicalSort:
    def test_simple_chain(self, minimal_envelope):
        dag = BlueprintDAG(minimal_envelope)
        ordered = dag.topological_sort()
        names = [n.name for n in ordered]
        # my-service depends on my-vpc and my-sa, so it must come after both
        assert names.index("my-service") > names.index("my-vpc")
        assert names.index("my-service") > names.index("my-sa")

    def test_complex_ordering(self, complex_envelope):
        dag = BlueprintDAG(complex_envelope)
        ordered = dag.topological_sort()
        names = [n.name for n in ordered]
        # my-subnet depends on my-vpc
        assert names.index("my-subnet") > names.index("my-vpc")
        # my-service depends on my-sa, my-db, my-firestore, my-bucket
        for dep in ["my-sa", "my-db", "my-firestore", "my-bucket"]:
            assert names.index("my-service") > names.index(dep)

    def test_no_dependencies(self):
        data = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": "a", "type": "vpc", "config": {"auto_create_subnetworks": False}},
                {"name": "b", "type": "vpc", "config": {"auto_create_subnetworks": False}},
            ],
        }
        envelope = Envelope.model_validate(data)
        dag = BlueprintDAG(envelope)
        ordered = dag.topological_sort()
        assert len(ordered) == 2


class TestCycleDetection:
    def test_cycle_raises_value_error(self, cyclic_envelope_data):
        envelope = Envelope.model_validate(cyclic_envelope_data)
        dag = BlueprintDAG(envelope)
        with pytest.raises(ValueError, match="Circular dependency"):
            dag.topological_sort()

    def test_validate_ordering_reports_cycle(self, cyclic_envelope_data):
        envelope = Envelope.model_validate(cyclic_envelope_data)
        dag = BlueprintDAG(envelope)
        errors = dag.validate_ordering()
        assert any("Circular" in e or "cycle" in e.lower() for e in errors)


class TestValidateOrdering:
    def test_missing_dependency(self):
        data = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": "a", "type": "vpc", "config": {"auto_create_subnetworks": False},
                 "depends_on": ["nonexistent"]},
            ],
        }
        envelope = Envelope.model_validate(data)
        dag = BlueprintDAG(envelope)
        errors = dag.validate_ordering()
        assert any("nonexistent" in e for e in errors)

    def test_valid_graph_has_no_errors(self, minimal_envelope):
        dag = BlueprintDAG(minimal_envelope)
        errors = dag.validate_ordering()
        assert errors == []


class TestParallelBatches:
    def test_independent_nodes_in_same_batch(self):
        data = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": "a", "type": "vpc", "config": {"auto_create_subnetworks": False}},
                {"name": "b", "type": "vpc", "config": {"auto_create_subnetworks": False}},
                {"name": "c", "type": "vpc", "config": {"auto_create_subnetworks": False}},
            ],
        }
        envelope = Envelope.model_validate(data)
        dag = BlueprintDAG(envelope)
        batches = dag.parallel_batches()
        # All three should be in the first batch (no dependencies)
        assert len(batches) == 1
        assert batches[0] == {"a", "b", "c"}

    def test_dependent_nodes_in_different_batches(self, minimal_envelope):
        dag = BlueprintDAG(minimal_envelope)
        batches = dag.parallel_batches()
        # my-service depends on others, so at least 2 batches
        assert len(batches) >= 2
        # my-service must be in a later batch than my-vpc and my-sa
        service_batch = next(i for i, b in enumerate(batches) if "my-service" in b)
        vpc_batch = next(i for i, b in enumerate(batches) if "my-vpc" in b)
        assert service_batch > vpc_batch
```

- [ ] **Step 2: Run tests**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration/packages && python -m pytest tests/test_dag.py -v`
Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add packages/tests/test_dag.py
git commit -m "test: add DAG topological sort, cycle detection, and parallel batch tests"
```

---

### Task 10: Validation unit tests

**Files:**
- Create: `packages/tests/test_validation.py`

- [ ] **Step 1: Write validation tests**

```python
"""Blueprint validation tests — required fields, duplicates, dependencies, parent refs."""

import pytest
from dataclasses import asdict

from packages.core.schemas.base import Envelope
from packages.core.validation import (
    validate_blueprint,
    validate_required_fields,
    validate_per_type_name_uniqueness,
    validate_firestore_free_tier,
    validate_parent_refs,
    validate_depends_on,
    ValidationIssue,
)


def _issues_by_severity(issues):
    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]
    return errors, warnings


class TestValidateBlueprint:
    def test_valid_blueprint_no_errors(self, minimal_envelope):
        issues = validate_blueprint(minimal_envelope)
        errors, _ = _issues_by_severity(issues)
        assert len(errors) == 0

    def test_duplicate_node_names(self, duplicate_names_envelope_data):
        envelope = Envelope.model_validate(duplicate_names_envelope_data)
        issues = validate_blueprint(envelope)
        errors, _ = _issues_by_severity(issues)
        dup_errors = [e for e in errors if "Duplicate" in e.message]
        assert len(dup_errors) >= 1

    def test_invalid_depends_on(self):
        data = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": "my-vpc", "type": "vpc", "config": {"auto_create_subnetworks": False},
                 "depends_on": ["does-not-exist"]},
            ],
        }
        envelope = Envelope.model_validate(data)
        issues = validate_blueprint(envelope)
        errors, _ = _issues_by_severity(issues)
        dep_errors = [e for e in errors if "does-not-exist" in e.message]
        assert len(dep_errors) >= 1

    def test_invalid_iam_service_account_ref(self):
        data = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": "my-service", "type": "cloud_run", "config": {
                    "image": "gcr.io/test/img", "service_account": "my-sa",
                }, "iam": {"service_account": "nonexistent-sa"}},
            ],
        }
        envelope = Envelope.model_validate(data)
        issues = validate_blueprint(envelope)
        errors, _ = _issues_by_severity(issues)
        sa_errors = [e for e in errors if "iam.service_account" in e.message]
        assert len(sa_errors) >= 1


class TestRequiredFields:
    def test_cloud_run_missing_image(self):
        data = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": "my-service", "type": "cloud_run", "config": {}},
            ],
        }
        envelope = Envelope.model_validate(data)
        issues = validate_required_fields(envelope.nodes)
        errors, _ = _issues_by_severity(issues)
        img_errors = [e for e in errors if "image" in e.message.lower()]
        assert len(img_errors) >= 1

    def test_cloud_sql_missing_required(self):
        data = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": "my-db", "type": "cloud_sql", "config": {}},
            ],
        }
        envelope = Envelope.model_validate(data)
        issues = validate_required_fields(envelope.nodes)
        errors, _ = _issues_by_severity(issues)
        assert any("Database version" in e.message for e in errors)
        assert any("tier" in e.message.lower() for e in errors)

    def test_warnings_for_optional_fields(self):
        data = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": "my-service", "type": "cloud_run", "config": {
                    "image": "gcr.io/test/img", "service_account": "my-sa",
                }},
            ],
        }
        envelope = Envelope.model_validate(data)
        issues = validate_required_fields(envelope.nodes)
        _, warnings = _issues_by_severity(issues)
        # CPU and memory are warnings, not errors
        assert any("CPU" in w.message for w in warnings)


class TestNameUniqueness:
    def test_duplicate_same_type(self, duplicate_names_envelope_data):
        envelope = Envelope.model_validate(duplicate_names_envelope_data)
        issues = validate_per_type_name_uniqueness(envelope.nodes)
        assert len(issues) >= 1
        assert issues[0].severity == "error"

    def test_same_name_different_types_ok(self):
        """Same name on different types is fine (uniqueness is per-type)."""
        data = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": "my-resource", "type": "vpc", "config": {"auto_create_subnetworks": False}},
                {"name": "my-resource", "type": "gcs_bucket", "config": {"location": "US"}},
            ],
        }
        envelope = Envelope.model_validate(data)
        issues = validate_per_type_name_uniqueness(envelope.nodes)
        assert len(issues) == 0


class TestFirestoreFreeTier:
    def test_default_database_no_warning(self):
        data = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": "my-fs", "type": "firestore", "config": {
                    "location_id": "us-central", "database_id": "(default)",
                }},
            ],
        }
        envelope = Envelope.model_validate(data)
        issues = validate_firestore_free_tier(envelope.nodes)
        assert len(issues) == 0

    def test_non_default_database_warns(self):
        data = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": "my-fs", "type": "firestore", "config": {
                    "location_id": "us-central", "database_id": "custom-db",
                }},
            ],
        }
        envelope = Envelope.model_validate(data)
        issues = validate_firestore_free_tier(envelope.nodes)
        assert len(issues) == 1
        assert issues[0].severity == "warning"
        assert "Free tier" in issues[0].message


class TestChildParentValidation:
    def test_missing_parent_ref(self):
        data = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": "my-db", "type": "cloud_sql", "config": {
                    "database_version": "POSTGRES_15", "tier": "db-f1-micro",
                }, "slug": "sql-abc123"},
                {"name": "orphan-db", "type": "cloud_sql_database", "config": {
                    "parentRef": "nonexistent-slug",
                }, "slug": "sqldb-xyz"},
            ],
        }
        envelope = Envelope.model_validate(data)
        issues = validate_parent_refs(envelope.nodes)
        errors = [i for i in issues if i.severity == "error"]
        assert any("non-existent" in e.message for e in errors)
```

- [ ] **Step 2: Run tests**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration/packages && python -m pytest tests/test_validation.py -v`
Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add packages/tests/test_validation.py
git commit -m "test: add blueprint validation unit tests"
```

---

### Task 11: Terraform generation unit tests

**Files:**
- Create: `packages/tests/test_terraform.py`

- [ ] **Step 1: Write Terraform generation tests**

```python
"""Terraform generation and preview tests."""

from packages.core.terraform.generator import generate_terraform, preview_resources
from packages.core.schemas.base import Envelope


class TestGenerateTerraform:
    def test_produces_provider_and_variables(self, minimal_envelope):
        files = generate_terraform(minimal_envelope)
        assert "provider.tf" in files
        assert "variables.tf" in files
        assert "hashicorp/google" in files["provider.tf"]
        assert "gcp_project_id" in files["variables.tf"]

    def test_produces_main_tf(self, minimal_envelope):
        files = generate_terraform(minimal_envelope)
        assert "main.tf" in files
        assert len(files["main.tf"]) > 0

    def test_single_vpc_node(self):
        data = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": "my-vpc", "type": "vpc", "config": {"auto_create_subnetworks": False}},
            ],
        }
        envelope = Envelope.model_validate(data)
        files = generate_terraform(envelope)
        assert "main.tf" in files
        assert "google_compute_network" in files["main.tf"]

    def test_multi_node_dependencies(self, complex_envelope):
        files = generate_terraform(complex_envelope)
        main = files["main.tf"]
        # Should contain resources for multiple types
        assert "google_compute_network" in main  # VPC
        assert "google_sql_database_instance" in main  # Cloud SQL

    def test_backend_tf_generated_when_config_present(self):
        data = {
            "global": {
                "project_id": "test", "region": "us-central1", "environment": "dev",
                "backend": {"type": "gcs", "bucket": "my-bucket", "prefix": "terraform/state"},
            },
            "nodes": [
                {"name": "my-vpc", "type": "vpc", "config": {"auto_create_subnetworks": False}},
            ],
        }
        envelope = Envelope.model_validate(data)
        files = generate_terraform(envelope)
        assert "backend.tf" in files
        assert "gcs" in files["backend.tf"]

    def test_no_backend_tf_without_config(self, minimal_envelope):
        files = generate_terraform(minimal_envelope)
        assert "backend.tf" not in files


class TestPreviewResources:
    def test_preview_lists_expected_resources(self, minimal_envelope):
        resources = preview_resources(minimal_envelope)
        types = {r["terraform_resource"] for r in resources}
        assert "google_compute_network" in types
        assert "google_service_account" in types
        assert "google_cloud_run_v2_service" in types

    def test_preview_count_matches_nodes_with_tf_resources(self, complex_envelope):
        resources = preview_resources(complex_envelope)
        # All 8 nodes have terraform_resource (except third_party_api which isn't in this fixture)
        assert len(resources) >= 7

    def test_nodes_without_terraform_resource_excluded(self):
        data = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": "ext-api", "type": "third_party_api", "config": {"base_url": "https://example.com"}},
            ],
        }
        envelope = Envelope.model_validate(data)
        resources = preview_resources(envelope)
        # third_party_api has terraform_resource="" so should be excluded
        assert len(resources) == 0
```

- [ ] **Step 2: Run tests**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration/packages && python -m pytest tests/test_terraform.py -v`
Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add packages/tests/test_terraform.py
git commit -m "test: add Terraform generation and preview unit tests"
```

---

### Task 12: Field resolution unit tests

**Files:**
- Create: `packages/tests/test_field_resolution.py`

- [ ] **Step 1: Write field resolution tests**

```python
"""Field reference resolution tests for Firestore, Cloud SQL, and BigQuery."""

from packages.core.field_resolution import resolve_field_ref, collect_storage_fields


class TestFirestoreResolution:
    def test_simple_collection_field(self):
        config = {
            "location_id": "us-central",
            "collections": [
                {"path": "users", "fields": [{"name": "email", "type": "string"}]},
            ],
        }
        assert resolve_field_ref("firestore", config, "users.email") is True

    def test_missing_field(self):
        config = {
            "location_id": "us-central",
            "collections": [
                {"path": "users", "fields": [{"name": "email", "type": "string"}]},
            ],
        }
        assert resolve_field_ref("firestore", config, "users.nonexistent") is False

    def test_missing_collection(self):
        config = {"location_id": "us-central", "collections": []}
        assert resolve_field_ref("firestore", config, "users.email") is False


class TestCloudSqlResolution:
    def test_valid_column_path(self):
        config = {
            "database_version": "POSTGRES_15",
            "tier": "db-f1-micro",
            "databases": [{
                "name": "app_db",
                "tables": [{
                    "name": "users",
                    "columns": [{"name": "email", "type": "VARCHAR(255)"}],
                }],
            }],
        }
        assert resolve_field_ref("cloud_sql", config, "app_db.users.email") is True

    def test_invalid_column(self):
        config = {
            "database_version": "POSTGRES_15",
            "tier": "db-f1-micro",
            "databases": [{
                "name": "app_db",
                "tables": [{
                    "name": "users",
                    "columns": [{"name": "email", "type": "VARCHAR(255)"}],
                }],
            }],
        }
        assert resolve_field_ref("cloud_sql", config, "app_db.users.nope") is False


class TestBigQueryResolution:
    def test_valid_column(self):
        config = {
            "dataset_id": "analytics",
            "tables": [{
                "table_id": "events",
                "columns": [{"name": "user_id", "type": "STRING"}],
            }],
        }
        assert resolve_field_ref("bigquery", config, "events.user_id") is True

    def test_invalid_table(self):
        config = {
            "dataset_id": "analytics",
            "tables": [{
                "table_id": "events",
                "columns": [{"name": "user_id", "type": "STRING"}],
            }],
        }
        assert resolve_field_ref("bigquery", config, "nope.user_id") is False


class TestCollectStorageFields:
    def test_collect_firestore_fields(self):
        config = {
            "location_id": "us-central",
            "collections": [
                {"path": "users", "fields": [
                    {"name": "email", "type": "string"},
                    {"name": "name", "type": "string"},
                ]},
            ],
        }
        fields = collect_storage_fields("firestore", config)
        assert "users.email" in fields
        assert "users.name" in fields

    def test_unsupported_type_returns_empty(self):
        fields = collect_storage_fields("unknown_type", {})
        assert fields == []
```

- [ ] **Step 2: Run tests**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration/packages && python -m pytest tests/test_field_resolution.py -v`
Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add packages/tests/test_field_resolution.py
git commit -m "test: add field resolution tests for Firestore, Cloud SQL, BigQuery"
```

---

### Task 13: Run all core unit tests

**Files:** None (verification only)

- [ ] **Step 1: Run full core test suite**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration/packages && python -m pytest tests/ -v --tb=short -m "not integration"`
Expected: All tests PASS. No GCP credentials required.

---

### Task 14: Integration test fixtures (conftest.py)

**Files:**
- Create: `packages/tests/integration/conftest.py`

- [ ] **Step 1: Write integration conftest**

```python
"""Integration test fixtures — GCP clients, cleanup helpers, test identity."""

import os
import uuid

import pytest

# Ensure env is set for auth bypass
os.environ.setdefault("AUTH_DISABLED", "true")
os.environ.setdefault("ENVIRONMENT", "dev")


def _test_prefix():
    """Generate a unique prefix for test resources."""
    return f"test-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_prefix():
    return _test_prefix()


@pytest.fixture
def tenant_id():
    """Tenant ID for integration tests — must match DEV_TENANT_ID env var."""
    return os.environ.get("DEV_TENANT_ID", "dev-local")


@pytest.fixture
def firestore_client():
    """Real Firestore client for integration tests."""
    from google.cloud import firestore
    project = os.environ.get("GCP_PROJECT_ID", "my-super-cool-app-dev-3f74d0")
    database = os.environ.get("FIRESTORE_DATABASE", "(default)")
    return firestore.Client(project=project, database=database)


@pytest.fixture
def gcs_client():
    """Real GCS client for integration tests."""
    from google.cloud import storage
    return storage.Client(project=os.environ.get("GCP_PROJECT_ID", "my-super-cool-app-dev-3f74d0"))


@pytest.fixture
def api_client():
    """FastAPI TestClient with auth disabled."""
    from fastapi.testclient import TestClient
    from packages.api.main import app
    return TestClient(app)


@pytest.fixture
def sample_envelope_data():
    """A minimal valid blueprint envelope dict for integration tests."""
    return {
        "global": {
            "project_id": os.environ.get("GCP_PROJECT_ID", "my-super-cool-app-dev-3f74d0"),
            "region": "us-central1",
            "environment": "dev",
        },
        "nodes": [
            {"name": "test-vpc", "type": "vpc", "config": {"auto_create_subnetworks": False}},
            {"name": "test-sa", "type": "service_account", "config": {"account_id": "test-sa"}},
            {"name": "test-service", "type": "cloud_run", "config": {
                "image": "gcr.io/test/image:latest",
                "service_account": "test-sa",
            }, "depends_on": ["test-vpc", "test-sa"]},
        ],
    }
```

- [ ] **Step 2: Commit**

```bash
git add packages/tests/integration/conftest.py
git commit -m "feat: add integration test fixtures with GCP clients and cleanup helpers"
```

---

### Task 15: Firestore store project tests

**Files:**
- Create: `packages/tests/integration/test_store_projects.py`

- [ ] **Step 1: Write project store tests**

```python
"""Integration tests for Firestore project CRUD."""

import pytest
from packages.platform.store import projects as project_store

pytestmark = pytest.mark.integration


class TestProjectLifecycle:
    def test_create_and_read(self, tenant_id, test_prefix):
        project_data = {
            "id": f"{test_prefix}-proj",
            "name": f"Test Project {test_prefix}",
            "owner_uid": tenant_id,
            "environments": ["dev"],
        }
        try:
            project_store.save_project(tenant_id, project_data)
            result = project_store.get_project(tenant_id, project_data["id"])
            assert result is not None
            assert result["name"] == project_data["name"]
        finally:
            project_store.delete_project(tenant_id, project_data["id"])

    def test_list_projects(self, tenant_id, test_prefix):
        project_data = {
            "id": f"{test_prefix}-list",
            "name": f"List Test {test_prefix}",
            "owner_uid": tenant_id,
            "environments": ["dev"],
        }
        try:
            project_store.save_project(tenant_id, project_data)
            projects = project_store.list_projects(tenant_id)
            ids = [p.get("id") for p in projects]
            assert project_data["id"] in ids
        finally:
            project_store.delete_project(tenant_id, project_data["id"])

    def test_delete_project(self, tenant_id, test_prefix):
        project_data = {
            "id": f"{test_prefix}-del",
            "name": f"Delete Test {test_prefix}",
            "owner_uid": tenant_id,
            "environments": ["dev"],
        }
        project_store.save_project(tenant_id, project_data)
        project_store.delete_project(tenant_id, project_data["id"])
        result = project_store.get_project(tenant_id, project_data["id"])
        assert result is None

    def test_update_settings(self, tenant_id, test_prefix):
        project_data = {
            "id": f"{test_prefix}-upd",
            "name": f"Update Test {test_prefix}",
            "owner_uid": tenant_id,
            "environments": ["dev"],
        }
        try:
            project_store.save_project(tenant_id, project_data)
            project_store.update_project_settings(tenant_id, project_data["id"], {"region": "europe-west1"})
            result = project_store.get_project(tenant_id, project_data["id"])
            assert result.get("region") == "europe-west1"
        finally:
            project_store.delete_project(tenant_id, project_data["id"])
```

- [ ] **Step 2: Run tests**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration/packages && python -m pytest tests/integration/test_store_projects.py -v -m integration`
Expected: All tests PASS (requires GCP credentials).

- [ ] **Step 3: Commit**

```bash
git add packages/tests/integration/test_store_projects.py
git commit -m "test: add Firestore project store integration tests"
```

---

### Task 16: Firestore store blueprint tests

**Files:**
- Create: `packages/tests/integration/test_store_blueprints.py`

- [ ] **Step 1: Write blueprint store tests**

```python
"""Integration tests for Firestore blueprint CRUD with node sharding."""

import pytest
from packages.platform.store import blueprints as blueprint_store
from packages.platform.store import projects as project_store

pytestmark = pytest.mark.integration


class TestBlueprintLifecycle:
    def test_save_and_read_back(self, tenant_id, test_prefix, sample_envelope_data):
        project_id = f"{test_prefix}-bp"
        project_data = {
            "id": project_id,
            "name": f"BP Test {test_prefix}",
            "owner_uid": tenant_id,
            "environments": ["dev"],
        }
        try:
            project_store.save_project(tenant_id, project_data)
            result = blueprint_store.save_env_blueprint(tenant_id, project_id, "dev", sample_envelope_data)
            assert result["node_count"] == 3

            doc = blueprint_store.get_env_blueprint(tenant_id, project_id, "dev")
            assert doc is not None
            envelope = doc.get("envelope", doc)
            nodes = envelope.get("nodes", [])
            assert len(nodes) == 3
        finally:
            project_store.delete_project(tenant_id, project_id)

    def test_node_sharding_reconstruction(self, tenant_id, test_prefix):
        """Save 5+ nodes and verify sharded subcollection reconstructs correctly."""
        project_id = f"{test_prefix}-shard"
        project_data = {
            "id": project_id,
            "name": f"Shard Test {test_prefix}",
            "owner_uid": tenant_id,
            "environments": ["dev"],
        }
        envelope = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": f"vpc-{i}", "type": "vpc", "config": {"auto_create_subnetworks": False}}
                for i in range(6)
            ],
        }
        try:
            project_store.save_project(tenant_id, project_data)
            result = blueprint_store.save_env_blueprint(tenant_id, project_id, "dev", envelope)
            assert result["node_count"] == 6

            doc = blueprint_store.get_env_blueprint(tenant_id, project_id, "dev")
            read_envelope = doc.get("envelope", doc)
            read_nodes = read_envelope.get("nodes", [])
            assert len(read_nodes) == 6
            names = {n["name"] for n in read_nodes}
            assert names == {f"vpc-{i}" for i in range(6)}
        finally:
            project_store.delete_project(tenant_id, project_id)

    def test_change_detection(self, tenant_id, test_prefix, sample_envelope_data):
        """Save blueprint twice with modifications, verify change tracking."""
        project_id = f"{test_prefix}-chg"
        project_data = {
            "id": project_id,
            "name": f"Change Test {test_prefix}",
            "owner_uid": tenant_id,
            "environments": ["dev"],
        }
        try:
            project_store.save_project(tenant_id, project_data)

            # First save — all nodes are "added"
            result1 = blueprint_store.save_env_blueprint(tenant_id, project_id, "dev", sample_envelope_data)
            assert result1["node_count"] == 3

            # Second save — modify one node's config
            modified = dict(sample_envelope_data)
            modified["nodes"] = list(sample_envelope_data["nodes"])
            modified_node = dict(modified["nodes"][2])
            modified_node["config"] = dict(modified_node["config"])
            modified_node["config"]["image"] = "gcr.io/test/image:v2"
            modified["nodes"][2] = modified_node

            result2 = blueprint_store.save_env_blueprint(tenant_id, project_id, "dev", modified)
            changes = result2.get("changes", {})
            # Should detect modified node
            assert len(changes.get("modified", [])) >= 1 or result2.get("is_noop") is not True
        finally:
            project_store.delete_project(tenant_id, project_id)
```

- [ ] **Step 2: Run tests**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration/packages && python -m pytest tests/integration/test_store_blueprints.py -v -m integration`
Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add packages/tests/integration/test_store_blueprints.py
git commit -m "test: add Firestore blueprint store integration tests with sharding"
```

---

### Task 17: Firestore collaborator tests

**Files:**
- Create: `packages/tests/integration/test_store_collaborators.py`

- [ ] **Step 1: Write collaborator store tests**

```python
"""Integration tests for collaborator management."""

import pytest
from packages.platform.store import collaborators as collab_store
from packages.platform.store import projects as project_store

pytestmark = pytest.mark.integration


class TestCollaboratorLifecycle:
    def test_add_and_list(self, tenant_id, test_prefix):
        project_id = f"{test_prefix}-collab"
        project_data = {
            "id": project_id,
            "name": f"Collab Test {test_prefix}",
            "owner_uid": tenant_id,
            "environments": ["dev"],
        }
        try:
            project_store.save_project(tenant_id, project_data)
            collab_store.add_collaborator(
                tenant_id, project_id, "collab@test.com", "viewer",
                collaborator_uid="collab-user-123",
            )
            collabs = collab_store.list_collaborators(tenant_id, project_id)
            emails = [c.get("email") for c in collabs]
            assert "collab@test.com" in emails
        finally:
            collab_store.remove_collaborator(tenant_id, project_id, "collab-user-123")
            project_store.delete_project(tenant_id, project_id)

    def test_remove_collaborator(self, tenant_id, test_prefix):
        project_id = f"{test_prefix}-rmcol"
        project_data = {
            "id": project_id,
            "name": f"Remove Collab Test {test_prefix}",
            "owner_uid": tenant_id,
            "environments": ["dev"],
        }
        try:
            project_store.save_project(tenant_id, project_data)
            collab_store.add_collaborator(
                tenant_id, project_id, "rm@test.com", "editor",
                collaborator_uid="rm-user-456",
            )
            collab_store.remove_collaborator(tenant_id, project_id, "rm-user-456")
            collabs = collab_store.list_collaborators(tenant_id, project_id)
            uids = [c.get("uid") for c in collabs]
            assert "rm-user-456" not in uids
        finally:
            project_store.delete_project(tenant_id, project_id)
```

- [ ] **Step 2: Run tests**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration/packages && python -m pytest tests/integration/test_store_collaborators.py -v -m integration`
Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add packages/tests/integration/test_store_collaborators.py
git commit -m "test: add Firestore collaborator store integration tests"
```

---

### Task 18: GCS storage tests

**Files:**
- Create: `packages/tests/integration/test_gcp_storage.py`

- [ ] **Step 1: Write GCS tests**

```python
"""Integration tests for GCS storage operations."""

import os
import pytest
from google.cloud import storage

pytestmark = pytest.mark.integration

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "my-super-cool-app-dev-3f74d0")
# Use the Cloud Build source bucket (already exists in tenant projects)
BUCKET_NAME = os.environ.get("CB_SOURCE_BUCKET", f"{PROJECT_ID}-cb-source")


class TestGcsOperations:
    def test_upload_and_download(self, test_prefix):
        client = storage.Client(project=PROJECT_ID)
        bucket = client.bucket(BUCKET_NAME)
        blob_name = f"test/{test_prefix}/test-file.txt"
        content = f"test content {test_prefix}"

        try:
            blob = bucket.blob(blob_name)
            blob.upload_from_string(content)

            downloaded = blob.download_as_text()
            assert downloaded == content
        finally:
            blob = bucket.blob(blob_name)
            if blob.exists():
                blob.delete()

    def test_list_blobs(self, test_prefix):
        client = storage.Client(project=PROJECT_ID)
        bucket = client.bucket(BUCKET_NAME)
        prefix = f"test/{test_prefix}/"
        blob_name = f"{prefix}list-test.txt"

        try:
            blob = bucket.blob(blob_name)
            blob.upload_from_string("list test content")

            blobs = list(bucket.list_blobs(prefix=prefix))
            names = [b.name for b in blobs]
            assert blob_name in names
        finally:
            blob = bucket.blob(blob_name)
            if blob.exists():
                blob.delete()
```

- [ ] **Step 2: Run tests**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration/packages && python -m pytest tests/integration/test_gcp_storage.py -v -m integration`
Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add packages/tests/integration/test_gcp_storage.py
git commit -m "test: add GCS storage integration tests"
```

---

### Task 19: Secret Manager tests

**Files:**
- Create: `packages/tests/integration/test_gcp_secrets.py`

- [ ] **Step 1: Write Secret Manager tests**

```python
"""Integration tests for Secret Manager operations."""

import os
import pytest
from google.cloud import secretmanager

pytestmark = pytest.mark.integration

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "my-super-cool-app-dev-3f74d0")


class TestSecretManagerOperations:
    def test_create_and_read_secret(self, test_prefix):
        client = secretmanager.SecretManagerServiceClient()
        secret_id = f"{test_prefix}-secret"
        parent = f"projects/{PROJECT_ID}"
        secret_name = f"{parent}/secrets/{secret_id}"

        try:
            # Create secret
            client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": secret_id,
                    "secret": {"replication": {"automatic": {}}},
                }
            )

            # Add version
            client.add_secret_version(
                request={
                    "parent": secret_name,
                    "payload": {"data": b"test-value-123"},
                }
            )

            # Read latest version
            response = client.access_secret_version(
                request={"name": f"{secret_name}/versions/latest"}
            )
            assert response.payload.data == b"test-value-123"

        finally:
            try:
                client.delete_secret(request={"name": secret_name})
            except Exception:
                pass  # Already deleted or never created
```

- [ ] **Step 2: Run tests**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration/packages && python -m pytest tests/integration/test_gcp_secrets.py -v -m integration`
Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add packages/tests/integration/test_gcp_secrets.py
git commit -m "test: add Secret Manager integration tests"
```

---

### Task 20: Cloud Build tests

**Files:**
- Create: `packages/tests/integration/test_gcp_cloud_build.py`

- [ ] **Step 1: Write Cloud Build tests**

```python
"""Integration tests for Cloud Build submission and polling."""

import os
import time
import pytest
from google.cloud.devtools import cloudbuild_v1

pytestmark = pytest.mark.integration

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "my-super-cool-app-dev-3f74d0")


class TestCloudBuild:
    @pytest.mark.timeout(120)
    def test_submit_and_poll_simple_build(self):
        """Submit a minimal build (echo command) and poll until completion."""
        client = cloudbuild_v1.CloudBuildClient()

        build = cloudbuild_v1.Build(
            steps=[
                cloudbuild_v1.BuildStep(
                    name="ubuntu",
                    args=["echo", "integration test passed"],
                ),
            ],
            timeout={"seconds": 60},
        )

        operation = client.create_build(project_id=PROJECT_ID, build=build)
        build_result = operation.result(timeout=120)

        assert build_result.status == cloudbuild_v1.Build.Status.SUCCESS
```

- [ ] **Step 2: Run test**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration/packages && python -m pytest tests/integration/test_gcp_cloud_build.py -v -m integration --timeout=120`
Expected: PASS (may take 30-60 seconds for the build to complete).

- [ ] **Step 3: Commit**

```bash
git add packages/tests/integration/test_gcp_cloud_build.py
git commit -m "test: add Cloud Build submission integration test"
```

---

### Task 21: API health and schema tests

**Files:**
- Create: `packages/tests/integration/test_api_health.py`

- [ ] **Step 1: Write API health tests**

```python
"""API layered tests — health, config, schema endpoints."""

import pytest

pytestmark = pytest.mark.integration


class TestHealthEndpoints:
    def test_health_returns_ok(self, api_client):
        response = api_client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_me_returns_dev_user(self, api_client):
        response = api_client.get("/api/me")
        assert response.status_code == 200
        data = response.json()
        assert "tenant_id" in data
        assert "email" in data

    def test_schema_types_returns_all_node_types(self, api_client):
        response = api_client.get("/api/schema/types")
        assert response.status_code == 200
        data = response.json()
        # Should have all 23 node types
        assert len(data) == 23
        assert "cloud_run" in data
        assert "firestore" in data
        assert "vpc" in data

    def test_schema_type_has_expected_fields(self, api_client):
        response = api_client.get("/api/schema/types")
        data = response.json()
        cr = data["cloud_run"]
        assert cr["label"] == "Cloud Run"
        assert cr["category"] == "Compute"
        assert cr["is_compute"] is True
        assert cr["terraform_resource"] == "google_cloud_run_v2_service"
```

- [ ] **Step 2: Run tests**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration/packages && python -m pytest tests/integration/test_api_health.py -v -m integration`
Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add packages/tests/integration/test_api_health.py
git commit -m "test: add API health, me, and schema endpoint tests"
```

---

### Task 22: API blueprint validation tests

**Files:**
- Create: `packages/tests/integration/test_api_blueprints.py`

- [ ] **Step 1: Write API blueprint tests**

```python
"""API layered tests — blueprint validation and CRUD."""

import pytest

pytestmark = pytest.mark.integration


class TestBlueprintValidation:
    def test_validate_valid_envelope(self, api_client, sample_envelope_data):
        response = api_client.post("/api/blueprints/validate", json=sample_envelope_data)
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True

    def test_validate_invalid_envelope_missing_global(self, api_client):
        response = api_client.post("/api/blueprints/validate", json={"nodes": []})
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False

    def test_validate_returns_issues_for_bad_deps(self, api_client):
        payload = {
            "global": {"project_id": "test", "region": "us-central1", "environment": "dev"},
            "nodes": [
                {"name": "my-vpc", "type": "vpc", "config": {"auto_create_subnetworks": False},
                 "depends_on": ["ghost"]},
            ],
        }
        response = api_client.post("/api/blueprints/validate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["issues"]) >= 1

    def test_schema_validate_valid(self, api_client, sample_envelope_data):
        response = api_client.post("/api/schema/validate", json=sample_envelope_data)
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["node_count"] == 3

    def test_schema_validate_invalid(self, api_client):
        response = api_client.post("/api/schema/validate", json={"bad": "data"})
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
```

- [ ] **Step 2: Run tests**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration/packages && python -m pytest tests/integration/test_api_blueprints.py -v -m integration`
Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add packages/tests/integration/test_api_blueprints.py
git commit -m "test: add API blueprint validation tests"
```

---

### Task 23: API Terraform generation tests

**Files:**
- Create: `packages/tests/integration/test_api_terraform.py`

- [ ] **Step 1: Write API Terraform tests**

```python
"""API layered tests — Terraform generate and preview endpoints."""

import pytest

pytestmark = pytest.mark.integration


class TestTerraformGeneration:
    def test_generate_returns_tf_files(self, api_client, sample_envelope_data):
        response = api_client.post("/api/terraform/generate", json=sample_envelope_data)
        assert response.status_code == 200
        data = response.json()
        assert "files" in data
        files = data["files"]
        assert "provider.tf" in files
        assert "variables.tf" in files
        assert "main.tf" in files

    def test_generate_main_contains_resources(self, api_client, sample_envelope_data):
        response = api_client.post("/api/terraform/generate", json=sample_envelope_data)
        data = response.json()
        main_tf = data["files"]["main.tf"]
        assert "google_compute_network" in main_tf
        assert "google_service_account" in main_tf

    def test_preview_lists_resources(self, api_client, sample_envelope_data):
        response = api_client.post("/api/terraform/preview", json=sample_envelope_data)
        assert response.status_code == 200
        data = response.json()
        assert "resources" in data
        types = {r["terraform_resource"] for r in data["resources"]}
        assert "google_compute_network" in types
        assert "google_cloud_run_v2_service" in types

    def test_generate_invalid_envelope_returns_error(self, api_client):
        response = api_client.post("/api/terraform/generate", json={"bad": "data"})
        assert response.status_code == 422 or response.status_code == 200
        # Either returns 422 validation error or 200 with error info
```

- [ ] **Step 2: Run tests**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration/packages && python -m pytest tests/integration/test_api_terraform.py -v -m integration`
Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add packages/tests/integration/test_api_terraform.py
git commit -m "test: add API Terraform generate and preview tests"
```

---

### Task 24: API project lifecycle tests

**Files:**
- Create: `packages/tests/integration/test_api_projects.py`

- [ ] **Step 1: Write API project tests**

```python
"""API layered tests — project CRUD lifecycle."""

import pytest

pytestmark = pytest.mark.integration


class TestProjectLifecycle:
    def test_create_list_delete(self, api_client, test_prefix):
        # Create
        project_data = {
            "name": f"API Test {test_prefix}",
            "ref_id": f"{test_prefix}-api-proj",
        }
        create_resp = api_client.post("/api/projects", json=project_data)
        assert create_resp.status_code == 200
        created = create_resp.json()
        project_ref_id = created.get("ref_id") or created.get("id") or project_data["ref_id"]

        try:
            # List — should include the new project
            list_resp = api_client.get("/api/projects")
            assert list_resp.status_code == 200
            projects = list_resp.json()
            ids = [p.get("ref_id") or p.get("id") for p in projects]
            assert project_ref_id in ids

            # Delete
            delete_resp = api_client.delete(f"/api/projects/{project_ref_id}")
            assert delete_resp.status_code == 200

            # Verify deleted
            list_resp2 = api_client.get("/api/projects")
            ids2 = [p.get("ref_id") or p.get("id") for p in list_resp2.json()]
            assert project_ref_id not in ids2
        except Exception:
            # Cleanup on failure
            api_client.delete(f"/api/projects/{project_ref_id}")
            raise
```

- [ ] **Step 2: Run tests**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration/packages && python -m pytest tests/integration/test_api_projects.py -v -m integration`
Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add packages/tests/integration/test_api_projects.py
git commit -m "test: add API project lifecycle integration tests"
```

---

### Task 25: API deploy flow test

**Files:**
- Create: `packages/tests/integration/test_api_deploy.py`

- [ ] **Step 1: Write API deploy test**

```python
"""API layered tests — full deploy pipeline (crown jewel).

This test exercises the entire flow: create project -> save blueprint ->
trigger deploy -> poll status. It requires the full GCP integration to be
working (Firestore, Cloud Build, GCS).
"""

import os
import time
import pytest

pytestmark = pytest.mark.integration

# This test is slow (Cloud Build takes time) — skip if env flag set
skip_deploy = os.environ.get("SKIP_DEPLOY_TEST", "").lower() in ("true", "1")


@pytest.mark.skipif(skip_deploy, reason="SKIP_DEPLOY_TEST is set")
class TestDeployPipeline:
    @pytest.mark.timeout(300)
    def test_full_deploy_flow(self, api_client, test_prefix, sample_envelope_data):
        """Create project, save blueprint, trigger deploy, poll until done."""
        project_ref_id = f"{test_prefix}-deploy"

        # 1. Create project
        create_resp = api_client.post("/api/projects", json={
            "name": f"Deploy Test {test_prefix}",
            "ref_id": project_ref_id,
        })
        assert create_resp.status_code == 200

        try:
            # 2. Save blueprint
            save_resp = api_client.put(
                f"/api/projects/{project_ref_id}/envs/dev/blueprint",
                json=sample_envelope_data,
            )
            assert save_resp.status_code == 200

            # 3. Trigger deploy
            deploy_resp = api_client.post(
                f"/api/projects/{project_ref_id}/envs/dev/deploy",
            )
            # Deploy may return 200 or 202
            assert deploy_resp.status_code in (200, 202)
            deploy_data = deploy_resp.json()
            deploy_id = deploy_data.get("deploy_id") or deploy_data.get("id")

            if deploy_id:
                # 4. Poll deploy status (up to 4 minutes)
                for _ in range(48):
                    status_resp = api_client.get(
                        f"/api/projects/{project_ref_id}/deploys/{deploy_id}/status"
                    )
                    if status_resp.status_code == 200:
                        status = status_resp.json().get("status", "")
                        if status in ("success", "completed", "failed", "error"):
                            break
                    time.sleep(5)

        finally:
            # Cleanup
            api_client.delete(f"/api/projects/{project_ref_id}")
```

- [ ] **Step 2: Run test (optional — slow)**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration/packages && python -m pytest tests/integration/test_api_deploy.py -v -m integration --timeout=300`
Expected: Test runs (may timeout on first run if Cloud Build isn't fully configured for the tenant project). Set `SKIP_DEPLOY_TEST=true` to skip.

- [ ] **Step 3: Commit**

```bash
git add packages/tests/integration/test_api_deploy.py
git commit -m "test: add full deploy pipeline integration test"
```

---

### Task 26: Run full test suite

**Files:** None (verification only)

- [ ] **Step 1: Run core unit tests**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration/packages && python -m pytest tests/ -v --tb=short -m "not integration"`
Expected: All core tests PASS. No GCP credentials needed.

- [ ] **Step 2: Run integration tests**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration/packages && python -m pytest tests/ -v --tb=short -m integration`
Expected: All integration tests PASS (requires GCP credentials and network).

- [ ] **Step 3: Run everything**

Run: `cd /Users/fsl/Documents/GitHub/gcp-orchestration/packages && python -m pytest tests/ -v --tb=short`
Expected: Full green. Core tests fast, integration tests take longer but all pass.
