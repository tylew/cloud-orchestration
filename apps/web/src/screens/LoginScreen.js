import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from 'react';
import { useAuthStore } from '@/stores/auth-store';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
export default function LoginScreen() {
    const { signInWithEmail, signInWithGoogle, error } = useAuthStore();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const handleEmail = async (e) => {
        e.preventDefault();
        setLoading(true);
        await signInWithEmail(email, password);
        setLoading(false);
    };
    const handleGoogle = async () => {
        setLoading(true);
        await signInWithGoogle();
        setLoading(false);
    };
    return (_jsx("div", { className: "min-h-screen bg-zinc-950 flex items-center justify-center", children: _jsxs("div", { className: "w-full max-w-sm space-y-6", children: [_jsxs("div", { className: "text-center", children: [_jsx("h1", { className: "text-2xl font-bold text-zinc-100", children: "GCP Orchestration" }), _jsx("p", { className: "text-zinc-500 text-sm mt-1", children: "Sign in to continue" })] }), _jsxs("form", { onSubmit: handleEmail, className: "space-y-4", children: [_jsx("div", { children: _jsx(Input, { type: "email", value: email, onChange: (e) => setEmail(e.target.value), placeholder: "Email" }) }), _jsx("div", { children: _jsx(Input, { type: "password", value: password, onChange: (e) => setPassword(e.target.value), placeholder: "Password" }) }), _jsx(Button, { type: "submit", className: "w-full", disabled: loading, children: loading ? 'Signing in...' : 'Sign In' })] }), _jsxs("div", { className: "relative", children: [_jsx("div", { className: "absolute inset-0 flex items-center", children: _jsx("div", { className: "w-full border-t border-zinc-800" }) }), _jsx("div", { className: "relative flex justify-center text-xs", children: _jsx("span", { className: "bg-zinc-950 px-2 text-zinc-500", children: "or" }) })] }), _jsx(Button, { variant: "outline", className: "w-full", onClick: handleGoogle, disabled: loading, children: "Sign in with Google" }), error && (_jsx("p", { className: "text-red-400 text-sm text-center", children: error }))] }) }));
}
