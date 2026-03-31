import { create } from 'zustand';
import { api } from '@/lib/api-client';
export const useProjectStore = create((set, get) => ({
    projects: [],
    currentProject: null,
    selectedEnv: '',
    loading: false,
    fetchProjects: async () => {
        set({ loading: true });
        const res = await api.get('/api/projects');
        if (res.ok && res.data) {
            set({ projects: res.data, loading: false });
        }
        else {
            set({ loading: false });
        }
    },
    createProject: async (data) => {
        const res = await api.post('/api/projects/provision', data);
        if (res.ok && res.data) {
            await get().fetchProjects();
            return res.data;
        }
        return null;
    },
    loadProject: async (projectRefId) => {
        set({ loading: true });
        const res = await api.get(`/api/projects/${projectRefId}`);
        if (res.ok && res.data) {
            const project = res.data;
            const envs = project.environments || [];
            const firstEnv = envs.length > 0 && typeof envs[0] === 'object' ? envs[0].name : 'dev';
            set({ currentProject: project, selectedEnv: firstEnv, loading: false });
        }
        else {
            set({ loading: false });
        }
    },
    selectEnv: (envName) => set({ selectedEnv: envName }),
    deleteProject: async (projectRefId) => {
        const res = await api.delete(`/api/projects/${projectRefId}`);
        if (res.ok) {
            await get().fetchProjects();
            return true;
        }
        return false;
    },
}));
