import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState, useCallback } from 'react';
export default function SplitPane({ left, right, defaultLeftWidth = 50 }) {
    const [leftWidth, setLeftWidth] = useState(defaultLeftWidth);
    const [dragging, setDragging] = useState(false);
    const handleMouseDown = useCallback(() => {
        setDragging(true);
        const handleMouseMove = (e) => {
            const pct = (e.clientX / window.innerWidth) * 100;
            setLeftWidth(Math.min(Math.max(pct, 25), 75));
        };
        const handleMouseUp = () => {
            setDragging(false);
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        };
        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
    }, []);
    return (_jsxs("div", { className: "flex h-full", children: [_jsx("div", { style: { width: `${leftWidth}%` }, className: "overflow-auto", children: left }), _jsx("div", { className: `w-1 cursor-col-resize hover:bg-blue-500/50 ${dragging ? 'bg-blue-500/50' : 'bg-zinc-800'}`, onMouseDown: handleMouseDown }), _jsx("div", { style: { width: `${100 - leftWidth}%` }, className: "overflow-auto", children: right })] }));
}
