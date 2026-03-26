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
