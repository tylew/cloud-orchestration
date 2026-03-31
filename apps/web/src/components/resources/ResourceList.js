import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useBlueprintStore } from '@/stores/blueprint-store';
import { useProjectStore } from '@/stores/project-store';
import ResourcePalette from './ResourcePalette';
// ─── Type color map ───────────────────────────────────────────────────────────
const TYPE_COLORS = {
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
};
// ─── Component ────────────────────────────────────────────────────────────────
export default function ResourceList() {
    const { projectRefId } = useParams();
    const { nodes, addNode } = useBlueprintStore();
    const { selectedEnv } = useProjectStore();
    const navigate = useNavigate();
    const [paletteOpen, setPaletteOpen] = useState(false);
    async function handleSelect(type, _label) {
        if (!projectRefId || !selectedEnv)
            return;
        const name = `${type.replace(/_/g, '-')}-${Date.now().toString(36).slice(-4)}`;
        const result = await addNode(projectRefId, selectedEnv, { name, type });
        setPaletteOpen(false);
        if (result) {
            const slug = result.slug || name;
            navigate(`/projects/${projectRefId}/resources/${slug}`);
        }
    }
    return (_jsxs("div", { className: "flex flex-col h-full", children: [_jsxs("div", { className: "flex items-center justify-between px-4 py-3 border-b border-zinc-800", children: [_jsx("span", { className: "text-xs font-semibold uppercase tracking-wider text-zinc-400", children: "Resources" }), _jsx("button", { type: "button", onClick: () => setPaletteOpen(true), className: "text-xs text-zinc-400 hover:text-zinc-100 px-2 py-1 rounded hover:bg-zinc-700 transition-colors", children: "+ Add" })] }), _jsx("div", { className: "flex-1 overflow-y-auto", children: nodes.length === 0 ? (_jsxs("div", { className: "px-4 py-6 text-xs text-zinc-600 text-center", children: ["No resources yet.", _jsx("br", {}), "Click ", _jsx("span", { className: "text-zinc-400", children: "+ Add" }), " to get started."] })) : (_jsx("ul", { className: "py-1", children: nodes.map((node) => (_jsx("li", { children: _jsxs("button", { type: "button", onClick: () => navigate(`/projects/${projectRefId}/resources/${node.slug}`), className: "w-full flex items-center gap-3 px-4 py-2 text-left hover:bg-zinc-800 transition-colors group", children: [_jsx("span", { className: `w-2 h-2 rounded-full flex-shrink-0 ${TYPE_COLORS[node.type] ?? 'bg-zinc-500'}` }), _jsxs("span", { className: "flex-1 min-w-0", children: [_jsx("span", { className: "block text-sm text-zinc-200 truncate", children: node.name }), _jsx("span", { className: "block text-xs text-zinc-500 truncate", children: node.type })] })] }) }, node.slug))) })) }), _jsx(ResourcePalette, { open: paletteOpen, onClose: () => setPaletteOpen(false), onSelect: handleSelect })] }));
}
