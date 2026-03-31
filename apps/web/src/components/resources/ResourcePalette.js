import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { Dialog, DialogContent, DialogHeader, DialogTitle, } from '@/components/ui/dialog';
// ─── Data ─────────────────────────────────────────────────────────────────────
const RESOURCE_CATEGORIES = [
    {
        name: 'Compute',
        color: 'text-blue-400',
        types: [
            { type: 'cloud_run', label: 'Cloud Run' },
            { type: 'cloud_run_job', label: 'Cloud Run Job' },
            { type: 'cloud_function', label: 'Cloud Function' },
        ],
    },
    {
        name: 'Network',
        color: 'text-green-400',
        types: [
            { type: 'vpc', label: 'VPC' },
            { type: 'subnet', label: 'Subnet' },
            { type: 'vpc_connector', label: 'VPC Connector' },
            { type: 'external_lb', label: 'External Load Balancer' },
        ],
    },
    {
        name: 'Storage',
        color: 'text-purple-400',
        types: [
            { type: 'firestore', label: 'Firestore' },
            { type: 'cloud_sql', label: 'Cloud SQL' },
            { type: 'gcs_bucket', label: 'GCS Bucket' },
            { type: 'bigquery', label: 'BigQuery' },
            { type: 'bigtable', label: 'Bigtable' },
        ],
    },
    {
        name: 'Messaging',
        color: 'text-yellow-400',
        types: [
            { type: 'pubsub_topic', label: 'Pub/Sub Topic' },
            { type: 'pubsub_subscription', label: 'Pub/Sub Subscription' },
            { type: 'cloud_task_queue', label: 'Cloud Tasks' },
        ],
    },
    {
        name: 'Security',
        color: 'text-orange-400',
        types: [
            { type: 'service_account', label: 'Service Account' },
            { type: 'secret_manager', label: 'Secret Manager' },
        ],
    },
];
// ─── Component ────────────────────────────────────────────────────────────────
export default function ResourcePalette({ open, onClose, onSelect }) {
    return (_jsx(Dialog, { open: open, onOpenChange: (isOpen) => { if (!isOpen)
            onClose(); }, children: _jsxs(DialogContent, { className: "sm:max-w-lg max-h-[80vh] overflow-y-auto", children: [_jsx(DialogHeader, { children: _jsx(DialogTitle, { children: "Add Resource" }) }), _jsx("div", { className: "flex flex-col gap-5 mt-2", children: RESOURCE_CATEGORIES.map((category) => (_jsxs("div", { children: [_jsx("p", { className: `text-xs font-semibold uppercase tracking-wider mb-2 ${category.color}`, children: category.name }), _jsx("div", { className: "flex flex-col gap-1", children: category.types.map((resource) => (_jsx("button", { type: "button", onClick: () => onSelect(resource.type, resource.label), className: "w-full text-left px-3 py-2 rounded-md text-sm text-zinc-200 hover:bg-zinc-700 transition-colors", children: resource.label }, resource.type))) })] }, category.name))) })] }) }));
}
