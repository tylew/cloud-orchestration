import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import { useAuthStore } from '@/stores/auth-store';
import LoginScreen from '@/screens/LoginScreen';
import ProjectListScreen from '@/screens/ProjectListScreen';
import WorkspaceScreen from '@/screens/WorkspaceScreen';
export default function App() {
    const { user, loading, init } = useAuthStore();
    useEffect(() => {
        init();
    }, [init]);
    if (loading) {
        return (_jsx("div", { className: "min-h-screen bg-zinc-950 flex items-center justify-center", children: _jsx("div", { className: "text-zinc-500", children: "Loading..." }) }));
    }
    if (!user) {
        return _jsx(LoginScreen, {});
    }
    return (_jsx("div", { className: "min-h-screen bg-zinc-950 text-zinc-100", children: _jsxs(Routes, { children: [_jsx(Route, { path: "/", element: _jsx(ProjectListScreen, {}) }), _jsx(Route, { path: "/projects/:projectRefId", element: _jsx(WorkspaceScreen, {}) }), _jsx(Route, { path: "/projects/:projectRefId/resources/:slug", element: _jsx(WorkspaceScreen, {}) })] }) }));
}
