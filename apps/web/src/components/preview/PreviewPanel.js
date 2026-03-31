import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { usePreviewStore } from '@/stores/preview-store';
import TerraformView from './TerraformView';
const TAB_LABELS = {
    terraform: 'Terraform',
    'build-log': 'Build Log',
    validation: 'Validation',
};
export default function PreviewPanel() {
    const { activeTab, setTab, validationIssues } = usePreviewStore();
    const errorCount = validationIssues.filter((i) => i.severity === 'error').length;
    return (_jsxs("div", { className: "h-full flex flex-col bg-zinc-950", children: [_jsx("div", { className: "flex border-b border-zinc-800", children: Object.keys(TAB_LABELS).map((tab) => (_jsxs("button", { onClick: () => setTab(tab), className: `px-4 py-2.5 text-xs font-medium transition-colors relative ${activeTab === tab
                        ? 'text-blue-400 border-b-2 border-blue-400'
                        : 'text-zinc-500 hover:text-zinc-300'}`, children: [TAB_LABELS[tab], tab === 'validation' && errorCount > 0 && (_jsx("span", { className: "ml-1.5 px-1.5 py-0.5 rounded-full bg-red-500/20 text-red-400 text-[10px]", children: errorCount }))] }, tab))) }), _jsxs("div", { className: "flex-1 overflow-hidden", children: [activeTab === 'terraform' && _jsx(TerraformView, {}), activeTab === 'build-log' && (_jsx("div", { className: "p-4 text-zinc-500 text-sm", children: "Build logs will appear here during deploy. (Phase 1B)" })), activeTab === 'validation' && (_jsx("div", { className: "p-4 text-zinc-500 text-sm", children: "Validation results will appear here. (Phase 1B)" }))] })] }));
}
