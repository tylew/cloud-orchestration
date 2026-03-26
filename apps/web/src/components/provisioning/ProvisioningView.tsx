import { useEffect, useState } from 'react'
import { doc, onSnapshot } from 'firebase/firestore'
import { db } from '@/lib/firebase'
import { useAuthStore } from '@/stores/auth-store'

type ProvisionStep = {
  step: string
  success?: boolean
  error?: string
  skipped?: boolean
  timestamp: string
}

type ProvisionRecord = {
  status: string
  steps: ProvisionStep[]
  error?: string
}

const STEP_LABELS: Record<string, string> = {
  creating_tenant_folder: 'Setting up tenant folder',
  creating_env_folder: 'Setting up environment folder',
  creating_project: 'Creating GCP project',
  enabling_apis: 'Enabling GCP APIs',
  creating_bucket: 'Creating Terraform state bucket',
  setup_firebase: 'Setting up Firebase Auth',
  verifying: 'Verifying project health',
  // Step result labels (from step_result.step field)
  ensure_tenant_folder: 'Tenant folder',
  ensure_env_folder: 'Environment folder',
  create_project: 'GCP project',
  enable_apis: 'GCP APIs',
  create_bucket: 'Terraform state bucket',
  verify_health: 'Project health',
}

type ProvisioningViewProps = {
  provisionId: string
  onReady: () => void
}

export default function ProvisioningView({ provisionId, onReady }: ProvisioningViewProps) {
  const { user } = useAuthStore()
  const [record, setRecord] = useState<ProvisionRecord | null>(null)

  useEffect(() => {
    if (!user || !provisionId) return

    const ref = doc(db, 'tenants', user.uid, 'provisions', provisionId)
    const unsub = onSnapshot(ref, (snap) => {
      if (!snap.exists()) return
      const data = snap.data() as ProvisionRecord
      setRecord(data)
      if (data.status === 'ready') {
        onReady()
      }
    })

    return unsub
  }, [user, provisionId, onReady])

  const isFailed = record?.status === 'failed'
  const steps = record?.steps || []

  return (
    <div className="flex items-center justify-center h-full">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <h2 className="text-xl font-semibold">
            {isFailed ? 'Provisioning Failed' : 'Provisioning Environment'}
          </h2>
          <p className="text-zinc-500 text-sm mt-1">
            {isFailed
              ? record?.error || 'An error occurred during provisioning'
              : 'Setting up your GCP project...'}
          </p>
        </div>

        <div className="space-y-2">
          {steps.map((step, i) => {
            const label = STEP_LABELS[step.step] || step.step
            const isSuccess = step.success === true
            const isError = step.success === false && !step.skipped
            const isSkipped = step.skipped === true

            return (
              <div
                key={i}
                className={`flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm ${
                  isError
                    ? 'bg-red-500/10 border border-red-500/20'
                    : isSuccess
                    ? 'bg-zinc-800/50'
                    : isSkipped
                    ? 'bg-zinc-800/30'
                    : 'bg-zinc-800/50'
                }`}
              >
                <span className="flex-shrink-0">
                  {isSuccess && <span className="text-green-400">✓</span>}
                  {isError && <span className="text-red-400">✗</span>}
                  {isSkipped && <span className="text-zinc-500">—</span>}
                </span>
                <span className={isError ? 'text-red-300' : isSkipped ? 'text-zinc-500' : 'text-zinc-300'}>
                  {label}
                </span>
                {step.error && (
                  <span className="text-red-400 text-xs ml-auto truncate max-w-[200px]" title={step.error}>
                    {step.error}
                  </span>
                )}
              </div>
            )
          })}

          {!isFailed && (
            <div className="flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm bg-zinc-800/30 animate-pulse">
              <span className="text-blue-400">●</span>
              <span className="text-zinc-400">
                {record?.status ? STEP_LABELS[record.status] || record.status : 'Initializing...'}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
