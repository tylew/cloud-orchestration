import { create } from 'zustand';
import { api } from '@/lib/api-client';
export const usePreviewStore = create((set) => ({
    activeTab: 'terraform',
    tfFiles: {},
    tfLoading: false,
    validationIssues: [],
    setTab: (tab) => set({ activeTab: tab }),
    fetchTerraform: async (envelope) => {
        set({ tfLoading: true });
        const res = await api.post('/api/terraform/generate', envelope);
        if (res.ok && res.data) {
            set({ tfFiles: res.data.files, tfLoading: false });
        }
        else {
            set({ tfFiles: {}, tfLoading: false });
        }
    },
    fetchValidation: async (envelope) => {
        const res = await api.post('/api/blueprints/validate', envelope);
        if (res.ok && res.data) {
            set({ validationIssues: res.data.issues || [] });
        }
    },
    autoSwitch: (tab) => set({ activeTab: tab }),
}));
