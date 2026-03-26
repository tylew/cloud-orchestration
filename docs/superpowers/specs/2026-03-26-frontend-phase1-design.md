# Frontend Phase 1: Developer Operations Dashboard

**Date:** 2026-03-26
**Status:** Draft
**Scope:** `apps/web/` — new React frontend application

## Problem

The backend API has 60+ endpoints covering project management, blueprint CRUD, Terraform generation, container builds, deploy orchestration, and environment management. There is no frontend. The developer has no birds-eye view into the system — no way to see what's in Firestore, inspect generated Terraform, watch build logs, or verify validation without direct API calls.

## Goals

1. A developer operations dashboard that provides full visibility into the platform: resources, Terraform output, build logs, validation state, deploy status.
2. Direct control: configure resources, trigger deploys, build containers — transparent at every step.
3. Basic environment management: add environments, see provision status, promote blueprints.
4. Not a polished end-user product — a functional developer tool for testing and operating the platform.

## Non-Goals

- End-user authentication or onboarding (using `AUTH_DISABLED=true` dev bypass)
- Visual node graph editor (@xyflow/react canvas — Phase 2)
- Secrets management UI (Phase 3)
- Code editor for compute nodes (Phase 3)
- Collaborator management (Phase 3)
- Real-time collaboration / Firestore listeners (Phase 2)
- Polished UX or error recovery flows — functional over pretty

---

## Design

### 1. Tech Stack

- **React 19** with TypeScript 5.9
- **Vite 8** for dev server and builds
- **Tailwind CSS 4** for styling
- **shadcn/ui** for form components (Button, Input, Tabs, Dialog, Select, Table)
- **Zustand** for state management
- **React Router DOM 7** for client-side routing
- Vite dev server proxies `/api/*` to `http://localhost:8080` (FastAPI backend)

### 2. Key Concepts

**`project_ref_id`** vs **`project_id`**: The `project_ref_id` is the Firestore document ID (auto-generated, used in all API routes). The `project_id` is the GCP project identifier provided at creation time (e.g., `my-super-cool-app-dev-3f74d0`). The frontend routes use `project_ref_id`.

### 3. Routing

| Route | Screen | Purpose |
|-------|--------|---------|
| `/` | ProjectListScreen | Table of projects with create button |
| `/projects/:projectRefId` | WorkspaceScreen | Split-pane: resource list + preview |
| `/projects/:projectRefId/resources/:slug` | WorkspaceScreen (drill-in) | Resource config form replaces left pane |

Environment selection is a dropdown in the top bar (not a route parameter). Changing env reloads the blueprint for that environment.

### 4. Layout: Split Pane

The workspace uses a split-pane layout:

- **Left pane**: Resource list (default) or resource config (drill-in)
- **Right pane**: Preview panel with tabs — Terraform, Build Log, Validation
- Project name, env selector, and Deploy button in a top bar

### 5. Left Pane — Resource List

**Resource List view (default):**
- Header with "Resources" label and node count badge
- "+ Add Resource" button opens a modal with the resource palette
- Each resource row: type color indicator, name, type label, validation status (green check / red dot)
- Click a resource → navigates to `/projects/:id/resources/:slug`, replacing the left pane with config

**Resource Palette (modal):**
Hardcoded categories from the backend registry:
- **Compute**: Cloud Run, Cloud Run Job, Cloud Function
- **Network**: VPC, Subnet, VPC Connector, External LB
- **Storage**: Firestore, Cloud SQL, GCS Bucket, BigQuery, Bigtable
- **Messaging**: Pub/Sub Topic, Pub/Sub Subscription, Cloud Tasks
- **Security**: Service Account, Secret Manager

Clicking a type: POST to nodes API with defaults → refresh blueprint store → navigate to config.

### 6. Left Pane — Resource Config (Drill-In)

Clicking a resource replaces the left pane with a full-width config form.

**Layout:**
- Breadcrumb: `← Resources › {name} ({type})`
- Config fields organized in sections (Basic, Scaling, Env Vars, Networking, etc.)
- Auto-save on field blur (debounced PATCH to nodes API)
- "Delete Resource" button at bottom with confirmation dialog

**Env Vars section (compute nodes only):**
- Unified list matching the `EnvVarEntry` model
- Each row: name input, type toggle (value/secret), value-or-secret-ref input, delete button
- "+ Add Env Var" button

**Dependencies section:**
- Pill tags showing current `depends_on` nodes
- "+ add" button to select from existing nodes

**Per-type config forms:**
- Complex types get dedicated forms: `CloudRunForm`, `CloudFunctionForm`, `CloudRunJobForm`
- Simple types use `GenericForm` — renders fields dynamically from the config object
- All forms share common sections (env vars, dependencies) via shared components
- Phase 1 covers the most common fields per type (image, port, CPU, memory, scaling, env vars, service account). Remaining fields added iteratively.

**Primary write path**: Per-node CRUD (`POST/PATCH/DELETE` on `/nodes/{slug}`) is the only write path in Phase 1. The full-envelope `PUT /projects/{ref}/envs/{env}/blueprint` is not used for editing — it exists for import scenarios only.

### 7. Right Pane — Preview Panel

Three tabs: **Terraform** | **Build Log** | **Validation**

**Auto-switch logic:**
- Default: Terraform tab
- When deploy starts: auto-switch to Build Log
- Validation tab shows red badge with error count when issues exist (no auto-switch)
- Developer can manually switch tabs at any time

**Terraform tab:**
- Syntax-highlighted HCL in a `<pre>` block with keyword coloring
- File tabs for multiple generated files (provider.tf, main.tf, variables.tf, backend.tf)
- Generated via `POST /api/terraform/generate` with the full envelope as body
- The envelope is assembled by: fetching `GET /api/projects/{ref}/envs/{env}/blueprint` (returns the full envelope with nodes reassembled) and passing it through to the generate endpoint. No client-side envelope reconstruction needed.

**Build Log tab:**
- Real-time SSE stream from `GET /api/projects/{ref}/deploys/{id}/logs/stream`
- Timestamped log lines with auto-scroll
- Status banner: "Building..." (blue) → "Success" (green) / "Failed" (red)

**Validation tab:**
- Issues grouped by node, each with severity icon (error/warning) and message
- Click an issue → navigates to that resource's config
- "No issues" state with green checkmark when blueprint validates

### 8. Deploy & Build Flow

**Deploy button** in the top bar. Disabled when validation errors exist or env is not provisioned.

**Deploy flow:**
1. POST `/api/projects/{ref}/envs/{env}/deploy`
2. Right pane auto-switches to Build Log tab
3. SSE connection streams Cloud Build output
4. Status banner updates as deploy progresses

**Deploy steps visible in UI:**

| Backend Step | UI Indicator |
|-------------|-------------|
| Generating TF | Spinner + "Generating Terraform..." |
| Submitting Cloud Build | "Submitting to Cloud Build..." |
| Building/Applying | Live log stream line by line |
| Success | Green banner, env marked deployed |
| Failed | Red banner, error in log, plan/apply output |

**Container builds (compute nodes):**
- In resource config for compute nodes, a "Build Image" button is available
- Note: `POST /api/pipeline/build-image` is currently a stub that returns simulated output. Phase 1 wires up the UI to this endpoint. Real Cloud Build integration for image builds is tracked separately.

### 9. Environment Management

**Env selector** in the top bar dropdown:
- Lists all environments with status badges: provisioning (yellow), ready (green), deployed (blue), failed (red)
- "Add Environment" option at bottom → name input → triggers `POST /api/projects/{ref}/envs` → shows provisioning state
- Changing env reloads the blueprint for that env

**Promotion:**
- When viewing an env that has no blueprint, show a "Promote from {source_env}" button
- Triggers `POST /api/projects/{ref}/envs/{target}/promote` with `{"source_env": "..."}` body
- After promotion, reloads the promoted blueprint

Note: The old promotion endpoint in `blueprints.py` (source in URL, target in body) has been removed. The canonical endpoint is in `promote.py` (target in URL, source in body).

### 10. Project List Screen

**Simple table** at `/`:
- Columns: Name, Project ID, Region, Environments (badges), Actions
- "Create Project" button → dialog with project_id (GCP project ID), display_name, region → POST `/api/projects`
- Click project row → navigate to workspace
- Delete button per row with confirmation

### 11. State Management

**Zustand stores:**

| Store | State | Key Actions |
|-------|-------|------------|
| `useProjectStore` | projects list, current project, selected env | `fetchProjects`, `createProject`, `selectEnv`, `addEnvironment` |
| `useBlueprintStore` | nodes list, selected node slug, dirty flag | `fetchBlueprint`, `addNode`, `updateNode`, `deleteNode` |
| `useDeployStore` | active deploy, build logs, SSE connection | `startDeploy`, `connectSSE`, `fetchDeployStatus` |
| `usePreviewStore` | active tab, TF files, validation issues | `setTab`, `fetchTerraform`, `fetchValidation`, `autoSwitch` |

### 12. API Client

Thin `fetch` wrapper returning `ApiResult<T>`:

```typescript
type ApiResult<T> = {
  ok: boolean
  status: number
  data?: T
  error?: any
}
```

All requests to `/api/*`. Vite dev proxy handles routing to backend. No auth headers in Phase 1 (dev bypass).

### 13. Loading & Error States

**Loading:** Spinner overlay for screen transitions (project load, env switch). Inline spinners for in-place operations (TF generation, node save).

**Errors:** Toast notifications for failed API calls. HTTP status mapping:

| Status | UI Behavior |
|--------|------------|
| 404 | "Not found" toast, redirect to project list if project missing |
| 409 | "Environment still provisioning" inline message |
| 422 | Inline validation error on the field/form that failed |
| 500 | "Server error" toast with detail message |

No retry logic in Phase 1 — developer can refresh or retry manually.

---

## File Structure

```
apps/web/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── lib/
│   │   └── api-client.ts
│   ├── stores/
│   │   ├── project-store.ts
│   │   ├── blueprint-store.ts
│   │   ├── deploy-store.ts
│   │   └── preview-store.ts
│   ├── screens/
│   │   ├── ProjectListScreen.tsx
│   │   └── WorkspaceScreen.tsx
│   ├── components/
│   │   ├── layout/
│   │   │   ├── TopBar.tsx
│   │   │   └── SplitPane.tsx
│   │   ├── resources/
│   │   │   ├── ResourceList.tsx
│   │   │   ├── ResourcePalette.tsx
│   │   │   ├── ResourceConfig.tsx
│   │   │   └── configs/
│   │   │       ├── CloudRunForm.tsx
│   │   │       ├── CloudFunctionForm.tsx
│   │   │       ├── CloudRunJobForm.tsx
│   │   │       └── GenericForm.tsx
│   │   ├── preview/
│   │   │   ├── PreviewPanel.tsx
│   │   │   ├── TerraformView.tsx
│   │   │   ├── BuildLogView.tsx
│   │   │   └── ValidationView.tsx
│   │   └── ui/                     # shadcn components
│   └── types/
│       ├── project.ts
│       ├── node.ts
│       └── api.ts
```

---

## API Endpoints Used

| Endpoint | Used By |
|----------|---------|
| `GET /api/projects` | ProjectListScreen |
| `POST /api/projects` | ProjectListScreen (create) |
| `GET /api/projects/{ref}` | WorkspaceScreen (load) |
| `DELETE /api/projects/{ref}` | ProjectListScreen |
| `POST /api/projects/{ref}/envs` | TopBar (add env) |
| `GET /api/projects/{ref}/envs/{env}/blueprint` | WorkspaceScreen (load blueprint, also used for TF generation input) |
| `GET /api/projects/{ref}/envs/{env}/nodes` | ResourceList |
| `POST /api/projects/{ref}/envs/{env}/nodes` | ResourcePalette (add) |
| `PATCH /api/projects/{ref}/envs/{env}/nodes/{slug}` | ResourceConfig (auto-save) |
| `DELETE /api/projects/{ref}/envs/{env}/nodes/{slug}` | ResourceConfig (delete) |
| `POST /api/terraform/generate` | TerraformView (envelope body from blueprint GET) |
| `POST /api/blueprints/validate` | ValidationView |
| `POST /api/projects/{ref}/envs/{env}/deploy` | TopBar (deploy) |
| `GET /api/projects/{ref}/deploys/{id}/status` | DeployStore (poll) |
| `GET /api/projects/{ref}/deploys/{id}/logs/stream` | BuildLogView (SSE) |
| `POST /api/projects/{ref}/envs/{target}/promote` | TopBar (promote, body: `{"source_env": "..."}`) |
| `POST /api/pipeline/build-image` | CloudRunForm (stub in Phase 1) |

---

## Backend Changes Required

1. **Removed**: Old promote endpoint in `blueprints.py` (source in URL, target in body) — superseded by `promote.py` (target in URL, source in body). Already removed.

---

## Risks

- **Config form completeness**: Cloud Run has ~30 config fields. Phase 1 covers common ones (image, port, CPU, memory, scaling, env vars, service account). Remaining fields added iteratively.
- **SSE reliability**: EventSource API doesn't support auth headers. The backend handles this via query param token. In dev mode with auth disabled, no token needed.
- **Auto-save conflicts**: Debounced auto-save could race with deploy. The deploy button should await any pending saves before triggering.
- **Build-image stub**: `POST /api/pipeline/build-image` returns simulated output. Real container builds need separate backend work.
