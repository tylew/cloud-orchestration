import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useNavigate } from 'react-router-dom';
import { useProjectStore } from '@/stores/project-store';
import { useAuthStore } from '@/stores/auth-store';
import { Button } from '@/components/ui/button';
export default function TopBar() {
    const navigate = useNavigate();
    const { currentProject, selectedEnv, selectEnv } = useProjectStore();
    const { user, signOut } = useAuthStore();
    if (!currentProject)
        return null;
    const envs = (currentProject.environments || []).filter((e) => typeof e === 'object');
    return (_jsxs("div", { className: "h-12 border-b border-zinc-800 bg-zinc-900 flex items-center justify-between px-4", children: [_jsxs("div", { className: "flex items-center gap-3", children: [_jsx("button", { onClick: () => navigate('/'), className: "text-zinc-500 hover:text-zinc-300 text-sm", children: "\u2190 Projects" }), _jsx("span", { className: "text-zinc-600", children: "|" }), _jsx("span", { className: "font-semibold text-sm", children: currentProject.display_name }), _jsx("select", { value: selectedEnv, onChange: (e) => selectEnv(e.target.value), className: "h-8 px-2 text-xs bg-zinc-800 border border-zinc-700 rounded text-zinc-200", children: envs.map((env) => (_jsxs("option", { value: env.name, children: [env.name, " (", env.provision_status, ")"] }, env.id))) })] }), _jsxs("div", { className: "flex items-center gap-3", children: [_jsx(Button, { size: "sm", children: "Deploy" }), _jsx("span", { className: "text-zinc-500 text-xs", children: user?.email }), _jsx(Button, { size: "sm", variant: "ghost", className: "text-zinc-500", onClick: signOut, children: "Sign Out" })] })] }));
}
