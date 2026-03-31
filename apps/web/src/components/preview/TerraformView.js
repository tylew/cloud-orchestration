import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useState } from 'react';
import { usePreviewStore } from '@/stores/preview-store';
import { useBlueprintStore } from '@/stores/blueprint-store';
function highlightHcl(code) {
    return code.split('\n').map((line) => {
        const escaped = line.replace(/&/g, '&amp;').replace(/</g, '&lt;');
        if (escaped.trimStart().startsWith('#')) {
            return `<span class="text-zinc-500">${escaped}</span>`;
        }
        return escaped
            .replace(/\b(resource|variable|provider|terraform|data|output|locals|module)\b/g, '<span class="text-purple-400">$&</span>')
            .replace(/"([^"]*?)"/g, '<span class="text-green-400">"$1"</span>');
    }).join('\n');
}
export default function TerraformView() {
    const { tfFiles, tfLoading, fetchTerraform } = usePreviewStore();
    const { envelope } = useBlueprintStore();
    const [selectedFile, setSelectedFile] = useState('');
    useEffect(() => {
        if (envelope) {
            fetchTerraform(envelope);
        }
    }, [envelope, fetchTerraform]);
    const fileNames = Object.keys(tfFiles);
    useEffect(() => {
        if (fileNames.length > 0 && !fileNames.includes(selectedFile)) {
            setSelectedFile(fileNames[0]);
        }
    }, [fileNames, selectedFile]);
    if (tfLoading) {
        return _jsx("div", { className: "p-4 text-zinc-500 text-sm", children: "Generating Terraform..." });
    }
    if (fileNames.length === 0) {
        return _jsx("div", { className: "p-4 text-zinc-500 text-sm", children: "Add resources to see generated Terraform." });
    }
    return (_jsxs("div", { className: "h-full flex flex-col", children: [_jsx("div", { className: "flex gap-1 px-2 pt-2 border-b border-zinc-800", children: fileNames.map((name) => (_jsx("button", { onClick: () => setSelectedFile(name), className: `px-3 py-1.5 text-xs rounded-t border border-b-0 transition-colors ${selectedFile === name
                        ? 'bg-zinc-900 text-zinc-100 border-zinc-700'
                        : 'bg-zinc-800 text-zinc-500 border-zinc-800 hover:text-zinc-300'}`, children: name }, name))) }), _jsx("div", { className: "flex-1 overflow-auto", children: selectedFile && tfFiles[selectedFile] && (_jsx("pre", { className: "p-4 text-xs font-mono leading-relaxed", dangerouslySetInnerHTML: { __html: highlightHcl(tfFiles[selectedFile]) } })) })] }));
}
