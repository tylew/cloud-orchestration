<!-- GSD:project-start source:PROJECT.md -->
## Project

**GCP Orchestration Platform**

A platform that abstracts GCP infrastructure for developers. Users visually design their cloud architecture as a node graph (Cloud Run, Cloud Functions, Cloud SQL, Firestore, etc.), define dependencies and data contracts between services, and deploy with one click -- without touching GCP directly. The platform handles Terraform generation, Cloud Build submission, GCP project provisioning, and deployment orchestration. Eventually, MCP tools and AI agents will layer on top to assist with infrastructure configuration and service code generation grounded in the actual infrastructure state (DB schemas, IAM bindings, networking).

**Core Value:** Users go from a visual architecture diagram to running, multi-environment GCP infrastructure without needing to understand Terraform, IAM, or GCP internals.

### Constraints

- **Tech stack**: Must stay on GCP (Cloud Run, Firestore, Cloud Build) -- the platform orchestrates GCP
- **Architecture**: Backend must remain stateless (FastAPI + Firestore) for Cloud Run scaling
- **Billing**: Stripe metered billing for pass-through GCP costs -- no alternative payment processors
- **Free tier limits**: 1-3 compute nodes per project to control costs
- **Existing users**: Cannot break current blueprint format -- migration path required if schema changes
- **Networking**: Host project likely owns shared infrastructure; tenants get isolated segments
- **Deliverable**: Complete specification -- every subsystem documented with data models, sequences, and edge cases
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.12 - Backend API server, all packages under `packages/`
- TypeScript ~5.9 - Frontend web app (`apps/web/`)
- TypeScript ~5.x - Product sales site (`apps/product-sales-site/`)
- HCL (Terraform) - Infrastructure definitions (`infra/host/`)
- Jinja2 - Terraform template generation (`packages/core/terraform/templates/*.tf.j2`)
## Runtime
- Python 3.12 (Docker base image: `python:3.12-slim`)
- Node.js 20 (used in `docker-compose.yml` web service and Cloud Build steps)
- pip with setuptools >= 68 (Python) - configured in `packages/pyproject.toml`
- npm (Node.js) - configured in `apps/web/package.json`, `apps/product-sales-site/package.json`
- Lockfile: `package-lock.json` present for npm; Python uses `pyproject.toml` with no lockfile
## Frameworks
- FastAPI >= 0.115 - Backend REST API (`packages/api/main.py`)
- React ^19.0.0 - Frontend UI (`apps/web/`)
- Next.js 16.2.0 - Product sales/marketing site (`apps/product-sales-site/`)
- Pydantic >= 2.0 - Data validation and serialization (`packages/core/schemas/`)
- pytest with pytest-asyncio - Python backend tests (`packages/pyproject.toml` `[project.optional-dependencies]`)
- No frontend test framework detected (no jest/vitest config)
- Vite ^6.0.0 - Frontend dev server and bundler (`apps/web/vite.config.ts`)
- Docker - Containerized backend (`Dockerfile`)
- Docker Compose - Local multi-service development (`docker-compose.yml`)
- Terraform >= 1.5 - Infrastructure as Code (`infra/host/main.tf`)
## Key Dependencies
- `fastapi` >= 0.115 - Web framework, router-based API design
- `uvicorn[standard]` - ASGI server (production and dev)
- `pydantic` >= 2.0 - Schema validation for blueprints, configs, API payloads
- `google-cloud-firestore` >= 2.16 - Primary database client
- `firebase-admin` >= 6.0 - Firebase Auth token verification
- `google-cloud-build` >= 3.0 - Cloud Build API for Terraform and container builds
- `google-cloud-storage` - GCS for TF source tarballs, code file storage, build artifacts
- `google-cloud-secret-manager` >= 2.20 - Secret CRUD operations
- `google-cloud-resource-manager` >= 1.12 - GCP project/folder creation and management
- `google-cloud-billing` >= 1.13 - Billing account linking
- `google-cloud-service-usage` >= 1.8 - API enablement on tenant projects
- `google-cloud-logging` >= 3.10 - Cloud Logging for build log streaming
- `google-auth` >= 2.29 - Default credentials and access token generation
- `jinja2` - Terraform HCL template rendering
- `sse-starlette` >= 2.0 - Server-Sent Events for deploy log streaming
- `httpx` >= 0.24 - Async HTTP client (GitHub API, general HTTP)
- `PyJWT` >= 2.0 - JWT signing for GitHub App authentication
- `cryptography` >= 3.0 - Key handling for GitHub App private keys
- `firebase` ^12.11.0 - Client SDK (Auth, Firestore real-time listeners)
- `react` ^19.0.0 - UI framework
- `react-dom` ^19.0.0 - DOM rendering
- `react-router-dom` ^7.0.0 - Client-side routing
- `zustand` ^5.0.0 - State management (stores in `apps/web/src/stores/`)
- `clsx` ^2.1.1 + `tailwind-merge` ^3.5.0 - CSS class utilities
- `class-variance-authority` ^0.7.1 - Component variant patterns
- `shadcn` ^4.1.0 - UI component library (source-installed)
- `@base-ui/react` ^1.3.0 - Base UI components
- `lucide-react` ^1.7.0 - Icon library
- `@fontsource-variable/geist` ^5.2.8 - Font
- `next` 16.2.0 - React SSR framework
- `@xyflow/react` ^12.10.1 - Node graph diagram editor (interactive demos)
- `framer-motion` ^12.38.0 - Animation library
- `react` 19.2.4 / `react-dom` 19.2.4 - UI framework (pinned version)
- `tailwindcss` ^4.0.0 - Utility-first CSS framework
- `@tailwindcss/vite` ^4.0.0 - Tailwind Vite plugin
- `@vitejs/plugin-react` ^4.0.0 - React plugin for Vite
- `typescript` ~5.9.0 - Type checking
- `vite` ^6.0.0 - Build tool
## Configuration
- `.env.local` - Backend local dev config (loaded by docker-compose)
- `.env.test` - Test environment config
- `apps/web/.env` - Frontend environment variables (VITE_* prefixed)
- Key backend env vars: `GCP_PROJECT_ID`, `FIRESTORE_DATABASE`, `AUTH_DISABLED`, `ENVIRONMENT`, `ADMIN_EMAILS`, `ORG_ID`, `TENANTS_FOLDER_ID`, `BILLING_ACCOUNT`, `CB_SOURCE_BUCKET`, `TF_BUILDER_SA`
- Key frontend env vars: `VITE_FIREBASE_API_KEY`, `VITE_GCP_PROJECT_ID`, `VITE_FIREBASE_MESSAGING_SENDER_ID`, `VITE_FIREBASE_APP_ID`
- GitHub integration env vars: `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`, `GITHUB_INSTALLATION_ID`, `GITHUB_ORG`
- `apps/web/vite.config.ts` - Vite config with React plugin, Tailwind plugin, `@/` path alias, dev proxy to backend
- `apps/web/tsconfig.json` - Strict TypeScript (ES2023 target, bundler resolution, `@/*` path alias)
- `packages/pyproject.toml` - Python project metadata, dependencies, pytest config
- `Dockerfile` - Production backend container (python:3.12-slim, uvicorn on port 8080)
- `docker-compose.yml` - Local dev: `app` (backend:8080) + `web` (frontend:5173, proxied to backend)
- `cloudbuild.yaml` - CI/CD pipeline (Docker build, push to Artifact Registry, deploy to Cloud Run, build frontend, deploy to Firebase Hosting)
- `infra/host/main.tf` - Terraform config for host project (GCS backend, Google provider ~5.0)
- `infra/host/dev.backend.hcl` / `infra/host/prod.backend.hcl` - Partial backend configs per environment
- `firebase.json` - Firebase Hosting (serves `frontend/dist`), Firestore rules, RTDB rules
- `firestore.rules` - Security rules with role-based access (owner/collaborator/viewer/editor/admin)
## Platform Requirements
- Python 3.12
- Node.js 20
- Docker and Docker Compose
- gcloud CLI configured with GCP credentials
- Git
- Google Cloud Platform:
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- PascalCase for React components: `ProjectListScreen.tsx`, `Button.tsx`, `TopBar.tsx`, `SplitPane.tsx`
- kebab-case for TypeScript utilities, hooks, stores, and libs: `api-client.ts`, `auth-store.ts`, `blueprint-store.ts`
- snake_case for Python backend modules: `authz.py`, `cloud_sql.py`, `field_resolution.py`, `secret_manager.py`
- Lowercase for Python test files: `test_validation.py`, `test_dag.py`, `test_terraform.py`
- Lowercase single-word for UI primitives: `button.tsx`, `dialog.tsx`, `input.tsx`, `select.tsx`, `tabs.tsx`
- camelCase for TypeScript: `fetchBlueprint()`, `handleCreate()`, `signInWithEmail()`, `getToken()`
- snake_case for Python: `get_current_user()`, `validate_blueprint()`, `save_project()`, `generate_terraform()`
- React event handlers prefixed with `handle`: `handleCreate`, `handleDelete`
- Async functions return explicit Promise types in TypeScript: `Promise<ApiResult<T>>`
- camelCase for TypeScript: `projectRefId`, `displayName`, `selectedNodeId`
- snake_case for Python: `tenant_id`, `project_ref_id`, `deploy_id`
- UPPER_SNAKE_CASE for constants and env vars: `MAX_BODY_SIZE`, `AUTH_DISABLED`, `ROLE_HIERARCHY`
- PascalCase for interfaces and types: `AuthState`, `BlueprintState`, `ProjectAccess`, `CurrentUser`
- `Props` suffix for component props (implicit via `ButtonPrimitive.Props & VariantProps<...>`)
- Union types defined inline: `ProvisionStatus = 'pending' | 'provisioning' | 'ready' | 'failed'`
- Python uses `@dataclass` for simple data holders: `ValidationIssue`, `FieldRequirement`, `ComponentDefinition`, `ProjectAccess`
- Pydantic `BaseModel` for validated schemas: `Envelope`, `BaseNode`, `GlobalConfig`, `CloudRunConfig`
- Zustand stores use `use` prefix: `useAuthStore`, `useBlueprintStore`, `useProjectStore`
- Store type named with `State` suffix: `AuthState`, `BlueprintState`
## Code Style
- No Prettier configuration -- code style enforced by ESLint and editor defaults
- 2-space indentation in TypeScript/JavaScript
- 4-space indentation in Python (PEP 8)
- No trailing semicolons in TypeScript (inconsistent but trending toward no-semicolons)
- Frontend (web app): No ESLint config found in `apps/web/` -- relies on tsconfig strict mode
- Product sales site: `apps/product-sales-site/eslint.config.mjs` uses `eslint-config-next/core-web-vitals` and `eslint-config-next/typescript`
- TypeScript strict mode enforced in `apps/web/tsconfig.json`:
- Python: No explicit linter config (ruff/flake8/pylint) -- uses `# noqa: N815` annotations for camelCase field names in Pydantic models
- Target: ES2023
- Module: ESNext with bundler resolution
- JSX: react-jsx (auto React import)
- Path alias: `@/*` maps to `./src/*` via tsconfig paths
## Import Organization
- `@/*` maps to `./src/*` in the web app (`apps/web/tsconfig.json` and `apps/web/vite.config.ts`)
- Named exports for utilities, stores, and shared components: `export { Button, buttonVariants }`
- Default exports for screen/page components: `export default function ProjectListScreen()`
- Zustand stores always named export: `export const useAuthStore = create<AuthState>(...)`
- Python modules use direct imports -- no `__all__` pattern observed
## Error Handling
- All API calls go through `api-client.ts` which returns `ApiResult<T>` type defined in `apps/web/src/types/api.ts`:
- Fetch errors caught with try-catch, return `{ ok: false, status: 0, error: err }`
- Non-critical JSON parse failures handled with `.catch(() => ({}))`
- Components check `res.ok` before using `res.data`
- FastAPI `HTTPException` for request-level errors:
- Structured validation responses: `{ valid: bool, issues: [...] }` for blueprint validation
- `ValidationIssue` dataclass with `severity` ("error" | "warning"), `node`, and `message` fields
- Firebase token verification in `packages/platform/auth/firebase.py`
- Role-based access via `packages/platform/auth/authz.py` -- returns 404 instead of 403 for unauthorized access
- Dev mode: `AUTH_DISABLED=true` bypasses token verification
## Logging
- Python `logging` module: `log = logging.getLogger(__name__)` at module level
- Minimal logging -- errors primarily returned via HTTP responses
- No structured logging framework (e.g., structlog)
- Browser console only: `console.log`, `console.warn`, `console.error`
- No logging framework or remote error tracking
## Comments
- Module-level docstrings describe purpose: `"""Cross-node reference & dependency validation."""`
- Function/class docstrings for public APIs: `"""FastAPI dependency factory that checks the user has at least min_role..."""`
- Inline `# noqa: N815` for intentional camelCase in Pydantic fields matching frontend JSON schema
- No JSDoc or TSDoc usage
- No section separators observed in current codebase
- Comments used sparingly for non-obvious behavior: `// Fallback: nodes may exist in subcollection...`
- Module-level docstrings describe test scope: `"""DAG topological sort, cycle detection, and parallel batch tests."""`
- Individual test methods rarely have docstrings except for complex scenarios
## Function Design
- React components: 30-140 lines (e.g., `ProjectListScreen.tsx` is 142 lines)
- Zustand stores: 30-65 lines per store file
- Utility modules: 5-35 lines (e.g., `utils.ts` is 6 lines, `api-client.ts` is 37 lines)
- Python handler functions: 10-50 lines
- Python dataclasses/models: 5-20 lines per class
- React components destructure props: `({ variant = 'default', size = 'default', className, ...props })`
- TypeScript generics for reusable API functions: `request<T>(method: string, url: string, body?: unknown): Promise<ApiResult<T>>`
- Python uses keyword arguments with type hints: `def save_project(tenant_id: str, project_data: dict) -> dict`
- FastAPI uses `Depends()` for dependency injection: `user: CurrentUser = Depends(get_current_user)`
- Zustand store actions return `Promise<boolean>` or `Promise<T | null>` for success/failure
- Python validation functions return `list[ValidationIssue]`
- FastAPI handlers return dicts (auto-serialized to JSON)
## Module Design
- Stores: one store per domain concern in `apps/web/src/stores/` -- `auth-store.ts`, `blueprint-store.ts`, `project-store.ts`
- UI components: barrel export via `apps/web/src/components/ui/` (button, dialog, input, select, tabs, table)
- Screens: one file per route in `apps/web/src/screens/`
- Lib: shared utilities in `apps/web/src/lib/` -- `api-client.ts`, `firebase.ts`, `utils.ts`
- Types: domain types in `apps/web/src/types/` -- `project.ts`, `node.ts`, `api.ts`
- Handlers by domain: `packages/api/handlers/` -- `health.py`, `nodes.py`, `pipeline.py`, `terraform.py`, `deploy.py`
- Platform services: `packages/platform/store/` -- `projects.py`, `blueprints.py`, `deploys.py`, `tenants.py`, `collaborators.py`
- Core logic: `packages/core/` -- `dag.py`, `validation.py`, `field_resolution.py`, `registry.py`
- Schemas: `packages/core/schemas/` -- `base.py`, `enums.py`, `configs/` (one file per node type)
- Terraform: `packages/core/terraform/` -- `generator.py`, `resolver.py`, `templates/*.tf.j2`
- `packages/core/schemas/configs/__init__.py` exports `TYPE_TO_CONFIG` mapping
- UI component barrel: `apps/web/src/components/ui/` (assumed from import patterns)
## State Management Pattern
- Create store with typed state: `create<AuthState>((set, get) => ({...}))`
- State and actions in same object
- Actions use `set()` for state updates, `get()` for reading current state
- Cross-store access via `useAuthStore.getState()` (e.g., in `api-client.ts` for token retrieval)
- No middleware (persist, devtools) observed
## API Client Pattern
- Single `request<T>()` function wraps all HTTP calls with auth token injection
- Exported as `api` object with methods: `api.get<T>()`, `api.post<T>()`, `api.put<T>()`, `api.patch<T>()`, `api.delete<T>()`
- Token obtained from auth store on every request
- All responses normalized to `ApiResult<T>`
- FastAPI `APIRouter()` per handler module
- Routes registered with `@router.get()`, `@router.post()`, etc.
- Auth injected via `Depends(get_current_user)`
- Project access injected via `Depends(require_project_access("editor"))`
## Pydantic Model Conventions
- `extra="allow"` on models that accept arbitrary frontend fields: `BaseNode`, `StepDetails`, `GlobalConfig`
- `Field(alias="...")` for JSON keys that conflict with Python: `global_` aliased as `"global"`, `schema_` aliased as `"$schema"`
- `model_config = {"populate_by_name": True}` to allow both alias and field name
- `@model_validator(mode="after")` for cross-field validation
- camelCase field names in models matching frontend JSON use `# noqa: N815` comment
- `@dataclass(frozen=True)` for immutable registry entries: `ComponentDefinition`
- Regular `@dataclass` for mutable result objects: `ValidationIssue`, `ProjectAccess`
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Multi-tenant isolation via Firebase Auth UID as tenant_id (Firestore path: `tenants/{uid}/...`)
- Blueprint-driven infrastructure: users design node graphs, backend generates Terraform and deploys via Cloud Build
- Each environment (dev, staging, prod) maps to a separate GCP project
- Background tasks for long-running operations (provisioning, deploy) with status tracking in Firestore
- Stateless API server -- all state lives in Firestore, enabling Cloud Run horizontal scaling
## Layers
- Purpose: Interactive workspace for project management, resource configuration, and deploy orchestration
- Location: `apps/web/src/`
- Contains: React components, Zustand stores, API client, Firebase integration
- Depends on: Firebase Auth (authentication), Firestore (real-time project doc updates), REST API (`/api/*`)
- Used by: Browser clients
- Purpose: REST endpoints for all CRUD, validation, generation, and orchestration operations
- Location: `packages/api/handlers/`
- Contains: 16 router modules, each handling a domain concern
- Key routers:
- Depends on: Core schemas, Platform services, Auth middleware
- Used by: Frontend via HTTP
- Purpose: Firebase token verification and role-based project access control
- Location: `packages/platform/auth/`
- Contains:
- Key abstraction: `CurrentUser(tenant_id, email, display_name, is_admin)` dataclass
- Key abstraction: `ProjectAccess(user, project, owner_uid)` dataclass injected by authorization
- Pattern: FastAPI `Depends()` injection -- handlers declare auth requirements declaratively
- Purpose: Blueprint data model, validation rules, Terraform generation, DAG operations
- Location: `packages/core/`
- Contains:
- Depends on: Pydantic, Jinja2, graphlib
- Used by: API handlers, deploy orchestrator
- Purpose: External integrations (GCP APIs, Firestore persistence, deploy orchestration)
- Location: `packages/platform/`
- Contains:
- Depends on: Google Cloud SDKs, Firestore
- Used by: API handlers
- Purpose: Terraform configuration for the host platform itself
- Location: `infra/host/`
- Contains: Terraform files for Cloud Run, Artifact Registry, Firebase, Firestore, IAM, org policies
- Not used at runtime -- applied manually to bootstrap the host project
## Data Flow
- Zustand stores: `useAuthStore`, `useProjectStore`, `useBlueprintStore`, `usePreviewStore`
- Auth state from Firebase `onAuthStateChanged` listener
- Project doc updates via Firestore `onSnapshot` listener (real-time)
- Blueprint/node data fetched via REST API, stored in Zustand
- API calls go through centralized `api-client.ts` which injects Bearer token from auth store
## Key Abstractions
- Purpose: Complete blueprint document -- the top-level schema for an infrastructure design
- Backend: `packages/core/schemas/base.py` class `Envelope` (Pydantic model)
- Frontend: `apps/web/src/types/node.ts` type `Blueprint.envelope`
- Structure: `{ version, global: GlobalConfig, nodes: BaseNode[], metadata }`
- GlobalConfig includes: `project_id`, `region`, `environment`, `naming_convention`, `labels`, `networking`, `backend`
- Purpose: Represents a single GCP resource in the blueprint
- Backend: `packages/core/schemas/base.py` class `BaseNode`
- Frontend: `apps/web/src/types/node.ts` type `BaseNode`
- Fields: `slug`, `name`, `type` (NodeType enum), `depends_on[]`, `inputs[]`, `outputs[]`, `iam`, `invoker_bindings`, `accessor_bindings`, `config` (polymorphic), `internalGraph` (compute types only)
- Config is polymorphic: validated by type-specific Pydantic model from `packages/core/schemas/configs/` via `TYPE_TO_CONFIG` map
- Purpose: Registry entry defining a component type's metadata and capabilities
- Location: `packages/core/registry.py` dataclass `ComponentDefinition`
- Fields: `node_type`, `label`, `category`, `is_compute`, `config_model`, `terraform_resource`, `iam_scope`, `default_outputs`
- Registry: `REGISTRY` dict maps `NodeType` -> `ComponentDefinition` for all 22 node types
- Purpose: Exhaustive enumeration of all supported GCP resource types
- Location: `packages/core/schemas/enums.py`
- Categories: Compute (cloud_run, cloud_run_job, cloud_function), Data (cloud_sql, firestore, bigquery, bigtable), Messaging (pubsub_topic, pubsub_subscription, cloud_task_queue), Network (vpc, subnet, vpc_connector, external_lb), Security (secret_manager, service_account), External (third_party_api)
- Child types: firestore_collection, bigquery_table, cloud_sql_database, cloud_sql_table
- Purpose: Authenticated user context injected into every handler
- Location: `packages/platform/auth/firebase.py`
- Fields: `tenant_id` (Firebase UID), `email`, `display_name`, `is_admin`
- Created by: `get_current_user()` FastAPI dependency
- Purpose: Authorized project context with role validation
- Location: `packages/platform/auth/authz.py`
- Fields: `user` (CurrentUser), `project` (dict), `owner_uid` (str)
- Created by: `require_project_access(min_role)` dependency factory
- Role hierarchy: viewer (0) < editor (1) < admin (2)
- Purpose: Dependency graph operations on blueprint nodes
- Location: `packages/core/dag.py`
- Methods: `topological_sort()`, `validate_ordering()`, `parallel_batches()`
- Uses: Python `graphlib.TopologicalSorter` (stdlib)
- Purpose: Structured validation error/warning for blueprint issues
- Location: `packages/core/validation.py`
- Fields: `severity` ("error" | "warning"), `node` (name or None), `message`
## Entry Points
- Location: `apps/web/src/main.tsx` -> `apps/web/src/App.tsx`
- Triggers: Browser navigation
- Responsibilities: Initialize React app with BrowserRouter, set up Firebase auth listener, route to LoginScreen (unauthenticated), ProjectListScreen (`/`), or WorkspaceScreen (`/projects/:projectRefId`)
- Location: `packages/api/main.py`
- Triggers: `uvicorn packages.api.main:app` (Dockerfile CMD)
- Responsibilities: Create FastAPI app, configure CORS + body size middleware, mount 16 routers under `/api` prefix
- Location: `apps/web/src/screens/WorkspaceScreen.tsx`
- Triggers: Route `/projects/:projectRefId`
- Responsibilities: Subscribe to Firestore project doc (real-time), gate on provisioning status, load blueprint for selected env, render SplitPane with ResourceList (left) and PreviewPanel (right)
- Location: `packages/platform/deploy_orchestrator.py` function `_run_deploy()`
- Triggers: `BackgroundTasks.add_task()` from deploy handler
- Responsibilities: Generate TF, submit Cloud Build, poll status, update Firestore
- Location: `packages/api/handlers/provision.py` function `_run_provisioning()`
- Triggers: `BackgroundTasks.add_task()` from provision endpoint
- Responsibilities: Create GCP folder hierarchy, create GCP project, enable APIs, update provision status
## Firestore Data Model
```
```
## Error Handling
- All API calls return `ApiResult<T>`: `{ ok: boolean, status: number, data?: T, error?: unknown }`
- Centralized in `apps/web/src/lib/api-client.ts` -- wraps fetch with auth token injection and error normalization
- Non-critical errors caught silently: `.catch(() => ({}))`
- Pydantic `ValidationError` -> 422 with structured error details
- Auth failures -> 401 (`Missing or invalid Authorization header` / `Invalid token`)
- Authorization failures -> 404 (avoids leaking project existence)
- Business rule violations -> 422 with descriptive messages (e.g., deploy blocked by validation errors)
- Provisioning guard -> 409 (still provisioning) or 422 (failed/not provisioned)
- Server config errors -> 500 (missing env vars like ORG_ID)
## Cross-Cutting Concerns
- Firebase Auth (email/password + Google OAuth) on frontend
- Firebase Admin SDK token verification on backend
- Dev bypass: `AUTH_DISABLED=true` + `ENVIRONMENT=dev` returns hardcoded `_DEV_USER`
- Token passed as `Authorization: Bearer {token}` header (SSE uses `?token=` query param)
- Role-based: viewer < editor < admin
- Enforced via `require_project_access(min_role)` FastAPI dependency
- Owner always has full access; global admins (`is_admin` flag) bypass role checks
- Collaborator roles stored in project doc `collaborators` map
- Firestore security rules mirror backend authorization for direct client reads
- Isolation key: Firebase UID as `tenant_id`
- All Firestore data scoped under `tenants/{tenant_id}/`
- Shared projects via `shared_projects` index collection
- Each environment is a separate GCP project: `{env}-{internal_project_id}`
- Frontend subscribes to Firestore project doc via `onSnapshot` for provisioning status
- Validation results persisted to `blueprints/{env}/validation/current` for frontend subscription
- SSE endpoint for Cloud Build log streaming during deploys
- Schema validation: Pydantic models enforce structure at API boundary
- Business validation: `packages/core/validation.py` checks cross-node references, required fields, naming, dependency graph
- Validation runs on every node CRUD operation and results are persisted to Firestore
- Deploy gated on zero validation errors
- Backend: Python `logging` module, `log = logging.getLogger(__name__)` pattern
- Frontend: `console.log/warn/error` (no structured logging)
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
