import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useProjectStore } from '@/stores/project-store';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, } from '@/components/ui/dialog';
export default function ProjectListScreen() {
    const { projects, loading, fetchProjects, createProject, deleteProject } = useProjectStore();
    const navigate = useNavigate();
    const [open, setOpen] = useState(false);
    const [form, setForm] = useState({ display_name: '', region: 'us-central1' });
    const [creating, setCreating] = useState(false);
    useEffect(() => {
        fetchProjects();
    }, [fetchProjects]);
    const handleCreate = async () => {
        if (!form.display_name.trim())
            return;
        setCreating(true);
        const result = await createProject(form);
        setCreating(false);
        if (result) {
            setOpen(false);
            setForm({ display_name: '', region: 'us-central1' });
            navigate(`/projects/${result.project_ref_id}`);
        }
    };
    const handleDelete = async (e, id) => {
        e.stopPropagation();
        if (confirm('Delete this project?')) {
            await deleteProject(id);
        }
    };
    return (_jsxs("div", { className: "max-w-5xl mx-auto p-8", children: [_jsxs("div", { className: "flex items-center justify-between mb-6", children: [_jsx("h1", { className: "text-2xl font-semibold", children: "Projects" }), _jsxs(Dialog, { open: open, onOpenChange: setOpen, children: [_jsx(DialogTrigger, { render: _jsx(Button, {}), children: "Create Project" }), _jsxs(DialogContent, { children: [_jsx(DialogHeader, { children: _jsx(DialogTitle, { children: "Create Project" }) }), _jsxs("div", { className: "space-y-4 mt-4", children: [_jsxs("div", { children: [_jsx("label", { className: "text-sm text-zinc-400", children: "Project Name" }), _jsx(Input, { value: form.display_name, onChange: (e) => setForm({ ...form, display_name: e.target.value }), placeholder: "My Project", autoFocus: true })] }), _jsxs("div", { children: [_jsx("label", { className: "text-sm text-zinc-400", children: "Region" }), _jsx(Input, { value: form.region, onChange: (e) => setForm({ ...form, region: e.target.value }), placeholder: "us-central1" })] }), _jsx(Button, { onClick: handleCreate, className: "w-full", disabled: creating, children: creating ? 'Provisioning...' : 'Create Project' })] })] })] })] }), loading ? (_jsx("div", { className: "text-zinc-500", children: "Loading..." })) : projects.length === 0 ? (_jsx("div", { className: "text-zinc-500", children: "No projects yet. Create one to get started." })) : (_jsxs("table", { className: "w-full text-sm", children: [_jsx("thead", { children: _jsxs("tr", { className: "border-b border-zinc-800 text-zinc-400 text-left", children: [_jsx("th", { className: "pb-3 font-medium", children: "Name" }), _jsx("th", { className: "pb-3 font-medium", children: "Region" }), _jsx("th", { className: "pb-3 font-medium", children: "Environments" }), _jsx("th", { className: "pb-3 font-medium w-20" })] }) }), _jsx("tbody", { children: projects.map((p) => (_jsxs("tr", { className: "border-b border-zinc-800/50 hover:bg-zinc-900 cursor-pointer", onClick: () => navigate(`/projects/${p.id}`), children: [_jsx("td", { className: "py-3 font-medium", children: p.display_name }), _jsx("td", { className: "py-3 text-zinc-400", children: p.region }), _jsx("td", { className: "py-3", children: _jsx("div", { className: "flex gap-1.5", children: (p.environments || []).map((env) => {
                                            const name = typeof env === 'string' ? env : env.name;
                                            const status = typeof env === 'object' ? env.provision_status : undefined;
                                            const statusColor = status === 'ready' ? 'text-green-400'
                                                : status === 'provisioning' ? 'text-yellow-400'
                                                    : status === 'failed' ? 'text-red-400'
                                                        : 'text-zinc-400';
                                            return (_jsxs("span", { className: "px-2 py-0.5 rounded text-xs bg-zinc-800 text-zinc-300", children: [_jsx("span", { className: statusColor, children: "\u25CF" }), " ", name] }, name));
                                        }) }) }), _jsx("td", { className: "py-3", children: _jsx(Button, { variant: "ghost", size: "sm", className: "text-zinc-500 hover:text-red-400", onClick: (e) => handleDelete(e, p.id), children: "Delete" }) })] }, p.id))) })] }))] }));
}
