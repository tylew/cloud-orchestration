# Frontend Phase 1A: Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold the React frontend app, wire up API client and stores, build the project list screen, workspace shell with split pane, resource list with palette, and the Terraform preview panel. End state: developer can create a project, add resources, and see generated Terraform.

**Architecture:** Vite + React SPA at `apps/web/`. Zustand stores for state, thin fetch wrapper for API calls. Vite dev proxy forwards `/api/*` to FastAPI backend at `localhost:8080`. Split-pane workspace layout with resource list on left and TF preview on right.

**Tech Stack:** React 19, TypeScript 5.9, Vite 8, Tailwind CSS 4, shadcn/ui, Zustand, React Router DOM 7

**Spec:** `docs/superpowers/specs/2026-03-26-frontend-phase1-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `apps/web/package.json` | Create | Dependencies and scripts |
| `apps/web/index.html` | Create | HTML entry point |
| `apps/web/tsconfig.json` | Create | TypeScript config |
| `apps/web/vite.config.ts` | Create | Vite + Tailwind + proxy config |
| `apps/web/src/main.tsx` | Create | React entry point |
| `apps/web/src/App.tsx` | Create | Router setup |
| `apps/web/src/app.css` | Create | Tailwind imports |
| `apps/web/src/lib/api-client.ts` | Create | Fetch wrapper returning ApiResult<T> |
| `apps/web/src/lib/utils.ts` | Create | cn() helper for shadcn |
| `apps/web/src/types/api.ts` | Create | ApiResult type |
| `apps/web/src/types/project.ts` | Create | Project, Environment types |
| `apps/web/src/types/node.ts` | Create | BaseNode, EnvVarEntry, node config types |
| `apps/web/src/stores/project-store.ts` | Create | Projects list, current project, selected env |
| `apps/web/src/stores/blueprint-store.ts` | Create | Nodes list, CRUD operations |
| `apps/web/src/stores/preview-store.ts` | Create | Active tab, TF files, validation issues |
| `apps/web/src/screens/ProjectListScreen.tsx` | Create | Project table + create dialog |
| `apps/web/src/screens/WorkspaceScreen.tsx` | Create | Split-pane shell, loads project + blueprint |
| `apps/web/src/components/layout/TopBar.tsx` | Create | Project name, env selector, deploy button |
| `apps/web/src/components/layout/SplitPane.tsx` | Create | Resizable left/right layout |
| `apps/web/src/components/resources/ResourceList.tsx` | Create | Node list with validation indicators |
| `apps/web/src/components/resources/ResourcePalette.tsx` | Create | Categorized type picker dialog |
| `apps/web/src/components/preview/PreviewPanel.tsx` | Create | Tab container for right pane |
| `apps/web/src/components/preview/TerraformView.tsx` | Create | HCL display with file tabs |
| `apps/web/src/components/ui/*` | Create | shadcn components (installed via CLI) |

---

### Task 1: Scaffold Vite + React + Tailwind + shadcn

**Files:**
- Create: `apps/web/package.json`
- Create: `apps/web/index.html`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/vite.config.ts`
- Create: `apps/web/src/main.tsx`
- Create: `apps/web/src/App.tsx`
- Create: `apps/web/src/app.css`
- Create: `apps/web/src/lib/utils.ts`
- Create: `apps/web/components.json`

- [ ] **Step 1: Create package.json**

```json
{
  "name": "gcp-orchestration-web",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router-dom": "^7.0.0",
    "zustand": "^5.0.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^3.0.0"
  },
  "devDependencies": {
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.0.0",
    "typescript": "~5.9.0",
    "vite": "^6.0.0",
    "@tailwindcss/vite": "^4.0.0",
    "tailwindcss": "^4.0.0"
  }
}
```

- [ ] **Step 2: Create index.html**

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>GCP Orchestration</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 3: Create tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2023",
    "lib": ["ES2023", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "paths": {
      "@/*": ["./src/*"]
    },
    "baseUrl": "."
  },
  "include": ["src"]
}
```

- [ ] **Step 4: Create vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 5: Create app.css**

```css
@import "tailwindcss";
```

- [ ] **Step 6: Create src/lib/utils.ts**

```typescript
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

- [ ] **Step 7: Create src/main.tsx**

```typescript
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './app.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
)
```

- [ ] **Step 8: Create src/App.tsx**

```typescript
import { Routes, Route } from 'react-router-dom'

function Placeholder({ name }: { name: string }) {
  return <div className="p-8 text-zinc-400">{name} — coming soon</div>
}

export default function App() {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <Routes>
        <Route path="/" element={<Placeholder name="Project List" />} />
        <Route path="/projects/:projectRefId" element={<Placeholder name="Workspace" />} />
        <Route path="/projects/:projectRefId/resources/:slug" element={<Placeholder name="Resource Config" />} />
      </Routes>
    </div>
  )
}
```

- [ ] **Step 9: Install dependencies and verify**

```bash
cd apps/web && npm install
```

- [ ] **Step 10: Install shadcn/ui and core components**

```bash
cd apps/web && npx shadcn@latest init -y
cd apps/web && npx shadcn@latest add button input dialog select tabs table
```

Note: If shadcn init asks questions, choose: New York style, Zinc color, CSS variables yes.

- [ ] **Step 11: Start dev server and verify**

```bash
cd apps/web && npm run dev
```

Open `http://localhost:5173` — should see "Project List — coming soon" on a dark background.

- [ ] **Step 12: Commit**

```bash
git add apps/web/
git commit -m "feat: scaffold Vite + React + Tailwind + shadcn frontend app"
```

---

### Task 2: API Client and Types

**Files:**
- Create: `apps/web/src/types/api.ts`
- Create: `apps/web/src/types/project.ts`
- Create: `apps/web/src/types/node.ts`
- Create: `apps/web/src/lib/api-client.ts`

- [ ] **Step 1: Create types/api.ts**

```typescript
export type ApiResult<T> = {
  ok: boolean
  status: number
  data?: T
  error?: unknown
}
```

- [ ] **Step 2: Create types/project.ts**

```typescript
export type ProvisionStatus = 'pending' | 'provisioning' | 'ready' | 'failed'

export type Environment = {
  id: string
  name: string
  order: number
  deployed: boolean
  deployed_at: string | null
  gcp_project_id: string
  tf_bucket: string
  region: string
  provision_status: ProvisionStatus
  provision_id: string
}

export type Project = {
  id: string
  project_id: string
  display_name: string
  region: string
  environments: Environment[]
  owner_uid: string
  created_at: string
  updated_at?: string
}
```

- [ ] **Step 3: Create types/node.ts**

```typescript
export type EnvVarEntry = {
  name: string
  type: 'value' | 'secret'
  value?: string | null
  secret?: string | null
  version?: string
}

export type BaseNode = {
  slug: string
  name: string
  type: string
  depends_on?: string[]
  config: Record<string, unknown>
  env_vars?: EnvVarEntry[]
}

export type Blueprint = {
  env: string
  envelope: {
    version: string
    global: {
      project_id: string
      region: string
      environment: string
    }
    nodes: BaseNode[]
  } | null
}
```

- [ ] **Step 4: Create lib/api-client.ts**

```typescript
import type { ApiResult } from '@/types/api'

async function request<T>(method: string, url: string, body?: unknown): Promise<ApiResult<T>> {
  try {
    const res = await fetch(url, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
      return { ok: false, status: res.status, error: data }
    }
    return { ok: true, status: res.status, data: data as T }
  } catch (err) {
    return { ok: false, status: 0, error: err }
  }
}

export const api = {
  get: <T>(url: string) => request<T>('GET', url),
  post: <T>(url: string, body?: unknown) => request<T>('POST', url, body),
  put: <T>(url: string, body?: unknown) => request<T>('PUT', url, body),
  patch: <T>(url: string, body?: unknown) => request<T>('PATCH', url, body),
  delete: <T>(url: string) => request<T>('DELETE', url),
}
```

- [ ] **Step 5: Verify it compiles**

```bash
cd apps/web && npx tsc --noEmit
```

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/types/ apps/web/src/lib/api-client.ts
git commit -m "feat: add API client, project/node/api types"
```

---

### Task 3: Zustand Stores

**Files:**
- Create: `apps/web/src/stores/project-store.ts`
- Create: `apps/web/src/stores/blueprint-store.ts`
- Create: `apps/web/src/stores/preview-store.ts`

- [ ] **Step 1: Create stores/project-store.ts**

```typescript
import { create } from 'zustand'
import { api } from '@/lib/api-client'
import type { Project } from '@/types/project'

type ProjectState = {
  projects: Project[]
  currentProject: Project | null
  selectedEnv: string
  loading: boolean
  fetchProjects: () => Promise<void>
  createProject: (data: { project_id: string; display_name: string; region: string; environments?: unknown[] }) => Promise<Project | null>
  loadProject: (projectRefId: string) => Promise<void>
  selectEnv: (envName: string) => void
  deleteProject: (projectRefId: string) => Promise<boolean>
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  projects: [],
  currentProject: null,
  selectedEnv: '',
  loading: false,

  fetchProjects: async () => {
    set({ loading: true })
    const res = await api.get<Project[]>('/api/projects')
    if (res.ok && res.data) {
      set({ projects: res.data, loading: false })
    } else {
      set({ loading: false })
    }
  },

  createProject: async (data) => {
    const res = await api.post<Project>('/api/projects', data)
    if (res.ok && res.data) {
      await get().fetchProjects()
      return res.data
    }
    return null
  },

  loadProject: async (projectRefId) => {
    set({ loading: true })
    const res = await api.get<Project>(`/api/projects/${projectRefId}`)
    if (res.ok && res.data) {
      const project = res.data
      const envs = project.environments || []
      const firstEnv = envs.length > 0 && typeof envs[0] === 'object' ? envs[0].name : 'dev'
      set({ currentProject: project, selectedEnv: firstEnv, loading: false })
    } else {
      set({ loading: false })
    }
  },

  selectEnv: (envName) => set({ selectedEnv: envName }),

  deleteProject: async (projectRefId) => {
    const res = await api.delete(`/api/projects/${projectRefId}`)
    if (res.ok) {
      await get().fetchProjects()
      return true
    }
    return false
  },
}))
```

- [ ] **Step 2: Create stores/blueprint-store.ts**

```typescript
import { create } from 'zustand'
import { api } from '@/lib/api-client'
import type { BaseNode, Blueprint } from '@/types/node'

type BlueprintState = {
  nodes: BaseNode[]
  loading: boolean
  envelope: Blueprint['envelope']
  fetchBlueprint: (projectRefId: string, envName: string) => Promise<void>
  addNode: (projectRefId: string, envName: string, nodeData: { name: string; type: string; config?: Record<string, unknown> }) => Promise<BaseNode | null>
  updateNode: (projectRefId: string, envName: string, slug: string, updates: Partial<BaseNode>) => Promise<boolean>
  deleteNode: (projectRefId: string, envName: string, slug: string) => Promise<boolean>
}

export const useBlueprintStore = create<BlueprintState>((set, get) => ({
  nodes: [],
  loading: false,
  envelope: null,

  fetchBlueprint: async (projectRefId, envName) => {
    set({ loading: true })
    const res = await api.get<Blueprint>(`/api/projects/${projectRefId}/envs/${envName}/blueprint`)
    if (res.ok && res.data?.envelope) {
      const nodes = res.data.envelope.nodes || []
      set({ nodes, envelope: res.data.envelope, loading: false })
    } else {
      // Fallback: nodes may exist in subcollection without parent blueprint doc
      // (happens when nodes are added via the nodes API before a full blueprint save)
      const nodesRes = await api.get<{ nodes: BaseNode[] }>(
        `/api/projects/${projectRefId}/envs/${envName}/nodes`
      )
      const nodes = nodesRes.ok && nodesRes.data ? nodesRes.data.nodes : []
      set({ nodes, envelope: null, loading: false })
    }
  },

  addNode: async (projectRefId, envName, nodeData) => {
    const res = await api.post<{ node: BaseNode; validation: unknown }>(`/api/projects/${projectRefId}/envs/${envName}/nodes`, nodeData)
    if (res.ok && res.data) {
      await get().fetchBlueprint(projectRefId, envName)
      return res.data.node
    }
    return null
  },

  updateNode: async (projectRefId, envName, slug, updates) => {
    const res = await api.patch(`/api/projects/${projectRefId}/envs/${envName}/nodes/${slug}`, updates)
    if (res.ok) {
      await get().fetchBlueprint(projectRefId, envName)
      return true
    }
    return false
  },

  deleteNode: async (projectRefId, envName, slug) => {
    const res = await api.delete(`/api/projects/${projectRefId}/envs/${envName}/nodes/${slug}`)
    if (res.ok) {
      await get().fetchBlueprint(projectRefId, envName)
      return true
    }
    return false
  },
}))
```

- [ ] **Step 3: Create stores/preview-store.ts**

```typescript
import { create } from 'zustand'
import { api } from '@/lib/api-client'

type PreviewTab = 'terraform' | 'build-log' | 'validation'

type ValidationIssue = {
  severity: string
  node: string
  message: string
}

type PreviewState = {
  activeTab: PreviewTab
  tfFiles: Record<string, string>
  tfLoading: boolean
  validationIssues: ValidationIssue[]
  setTab: (tab: PreviewTab) => void
  fetchTerraform: (envelope: unknown) => Promise<void>
  fetchValidation: (envelope: unknown) => Promise<void>
  autoSwitch: (tab: PreviewTab) => void
}

export const usePreviewStore = create<PreviewState>((set) => ({
  activeTab: 'terraform',
  tfFiles: {},
  tfLoading: false,
  validationIssues: [],

  setTab: (tab) => set({ activeTab: tab }),

  fetchTerraform: async (envelope) => {
    set({ tfLoading: true })
    const res = await api.post<{ files: Record<string, string> }>('/api/terraform/generate', envelope)
    if (res.ok && res.data) {
      set({ tfFiles: res.data.files, tfLoading: false })
    } else {
      set({ tfFiles: {}, tfLoading: false })
    }
  },

  fetchValidation: async (envelope) => {
    const res = await api.post<{ issues: ValidationIssue[] }>('/api/blueprints/validate', envelope)
    if (res.ok && res.data) {
      set({ validationIssues: res.data.issues || [] })
    }
  },

  autoSwitch: (tab) => set({ activeTab: tab }),
}))
```

- [ ] **Step 4: Verify it compiles**

```bash
cd apps/web && npx tsc --noEmit
```

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/stores/
git commit -m "feat: add Zustand stores for projects, blueprint, and preview"
```

---

### Task 4: Project List Screen

**Files:**
- Create: `apps/web/src/screens/ProjectListScreen.tsx`
- Modify: `apps/web/src/App.tsx`

- [ ] **Step 1: Create ProjectListScreen.tsx**

```typescript
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useProjectStore } from '@/stores/project-store'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'

export default function ProjectListScreen() {
  const { projects, loading, fetchProjects, createProject, deleteProject } = useProjectStore()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ project_id: '', display_name: '', region: 'us-central1' })

  useEffect(() => {
    fetchProjects()
  }, [fetchProjects])

  const handleCreate = async () => {
    const result = await createProject(form)
    if (result) {
      setOpen(false)
      setForm({ project_id: '', display_name: '', region: 'us-central1' })
      navigate(`/projects/${result.id}`)
    }
  }

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    if (confirm('Delete this project?')) {
      await deleteProject(id)
    }
  }

  return (
    <div className="max-w-5xl mx-auto p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Projects</h1>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button>Create Project</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Project</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 mt-4">
              <div>
                <label className="text-sm text-zinc-400">GCP Project ID</label>
                <Input
                  value={form.project_id}
                  onChange={(e) => setForm({ ...form, project_id: e.target.value })}
                  placeholder="my-gcp-project-id"
                />
              </div>
              <div>
                <label className="text-sm text-zinc-400">Display Name</label>
                <Input
                  value={form.display_name}
                  onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                  placeholder="My Project"
                />
              </div>
              <div>
                <label className="text-sm text-zinc-400">Region</label>
                <Input
                  value={form.region}
                  onChange={(e) => setForm({ ...form, region: e.target.value })}
                  placeholder="us-central1"
                />
              </div>
              <Button onClick={handleCreate} className="w-full">Create</Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {loading ? (
        <div className="text-zinc-500">Loading...</div>
      ) : projects.length === 0 ? (
        <div className="text-zinc-500">No projects yet. Create one to get started.</div>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-800 text-zinc-400 text-left">
              <th className="pb-3 font-medium">Name</th>
              <th className="pb-3 font-medium">Project ID</th>
              <th className="pb-3 font-medium">Region</th>
              <th className="pb-3 font-medium">Environments</th>
              <th className="pb-3 font-medium w-20"></th>
            </tr>
          </thead>
          <tbody>
            {projects.map((p) => (
              <tr
                key={p.id}
                className="border-b border-zinc-800/50 hover:bg-zinc-900 cursor-pointer"
                onClick={() => navigate(`/projects/${p.id}`)}
              >
                <td className="py-3 font-medium">{p.display_name}</td>
                <td className="py-3 text-zinc-400 font-mono text-xs">{p.project_id}</td>
                <td className="py-3 text-zinc-400">{p.region}</td>
                <td className="py-3">
                  <div className="flex gap-1.5">
                    {(p.environments || []).map((env) => (
                      <span
                        key={typeof env === 'string' ? env : env.name}
                        className="px-2 py-0.5 rounded text-xs bg-zinc-800 text-zinc-300"
                      >
                        {typeof env === 'string' ? env : env.name}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="py-3">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-zinc-500 hover:text-red-400"
                    onClick={(e) => handleDelete(e, p.id)}
                  >
                    Delete
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Update App.tsx to use real screens**

```typescript
import { Routes, Route } from 'react-router-dom'
import ProjectListScreen from '@/screens/ProjectListScreen'

function Placeholder({ name }: { name: string }) {
  return <div className="p-8 text-zinc-400">{name} — coming soon</div>
}

export default function App() {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <Routes>
        <Route path="/" element={<ProjectListScreen />} />
        <Route path="/projects/:projectRefId" element={<Placeholder name="Workspace" />} />
        <Route path="/projects/:projectRefId/resources/:slug" element={<Placeholder name="Resource Config" />} />
      </Routes>
    </div>
  )
}
```

- [ ] **Step 3: Verify it renders**

```bash
cd apps/web && npm run dev
```

Open `http://localhost:5173`. With the backend running (`AUTH_DISABLED=true`), you should see the project table. If no backend, the page loads with "No projects yet."

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/screens/ProjectListScreen.tsx apps/web/src/App.tsx
git commit -m "feat: add project list screen with create/delete"
```

---

### Task 5: Layout Components — TopBar and SplitPane

**Files:**
- Create: `apps/web/src/components/layout/TopBar.tsx`
- Create: `apps/web/src/components/layout/SplitPane.tsx`

- [ ] **Step 1: Create TopBar.tsx**

```typescript
import { useNavigate } from 'react-router-dom'
import { useProjectStore } from '@/stores/project-store'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { Environment } from '@/types/project'

export default function TopBar() {
  const navigate = useNavigate()
  const { currentProject, selectedEnv, selectEnv } = useProjectStore()

  if (!currentProject) return null

  const envs: Environment[] = (currentProject.environments || []).filter(
    (e): e is Environment => typeof e === 'object'
  )

  const envStatusColor = (env: Environment) => {
    if (env.deployed) return 'text-blue-400'
    if (env.provision_status === 'ready') return 'text-green-400'
    if (env.provision_status === 'provisioning') return 'text-yellow-400'
    if (env.provision_status === 'failed') return 'text-red-400'
    return 'text-zinc-400'
  }

  return (
    <div className="h-12 border-b border-zinc-800 bg-zinc-900 flex items-center justify-between px-4">
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate('/')}
          className="text-zinc-500 hover:text-zinc-300 text-sm"
        >
          ← Projects
        </button>
        <span className="text-zinc-600">|</span>
        <span className="font-semibold text-sm">{currentProject.display_name}</span>
        <Select value={selectedEnv} onValueChange={selectEnv}>
          <SelectTrigger className="w-32 h-8 text-xs bg-zinc-800 border-zinc-700">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {envs.map((env) => (
              <SelectItem key={env.id} value={env.name}>
                <span className={envStatusColor(env)}>●</span> {env.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="flex items-center gap-2">
        <Button size="sm">Deploy</Button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create SplitPane.tsx**

```typescript
import { useState, useCallback } from 'react'

type SplitPaneProps = {
  left: React.ReactNode
  right: React.ReactNode
  defaultLeftWidth?: number
}

export default function SplitPane({ left, right, defaultLeftWidth = 50 }: SplitPaneProps) {
  const [leftWidth, setLeftWidth] = useState(defaultLeftWidth)
  const [dragging, setDragging] = useState(false)

  const handleMouseDown = useCallback(() => {
    setDragging(true)
    const handleMouseMove = (e: MouseEvent) => {
      const pct = (e.clientX / window.innerWidth) * 100
      setLeftWidth(Math.min(Math.max(pct, 25), 75))
    }
    const handleMouseUp = () => {
      setDragging(false)
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }, [])

  return (
    <div className="flex h-full">
      <div style={{ width: `${leftWidth}%` }} className="overflow-auto">
        {left}
      </div>
      <div
        className={`w-1 cursor-col-resize hover:bg-blue-500/50 ${dragging ? 'bg-blue-500/50' : 'bg-zinc-800'}`}
        onMouseDown={handleMouseDown}
      />
      <div style={{ width: `${100 - leftWidth}%` }} className="overflow-auto">
        {right}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Verify it compiles**

```bash
cd apps/web && npx tsc --noEmit
```

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/components/layout/
git commit -m "feat: add TopBar and SplitPane layout components"
```

---

### Task 6: Workspace Screen Shell

**Files:**
- Create: `apps/web/src/screens/WorkspaceScreen.tsx`
- Modify: `apps/web/src/App.tsx`

- [ ] **Step 1: Create WorkspaceScreen.tsx**

```typescript
import { useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useProjectStore } from '@/stores/project-store'
import { useBlueprintStore } from '@/stores/blueprint-store'
import TopBar from '@/components/layout/TopBar'
import SplitPane from '@/components/layout/SplitPane'

export default function WorkspaceScreen() {
  const { projectRefId } = useParams<{ projectRefId: string }>()
  const { currentProject, selectedEnv, loadProject } = useProjectStore()
  const { fetchBlueprint, loading: blueprintLoading } = useBlueprintStore()

  useEffect(() => {
    if (projectRefId) {
      loadProject(projectRefId)
    }
  }, [projectRefId, loadProject])

  useEffect(() => {
    if (projectRefId && selectedEnv) {
      fetchBlueprint(projectRefId, selectedEnv)
    }
  }, [projectRefId, selectedEnv, fetchBlueprint])

  if (!currentProject) {
    return <div className="p-8 text-zinc-500">Loading project...</div>
  }

  return (
    <div className="h-screen flex flex-col">
      <TopBar />
      <div className="flex-1 overflow-hidden">
        <SplitPane
          left={
            <div className="p-4 text-zinc-500">Resource List — coming in Task 7</div>
          }
          right={
            <div className="p-4 text-zinc-500">Preview Panel — coming in Task 8</div>
          }
        />
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Update App.tsx**

```typescript
import { Routes, Route } from 'react-router-dom'
import ProjectListScreen from '@/screens/ProjectListScreen'
import WorkspaceScreen from '@/screens/WorkspaceScreen'

export default function App() {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <Routes>
        <Route path="/" element={<ProjectListScreen />} />
        <Route path="/projects/:projectRefId" element={<WorkspaceScreen />} />
        <Route path="/projects/:projectRefId/resources/:slug" element={<WorkspaceScreen />} />
      </Routes>
    </div>
  )
}
```

- [ ] **Step 3: Verify — click a project from the list and see the split-pane workspace**

```bash
cd apps/web && npm run dev
```

- [ ] **Step 4: Commit**

```bash
git add apps/web/src/screens/WorkspaceScreen.tsx apps/web/src/App.tsx
git commit -m "feat: add workspace screen with split-pane layout"
```

---

### Task 7: Resource List and Palette

**Files:**
- Create: `apps/web/src/components/resources/ResourceList.tsx`
- Create: `apps/web/src/components/resources/ResourcePalette.tsx`
- Modify: `apps/web/src/screens/WorkspaceScreen.tsx`

- [ ] **Step 1: Create ResourcePalette.tsx**

```typescript
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

const RESOURCE_CATEGORIES = [
  {
    name: 'Compute',
    color: 'text-blue-400',
    types: [
      { type: 'cloud_run', label: 'Cloud Run' },
      { type: 'cloud_run_job', label: 'Cloud Run Job' },
      { type: 'cloud_function', label: 'Cloud Function' },
    ],
  },
  {
    name: 'Network',
    color: 'text-green-400',
    types: [
      { type: 'vpc', label: 'VPC' },
      { type: 'subnet', label: 'Subnet' },
      { type: 'vpc_connector', label: 'VPC Connector' },
      { type: 'external_lb', label: 'External Load Balancer' },
    ],
  },
  {
    name: 'Storage',
    color: 'text-purple-400',
    types: [
      { type: 'firestore', label: 'Firestore' },
      { type: 'cloud_sql', label: 'Cloud SQL' },
      { type: 'gcs_bucket', label: 'GCS Bucket' },
      { type: 'bigquery', label: 'BigQuery' },
      { type: 'bigtable', label: 'Bigtable' },
    ],
  },
  {
    name: 'Messaging',
    color: 'text-yellow-400',
    types: [
      { type: 'pubsub_topic', label: 'Pub/Sub Topic' },
      { type: 'pubsub_subscription', label: 'Pub/Sub Subscription' },
      { type: 'cloud_task_queue', label: 'Cloud Tasks' },
    ],
  },
  {
    name: 'Security',
    color: 'text-orange-400',
    types: [
      { type: 'service_account', label: 'Service Account' },
      { type: 'secret_manager', label: 'Secret Manager' },
    ],
  },
]

type ResourcePaletteProps = {
  open: boolean
  onClose: () => void
  onSelect: (type: string, label: string) => void
}

export default function ResourcePalette({ open, onClose, onSelect }: ResourcePaletteProps) {
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Add Resource</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 mt-2">
          {RESOURCE_CATEGORIES.map((cat) => (
            <div key={cat.name}>
              <div className={`text-xs uppercase tracking-wide mb-2 ${cat.color}`}>
                {cat.name}
              </div>
              <div className="grid grid-cols-2 gap-1.5">
                {cat.types.map((t) => (
                  <button
                    key={t.type}
                    onClick={() => onSelect(t.type, t.label)}
                    className="text-left px-3 py-2 rounded bg-zinc-800 hover:bg-zinc-700 text-sm text-zinc-200 transition-colors"
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  )
}
```

- [ ] **Step 2: Create ResourceList.tsx**

```typescript
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useBlueprintStore } from '@/stores/blueprint-store'
import { useProjectStore } from '@/stores/project-store'
import { Button } from '@/components/ui/button'
import ResourcePalette from './ResourcePalette'

const TYPE_COLORS: Record<string, string> = {
  cloud_run: 'bg-blue-500',
  cloud_run_job: 'bg-blue-400',
  cloud_function: 'bg-blue-300',
  vpc: 'bg-green-500',
  subnet: 'bg-green-400',
  vpc_connector: 'bg-green-300',
  external_lb: 'bg-green-200',
  firestore: 'bg-purple-500',
  cloud_sql: 'bg-purple-400',
  gcs_bucket: 'bg-purple-300',
  bigquery: 'bg-purple-200',
  bigtable: 'bg-purple-100',
  pubsub_topic: 'bg-yellow-500',
  pubsub_subscription: 'bg-yellow-400',
  cloud_task_queue: 'bg-yellow-300',
  service_account: 'bg-orange-500',
  secret_manager: 'bg-orange-400',
}

export default function ResourceList() {
  const { projectRefId } = useParams<{ projectRefId: string }>()
  const { selectedEnv } = useProjectStore()
  const { nodes, addNode } = useBlueprintStore()
  const navigate = useNavigate()
  const [paletteOpen, setPaletteOpen] = useState(false)

  const handleAddResource = async (type: string, label: string) => {
    if (!projectRefId || !selectedEnv) return
    const name = `${type.replace(/_/g, '-')}-${Date.now().toString(36).slice(-4)}`
    const result = await addNode(projectRefId, selectedEnv, { name, type })
    setPaletteOpen(false)
    if (result) {
      navigate(`/projects/${projectRefId}/resources/${result.slug || name}`)
    }
  }

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-medium text-sm">Resources</span>
          <span className="text-xs bg-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded">
            {nodes.length}
          </span>
        </div>
        <Button size="sm" variant="outline" onClick={() => setPaletteOpen(true)}>
          + Add
        </Button>
      </div>

      <div className="flex-1 overflow-auto">
        {nodes.length === 0 ? (
          <div className="p-4 text-zinc-500 text-sm">
            No resources yet. Click "+ Add" to add one.
          </div>
        ) : (
          <div className="divide-y divide-zinc-800/50">
            {nodes.map((node) => (
              <button
                key={node.slug}
                onClick={() => navigate(`/projects/${projectRefId}/resources/${node.slug}`)}
                className="w-full text-left px-4 py-3 hover:bg-zinc-900 flex items-center gap-3 transition-colors"
              >
                <div className={`w-2 h-2 rounded-full ${TYPE_COLORS[node.type] || 'bg-zinc-500'}`} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{node.name}</div>
                  <div className="text-xs text-zinc-500">{node.type.replace(/_/g, ' ')}</div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      <ResourcePalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        onSelect={handleAddResource}
      />
    </div>
  )
}
```

- [ ] **Step 3: Wire into WorkspaceScreen**

Update `WorkspaceScreen.tsx` — replace the left pane placeholder:

```typescript
import ResourceList from '@/components/resources/ResourceList'

// In the SplitPane, replace the left placeholder:
<SplitPane
  left={<ResourceList />}
  right={<div className="p-4 text-zinc-500">Preview Panel — coming in Task 8</div>}
/>
```

- [ ] **Step 4: Verify — open a project, see empty resource list, click "+ Add", add a VPC**

```bash
cd apps/web && npm run dev
```

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/components/resources/ apps/web/src/screens/WorkspaceScreen.tsx
git commit -m "feat: add resource list and resource palette"
```

---

### Task 8: Preview Panel with Terraform View

**Files:**
- Create: `apps/web/src/components/preview/PreviewPanel.tsx`
- Create: `apps/web/src/components/preview/TerraformView.tsx`
- Modify: `apps/web/src/screens/WorkspaceScreen.tsx`

- [ ] **Step 1: Create TerraformView.tsx**

```typescript
import { useEffect, useState } from 'react'
import { usePreviewStore } from '@/stores/preview-store'
import { useBlueprintStore } from '@/stores/blueprint-store'

function highlightHcl(code: string): string {
  // Process line by line to avoid regex corruption across HTML tags
  return code.split('\n').map((line) => {
    const escaped = line.replace(/&/g, '&amp;').replace(/</g, '&lt;')
    // Comments take priority
    if (escaped.trimStart().startsWith('#')) {
      return `<span class="text-zinc-500">${escaped}</span>`
    }
    return escaped
      .replace(/\b(resource|variable|provider|terraform|data|output|locals|module)\b/g,
        '<span class="text-purple-400">$&</span>')
      .replace(/"([^"]*?)"/g, '<span class="text-green-400">"$1"</span>')
  }).join('\n')
}

export default function TerraformView() {
  const { tfFiles, tfLoading, fetchTerraform } = usePreviewStore()
  const { envelope } = useBlueprintStore()
  const [selectedFile, setSelectedFile] = useState('')

  useEffect(() => {
    if (envelope) {
      fetchTerraform(envelope)
    }
  }, [envelope, fetchTerraform])

  const fileNames = Object.keys(tfFiles)

  // Auto-select first file when files change
  useEffect(() => {
    if (fileNames.length > 0 && !fileNames.includes(selectedFile)) {
      setSelectedFile(fileNames[0])
    }
  }, [fileNames, selectedFile])

  if (tfLoading) {
    return <div className="p-4 text-zinc-500 text-sm">Generating Terraform...</div>
  }

  if (fileNames.length === 0) {
    return <div className="p-4 text-zinc-500 text-sm">Add resources to see generated Terraform.</div>
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex gap-1 px-2 pt-2 border-b border-zinc-800">
        {fileNames.map((name) => (
          <button
            key={name}
            onClick={() => setSelectedFile(name)}
            className={`px-3 py-1.5 text-xs rounded-t border border-b-0 transition-colors ${
              selectedFile === name
                ? 'bg-zinc-900 text-zinc-100 border-zinc-700'
                : 'bg-zinc-800 text-zinc-500 border-zinc-800 hover:text-zinc-300'
            }`}
          >
            {name}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-auto">
        {selectedFile && tfFiles[selectedFile] && (
          <pre
            className="p-4 text-xs font-mono leading-relaxed"
            dangerouslySetInnerHTML={{ __html: highlightHcl(tfFiles[selectedFile]) }}
          />
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create PreviewPanel.tsx**

```typescript
import { usePreviewStore } from '@/stores/preview-store'
import TerraformView from './TerraformView'

const TAB_LABELS = {
  terraform: 'Terraform',
  'build-log': 'Build Log',
  validation: 'Validation',
} as const

export default function PreviewPanel() {
  const { activeTab, setTab, validationIssues } = usePreviewStore()

  const errorCount = validationIssues.filter((i) => i.severity === 'error').length

  return (
    <div className="h-full flex flex-col bg-zinc-950">
      <div className="flex border-b border-zinc-800">
        {(Object.keys(TAB_LABELS) as Array<keyof typeof TAB_LABELS>).map((tab) => (
          <button
            key={tab}
            onClick={() => setTab(tab)}
            className={`px-4 py-2.5 text-xs font-medium transition-colors relative ${
              activeTab === tab
                ? 'text-blue-400 border-b-2 border-blue-400'
                : 'text-zinc-500 hover:text-zinc-300'
            }`}
          >
            {TAB_LABELS[tab]}
            {tab === 'validation' && errorCount > 0 && (
              <span className="ml-1.5 px-1.5 py-0.5 rounded-full bg-red-500/20 text-red-400 text-[10px]">
                {errorCount}
              </span>
            )}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-hidden">
        {activeTab === 'terraform' && <TerraformView />}
        {activeTab === 'build-log' && (
          <div className="p-4 text-zinc-500 text-sm">Build logs will appear here during deploy. (Phase 1B)</div>
        )}
        {activeTab === 'validation' && (
          <div className="p-4 text-zinc-500 text-sm">Validation results will appear here. (Phase 1B)</div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Wire into WorkspaceScreen**

Update `WorkspaceScreen.tsx` — replace the right pane placeholder:

```typescript
import PreviewPanel from '@/components/preview/PreviewPanel'

// In the SplitPane:
<SplitPane
  left={<ResourceList />}
  right={<PreviewPanel />}
/>
```

- [ ] **Step 4: Verify end-to-end**

With the backend running:
1. Create a project
2. Add a VPC resource
3. See the Terraform output appear in the right pane

```bash
cd apps/web && npm run dev
```

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/components/preview/ apps/web/src/screens/WorkspaceScreen.tsx
git commit -m "feat: add preview panel with Terraform view"
```
