import { useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useInsightStore } from '@/stores/insight-store'
import { useAuthStore } from '@/stores/auth-store'

export default function InsightBoard() {
  const { projectRefId } = useParams<{ projectRefId: string }>()
  const user = useAuthStore((s) => s.user)
  const { subscribe, cleanup, project, env, setEnv, loading, connected, error } =
    useInsightStore()

  useEffect(() => {
    if (user?.uid && projectRefId) {
      subscribe(user.uid, projectRefId, 'dev')
    }
    return cleanup
  }, [user?.uid, projectRefId])

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-muted-foreground">Loading insight board...</div>
      </div>
    )
  }

  const environments = ((project as Record<string, unknown>)?.environments as Array<Record<string, unknown>>) || []

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Connection banner */}
      {!connected && error && (
        <div className="bg-amber-500/10 border-b border-amber-500/20 px-8 py-2 text-sm text-amber-600">
          {error}
        </div>
      )}

      {/* TopBar */}
      <header className="border-b px-8 py-4 flex items-center justify-between">
        <h1 className="text-lg font-semibold">
          {(project as Record<string, unknown>)?.display_name as string || 'Loading...'} — Insight Board
        </h1>
        {/* Environment tabs */}
        <div className="flex gap-2">
          {environments.map((e) => (
            <button
              key={e.name as string}
              onClick={() => setEnv(e.name as string)}
              className={`px-3 py-1 rounded-md text-sm ${
                env === e.name
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:bg-muted/80'
              }`}
            >
              {e.name as string}
            </button>
          ))}
        </div>
      </header>

      {/* Two-column grid -- panels added in Plan 06 */}
      <main className="grid grid-cols-2 gap-8 p-8 pt-12 min-w-[1024px]">
        <div className="flex flex-col gap-6">
          <div className="rounded-lg border bg-card p-4 text-card-foreground">
            <p className="text-sm text-muted-foreground">
              Project State Panel -- coming in Plan 06
            </p>
          </div>
          <div className="rounded-lg border bg-card p-4 text-card-foreground">
            <p className="text-sm text-muted-foreground">
              Resource List Panel -- coming in Plan 06
            </p>
          </div>
          <div className="rounded-lg border bg-card p-4 text-card-foreground">
            <p className="text-sm text-muted-foreground">
              Validation Panel -- coming in Plan 06
            </p>
          </div>
        </div>
        <div className="flex flex-col gap-6">
          <div className="rounded-lg border bg-card p-4 text-card-foreground">
            <p className="text-sm text-muted-foreground">
              Terraform Panel -- coming in Plan 06
            </p>
          </div>
          <div className="rounded-lg border bg-card p-4 text-card-foreground">
            <p className="text-sm text-muted-foreground">
              Deploy Panel -- coming in Plan 06
            </p>
          </div>
          <div className="rounded-lg border bg-card p-4 text-card-foreground">
            <p className="text-sm text-muted-foreground">
              Activity Feed -- coming in Plan 06
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}
