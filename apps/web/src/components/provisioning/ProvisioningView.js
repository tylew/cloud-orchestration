import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from 'react';
import { doc, onSnapshot } from 'firebase/firestore';
import { db } from '@/lib/firebase';
import { useAuthStore } from '@/stores/auth-store';
const STEP_LABELS = {
    creating_tenant_folder: 'Creating tenant folder',
    creating_project_folder: 'Creating project folder',
    creating_project: 'Creating GCP project',
    enabling_apis: 'Enabling GCP APIs',
    // Step result labels (from step_result.step field)
    ensure_tenant_folder: 'Tenant folder',
    ensure_project_folder: 'Project folder',
    create_project: 'GCP project',
    enable_apis: 'GCP APIs',
};
export default function ProvisioningView({ provisionId }) {
    const { user } = useAuthStore();
    const [record, setRecord] = useState(null);
    useEffect(() => {
        if (!user || !provisionId)
            return;
        const ref = doc(db, 'tenants', user.uid, 'provisions', provisionId);
        const unsub = onSnapshot(ref, (snap) => {
            if (!snap.exists())
                return;
            const data = snap.data();
            setRecord(data);
        });
        return unsub;
    }, [user, provisionId]);
    const isFailed = record?.status === 'failed';
    const steps = record?.steps || [];
    return (_jsx("div", { className: "flex items-center justify-center h-full", children: _jsxs("div", { className: "w-full max-w-md space-y-6", children: [_jsxs("div", { className: "text-center", children: [_jsx("h2", { className: "text-xl font-semibold", children: isFailed ? 'Provisioning Failed' : 'Provisioning Environment' }), _jsx("p", { className: "text-zinc-500 text-sm mt-1", children: isFailed
                                ? record?.error || 'An error occurred during provisioning'
                                : 'Setting up your GCP project...' })] }), _jsxs("div", { className: "space-y-2", children: [steps.map((step, i) => {
                            const label = STEP_LABELS[step.step] || step.step;
                            const isSuccess = step.success === true || step.created === true;
                            const isError = (step.success === false || step.created === false) && !step.skipped;
                            const isSkipped = step.skipped === true;
                            return (_jsxs("div", { className: `flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm ${isError
                                    ? 'bg-red-500/10 border border-red-500/20'
                                    : isSuccess
                                        ? 'bg-zinc-800/50'
                                        : isSkipped
                                            ? 'bg-zinc-800/30'
                                            : 'bg-zinc-800/50'}`, children: [_jsxs("span", { className: "flex-shrink-0", children: [isSuccess && _jsx("span", { className: "text-green-400", children: "\u2713" }), isError && _jsx("span", { className: "text-red-400", children: "\u2717" }), isSkipped && _jsx("span", { className: "text-zinc-500", children: "\u2014" })] }), _jsx("span", { className: isError ? 'text-red-300' : isSkipped ? 'text-zinc-500' : 'text-zinc-300', children: label }), step.error && (_jsx("span", { className: "text-red-400 text-xs ml-auto truncate max-w-[200px]", title: step.error, children: step.error }))] }, i));
                        }), !isFailed && (_jsxs("div", { className: "flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm bg-zinc-800/30 animate-pulse", children: [_jsx("span", { className: "text-blue-400", children: "\u25CF" }), _jsx("span", { className: "text-zinc-400", children: record?.status ? STEP_LABELS[record.status] || record.status : 'Initializing...' })] }))] })] }) }));
}
