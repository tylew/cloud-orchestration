# Packages Bootability & Testing Design

**Date:** 2026-03-25
**Goal:** Get the Python packages (`core`, `api`, `platform`) running locally via Docker and verified through a layered test suite, so the UI/UX layers can be engineered on top of a proven backend.

**Approach:** Bottom-up. Verify each layer before stacking the next.

---

## 1. Docker & Local Bootability

### Dockerfile (repo root)

- **Base:** `python:3.12-slim`
- **Copy:** Entire repo into container (code imports use `packages.api`, `packages.core`, `packages.platform` paths)
- **Install:** `pip install ./packages` to install dependencies from `packages/pyproject.toml`
- **Workdir:** Repo root (so `packages.*` imports resolve)
- **Entrypoint:** `uvicorn packages.api.main:app --host 0.0.0.0 --port 8080`
- No `gcloud`/`terraform` in the dev image — those are only needed in the Cloud Build builder image for tenant deploys

### docker-compose.yml Fixes

- Fix build context and module path (`packages.api.main:app`, not `backend.main:app`)
- Mount `packages/` for hot reload during development
- Load `.env` file with defaults for: `GCP_PROJECT_ID`, `FIRESTORE_DATABASE`, `AUTH_DISABLED=true`, `DEV_USER_*` vars
- Drop the `frontend` service (not relevant yet — `test-frontend/` is empty, `product-sales-site` is a separate Next.js app)

### CORS Fix

- Add `localhost` and `http://localhost:5173` to allowed origins in `api/main.py` (currently hardcoded to Firebase production domains only)
- Gate behind `ENVIRONMENT` env var so production stays locked down

### Verification

`docker compose up` then `GET http://localhost:8080/api/health` returns 200 (all routes are mounted under `/api` prefix).

---

## 2. Configurable Dev User

### Current State

`platform/auth/firebase.py` has a hardcoded `_DEV_USER`:

```python
_DEV_USER = CurrentUser(
    tenant_id="dev-local",
    email="dev@localhost",
    display_name="Local Developer",
    is_admin=True,
)
```

### Change

Read from environment variables with fallbacks to current defaults. `CurrentUser` has four fields: `tenant_id`, `email`, `display_name`, `is_admin`.

| Env Var | Fallback | Maps To |
|---------|----------|---------|
| `DEV_TENANT_ID` | `"dev-local"` | `tenant_id` (= Firebase UID of the tenant owner) |
| `DEV_USER_EMAIL` | `"dev@localhost"` | `email` |
| `DEV_USER_DISPLAY_NAME` | `"Local Developer"` | `display_name` |
| `DEV_USER_IS_ADMIN` | `"true"` | `is_admin` |

Modify the existing `_DEV_USER` construction in `firebase.py` to use `os.environ.get()`. No new files.

### Usage

- **Integration tests against `my-super-cool-app-dev-3f74d0`:** Set vars to Tyler's identity so Firestore paths align with the real tenant project.
- **Pure local dev:** Leave unset, get the same dev defaults as today.

---

## 3. Core Unit Tests

Pure logic tests. No GCP, no mocks, no credentials needed.

### Validation (`test_validation.py`)

| Test Case | What It Proves |
|-----------|---------------|
| Valid blueprint passes clean | Happy path works |
| Missing required fields per node type | Per-type field requirements enforced |
| Duplicate node names caught | Uniqueness validation works |
| Invalid `depends_on` references | Cross-node reference validation |
| Child-parent relationship violations | `CHILD_PARENT_MAP` enforcement (e.g., `CLOUD_SQL_DATABASE` without `CLOUD_SQL`) |
| Firestore free-tier quota warnings | Quota checking logic |
| Severity levels (error vs warning) | Issue classification is correct |

### DAG (`test_dag.py`)

| Test Case | What It Proves |
|-----------|---------------|
| Topological sort on simple graph | Ordering works |
| Cycle detection raises error | Cycles caught |
| `parallel_batches()` groups independent nodes | Parallelization logic |
| Missing dependency references | `validate_ordering()` catches dangling refs |

### Terraform Generation (`test_terraform.py`)

| Test Case | What It Proves |
|-----------|---------------|
| Single node produces valid `.tf` file dict | Basic generation works |
| Multi-node with dependencies produces correct resource references | Cross-resource wiring |
| `preview_resources()` returns expected list | Resource preview matches blueprint |
| Child resources embedded in parent output | BQ tables, SQL databases attach correctly |

### Field Resolution (`test_field_resolution.py`)

| Test Case | What It Proves |
|-----------|---------------|
| Valid field refs resolve correctly | Happy path |
| Invalid refs produce clear errors | Error messaging |

### Registry (`test_registry.py`)

| Test Case | What It Proves |
|-----------|---------------|
| All 23 node types have definitions | Registry completeness |
| `get_config_model()` returns correct Pydantic class | Type-to-config mapping |
| `is_compute()` correct for compute vs non-compute | Compute classification |

### Test Fixtures (`conftest.py`)

Reusable `Envelope` objects:

- **Minimal valid blueprint** — 2-3 nodes with dependencies (e.g., Cloud Run → Cloud SQL → VPC)
- **Invalid blueprint** — Cycles, missing fields, duplicate names
- **Complex blueprint** — 10+ nodes covering multiple node types and dependency patterns

### File Structure

```
packages/tests/
    conftest.py
    test_validation.py
    test_dag.py
    test_terraform.py
    test_field_resolution.py
    test_registry.py
```

---

## 4. Platform Integration Tests

Hit real GCP on `my-super-cool-app-dev-3f74d0`. Require gcloud credentials.

### Firestore Store Tests

| Module | Test Cases |
|--------|-----------|
| `test_store_projects.py` | Create project, read back, update settings, list, delete. Verify full doc lifecycle. |
| `test_store_blueprints.py` | Save blueprint with 5+ nodes, read back, verify node sharding reconstructs correctly. Test add/remove/modify change detection. |
| `test_store_collaborators.py` | Add collaborator, verify role, list, remove. Check `shared_projects` index updates. |

### GCP Service Tests

| Module | Test Cases |
|--------|-----------|
| `test_gcp_storage.py` | Upload file to GCS, download, verify content, clean up. |
| `test_gcp_cloud_build.py` | Submit minimal Terraform build (e.g., `null_resource`), poll status, verify success. |
| `test_gcp_secrets.py` | Create secret, read version, clean up. |

### Cleanup Strategy

- Each test creates resources with a test-run prefix: `test-{uuid4[:8]}`
- Teardown in `finally` blocks or pytest fixture finalizers
- No orphaned resources

### File Structure

```
packages/tests/integration/
    conftest.py              # GCP client fixtures, test tenant config, cleanup helpers
    test_store_projects.py
    test_store_blueprints.py
    test_store_collaborators.py
    test_gcp_storage.py
    test_gcp_cloud_build.py
    test_gcp_secrets.py
```

### Pytest Marker

All integration tests marked with `@pytest.mark.integration`.

---

## 5. API Layered Tests

Boot FastAPI with `TestClient`, wired to real GCP through the platform layer. Prove end-to-end user flows.

### Flows to Test

**Health & Config (`test_api_health.py`):**
- `GET /api/health` returns 200
- `GET /api/me` returns the configured dev user
- `GET /api/schema/types` returns all 23 node types from registry

Note: All routes are mounted under the `/api` prefix in `main.py`.

**Blueprint Lifecycle (`test_api_blueprints.py`):**
- `POST /api/blueprints/validate` with valid envelope returns `valid: true`
- `POST /api/blueprints/validate` with invalid envelope returns issues array
- `PUT /api/projects/{id}/envs/{env}/blueprint` saves, then `GET` reads back matching nodes

**Terraform Generation (`test_api_terraform.py`):**
- `POST /api/terraform/generate` with multi-node blueprint returns `.tf` file dict with expected resource blocks
- `POST /api/terraform/preview` returns resource list matching the blueprint

**Project Lifecycle (`test_api_projects.py`):**
- Create project, list (verify appears), update settings, delete (verify gone)

**Deploy Flow (`test_api_deploy.py`):**
- Create project, save blueprint, trigger deploy, poll status until complete or timeout
- This is the crown jewel — proves the full pipeline from blueprint to infrastructure

### Auth

All API tests use `AUTH_DISABLED=true` with the configurable dev user. `TestClient` does not send Firebase tokens.

### Separation from Platform Tests

Platform tests verify individual store/GCP operations. API tests verify handlers wire everything together. If an API test fails but the corresponding platform test passes, the bug is in the handler layer.

### File Structure

```
packages/tests/integration/
    test_api_health.py
    test_api_blueprints.py
    test_api_terraform.py
    test_api_projects.py
    test_api_deploy.py
```

---

## 6. Test Configuration

### pytest config (in `packages/pyproject.toml`)

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["integration: requires GCP credentials and network"]
asyncio_mode = "auto"
```

### Environment

`.env.test` file (added to `.gitignore`) with tenant project config:

```env
GCP_PROJECT_ID=my-super-cool-app-dev-3f74d0
AUTH_DISABLED=true
DEV_TENANT_ID=<tyler-firebase-uid>       # Get from Firebase Console → Authentication → Users
DEV_USER_EMAIL=tyler@pl4m.com
DEV_USER_DISPLAY_NAME=Tyler
DEV_USER_IS_ADMIN=true
FIRESTORE_DATABASE=(default)
```

Docker compose loads env file — no `python-dotenv` needed.

### Dev Dependencies to Add

- `pytest-asyncio` — async test support for FastAPI TestClient and async Firestore calls

(Alongside existing `pytest` and `httpx` in `[project.optional-dependencies] dev`)

### Run Commands

| Command | What It Runs |
|---------|-------------|
| `pytest` | Core unit tests only (fast, no credentials) |
| `pytest -m integration` | Integration + API tests (needs GCP auth) |
| `pytest -m "not integration"` | Explicitly excludes integration |
| `docker compose run --rm app pytest` | Tests inside container with mounted credentials |

---

## Implementation Order

| Step | Layer | Depends On |
|------|-------|-----------|
| 1 | Dockerfile + docker-compose fixes | Nothing |
| 2 | Configurable dev user | Nothing |
| 3 | CORS localhost fix | Nothing |
| 4 | pytest config + dev deps | Step 1 (to verify in container) |
| 5 | Core unit tests | Step 4 |
| 6 | Platform integration tests | Steps 2, 4 |
| 7 | API layered tests | Steps 2, 3, 4 |

Steps 1-3 are independent and can be done in parallel. Steps 5-7 can proceed in parallel once step 4 is done.

---

## Success Criteria

- `docker compose up` boots the FastAPI server, `GET /api/health` returns 200
- `pytest` (core only) passes with zero GCP dependencies
- `pytest -m integration` passes against `my-super-cool-app-dev-3f74d0`
- API tests prove: blueprint validation, Terraform generation, project CRUD, and deploy flow all work end-to-end
- No orphaned GCP resources after test runs
- UI/UX engineering can begin with confidence that the API surface is verified
