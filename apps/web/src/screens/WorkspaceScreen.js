import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { doc, onSnapshot } from 'firebase/firestore';
import { db } from '@/lib/firebase';
import { useProjectStore } from '@/stores/project-store';
import { useAuthStore } from '@/stores/auth-store';
import { useBlueprintStore } from '@/stores/blueprint-store';
import TopBar from '@/components/layout/TopBar';
import SplitPane from '@/components/layout/SplitPane';
import ResourceList from '@/components/resources/ResourceList';
import PreviewPanel from '@/components/preview/PreviewPanel';
import ProvisioningView from '@/components/provisioning/ProvisioningView';
import { useState } from 'react';
function getDevEnv(project) {
    if (!project)
        return undefined;
    return (project.environments || []).find((e) => typeof e === 'object' && e.name === 'dev');
}
export default function WorkspaceScreen() {
    const { projectRefId } = useParams();
    const { user } = useAuthStore();
    const { selectedEnv, loadProject, selectEnv } = useProjectStore();
    const { fetchBlueprint } = useBlueprintStore();
    const [project, setProject] = useState(null);
    // Single source of truth: Firestore listener on the project doc
    useEffect(() => {
        if (!user || !projectRefId)
            return;
        const ref = doc(db, 'tenants', user.uid, 'projects', projectRefId);
        const unsub = onSnapshot(ref, (snap) => {
            if (!snap.exists())
                return;
            const data = snap.data();
            const p = { ...data, id: snap.id };
            setProject(p);
            // Set selected env to first env if not set
            const envs = p.environments || [];
            if (envs.length > 0 && !selectedEnv) {
                const first = typeof envs[0] === 'object' ? envs[0].name : 'dev';
                selectEnv(first);
            }
        });
        return unsub;
    }, [user, projectRefId]);
    // Also load via API store (for other components that read from store)
    useEffect(() => {
        if (projectRefId) {
            loadProject(projectRefId);
        }
    }, [projectRefId, loadProject]);
    const devEnv = useMemo(() => getDevEnv(project), [project]);
    const isDevReady = devEnv?.provision_status === 'ready';
    // Load blueprint only when dev env is provisioned and env is selected
    useEffect(() => {
        if (projectRefId && selectedEnv && isDevReady) {
            fetchBlueprint(projectRefId, selectedEnv);
        }
    }, [projectRefId, selectedEnv, isDevReady, fetchBlueprint]);
    if (!project) {
        return (_jsx("div", { className: "h-screen bg-zinc-950 flex items-center justify-center", children: _jsx("div", { className: "text-zinc-500", children: "Loading project..." }) }));
    }
    // Gate: show provisioning screen until dev env is ready
    if (!isDevReady) {
        return (_jsxs("div", { className: "h-screen bg-zinc-950 flex flex-col", children: [_jsxs("div", { className: "h-12 border-b border-zinc-800 bg-zinc-900 flex items-center px-4", children: [_jsx("span", { className: "font-semibold text-sm text-zinc-100", children: project.display_name }), _jsx("span", { className: "ml-3 px-2 py-0.5 rounded text-xs bg-yellow-500/10 text-yellow-400 border border-yellow-500/20", children: "Provisioning" })] }), _jsx("div", { className: "flex-1", children: _jsx(ProvisioningView, { provisionId: devEnv?.provision_id || '' }) })] }));
    }
    return (_jsxs("div", { className: "h-screen flex flex-col", children: [_jsx(TopBar, {}), _jsx("div", { className: "flex-1 overflow-hidden", children: _jsx(SplitPane, { left: _jsx(ResourceList, {}), right: _jsx(PreviewPanel, {}) }) })] }));
}
