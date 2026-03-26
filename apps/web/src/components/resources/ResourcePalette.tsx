import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

// ─── Types ────────────────────────────────────────────────────────────────────

type ResourceType = {
  type: string
  label: string
}

type ResourceCategory = {
  name: string
  color: string
  types: ResourceType[]
}

type ResourcePaletteProps = {
  open: boolean
  onClose: () => void
  onSelect: (type: string, label: string) => void
}

// ─── Data ─────────────────────────────────────────────────────────────────────

const RESOURCE_CATEGORIES: ResourceCategory[] = [
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
]

// ─── Component ────────────────────────────────────────────────────────────────

export default function ResourcePalette({ open, onClose, onSelect }: ResourcePaletteProps) {
  return (
    <Dialog open={open} onOpenChange={(isOpen) => { if (!isOpen) onClose() }}>
      <DialogContent className="sm:max-w-lg max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Add Resource</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-5 mt-2">
          {RESOURCE_CATEGORIES.map((category) => (
            <div key={category.name}>
              <p className={`text-xs font-semibold uppercase tracking-wider mb-2 ${category.color}`}>
                {category.name}
              </p>
              <div className="flex flex-col gap-1">
                {category.types.map((resource) => (
                  <button
                    key={resource.type}
                    type="button"
                    onClick={() => onSelect(resource.type, resource.label)}
                    className="w-full text-left px-3 py-2 rounded-md text-sm text-zinc-200 hover:bg-zinc-700 transition-colors"
                  >
                    {resource.label}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  )
}
