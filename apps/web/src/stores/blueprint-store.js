import { create } from 'zustand';
import { api } from '@/lib/api-client';
export const useBlueprintStore = create((set, get) => ({
    nodes: [],
    loading: false,
    envelope: null,
    fetchBlueprint: async (projectRefId, envName) => {
        set({ loading: true });
        const res = await api.get(`/api/projects/${projectRefId}/envs/${envName}/blueprint`);
        if (res.ok && res.data?.envelope) {
            const nodes = res.data.envelope.nodes || [];
            set({ nodes, envelope: res.data.envelope, loading: false });
        }
        else {
            // Fallback: nodes may exist in subcollection without parent blueprint doc
            const nodesRes = await api.get(`/api/projects/${projectRefId}/envs/${envName}/nodes`);
            const nodes = nodesRes.ok && nodesRes.data ? nodesRes.data.nodes : [];
            set({ nodes, envelope: null, loading: false });
        }
    },
    addNode: async (projectRefId, envName, nodeData) => {
        const res = await api.post(`/api/projects/${projectRefId}/envs/${envName}/nodes`, nodeData);
        if (res.ok && res.data) {
            await get().fetchBlueprint(projectRefId, envName);
            return res.data.node;
        }
        return null;
    },
    updateNode: async (projectRefId, envName, slug, updates) => {
        const res = await api.patch(`/api/projects/${projectRefId}/envs/${envName}/nodes/${slug}`, updates);
        if (res.ok) {
            await get().fetchBlueprint(projectRefId, envName);
            return true;
        }
        return false;
    },
    deleteNode: async (projectRefId, envName, slug) => {
        const res = await api.delete(`/api/projects/${projectRefId}/envs/${envName}/nodes/${slug}`);
        if (res.ok) {
            await get().fetchBlueprint(projectRefId, envName);
            return true;
        }
        return false;
    },
}));
