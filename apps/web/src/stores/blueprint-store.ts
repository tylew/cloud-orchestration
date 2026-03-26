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
