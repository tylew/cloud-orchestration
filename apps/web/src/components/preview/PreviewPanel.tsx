import { usePreviewStore } from '@/stores/preview-store'
import TerraformView from './TerraformView'

const TAB_LABELS = {
  terraform: 'Terraform',
  'build-log': 'Build Log',
  validation: 'Validation',
} as const

export default function PreviewPanel() {
  const { activeTab, setTab, validationIssues } = usePreviewStore()

  const errorCount = validationIssues.filter((i) => i.severity === 'error').length

  return (
    <div className="h-full flex flex-col bg-zinc-950">
      <div className="flex border-b border-zinc-800">
        {(Object.keys(TAB_LABELS) as Array<keyof typeof TAB_LABELS>).map((tab) => (
          <button
            key={tab}
            onClick={() => setTab(tab)}
            className={`px-4 py-2.5 text-xs font-medium transition-colors relative ${
              activeTab === tab
                ? 'text-blue-400 border-b-2 border-blue-400'
                : 'text-zinc-500 hover:text-zinc-300'
            }`}
          >
            {TAB_LABELS[tab]}
            {tab === 'validation' && errorCount > 0 && (
              <span className="ml-1.5 px-1.5 py-0.5 rounded-full bg-red-500/20 text-red-400 text-[10px]">
                {errorCount}
              </span>
            )}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-hidden">
        {activeTab === 'terraform' && <TerraformView />}
        {activeTab === 'build-log' && (
          <div className="p-4 text-zinc-500 text-sm">Build logs will appear here during deploy. (Phase 1B)</div>
        )}
        {activeTab === 'validation' && (
          <div className="p-4 text-zinc-500 text-sm">Validation results will appear here. (Phase 1B)</div>
        )}
      </div>
    </div>
  )
}
