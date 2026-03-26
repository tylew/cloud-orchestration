import { create } from 'zustand'
import { api } from '@/lib/api-client'
import type { Project } from '@/types/project'

type ProjectState = {
  projects: Project[]
  currentProject: Project | null
  selectedEnv: string
  loading: boolean
  fetchProjects: () => Promise<void>
  createProject: (data: { display_name: string; region?: string }) => Promise<{ project_ref_id: string } | null>
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
    const res = await api.post<{ project_ref_id: string; provision_id: string }>('/api/projects/provision', data)
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
