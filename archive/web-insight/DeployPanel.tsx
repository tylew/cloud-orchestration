import { useState, useEffect, useRef, useCallback } from 'react'
import { useInsightStore } from '@/stores/insight-store'
import { useAuthStore } from '@/stores/auth-store'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { StatusDot } from './StatusDot'
import { api } from '@/lib/api-client'
import { ChevronDown, ChevronRight } from 'lucide-react'

type DeployPanelProps = {
  projectRefId: string
}

type Deploy = {
  deploy_id?: string
  id?: string
  env?: string
  status?: string
  started_at?: string
  finished_at?: string
  [key: string]: unknown
}

type LogEntry = {
  text?: string
  message?: string
  timestamp?: string
  [key: string]: unknown
}

function getDeployStatusDot(status: string): 'success' | 'warning' | 'error' | 'pending' {
  switch (status) {
    case 'success':
    case 'deployed':
      return 'success'
    case 'running':
    case 'building':
    case 'queued':
      return 'warning'
    case 'failed':
    case 'error':
      return 'error'
    default:
      return 'pending'
  }
}

function formatTimestamp(ts: string): string {
  try {
    const d = new Date(ts)
    return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return ts
  }
}

export function DeployPanel({ projectRefId }: DeployPanelProps) {
  const env = useInsightStore((s) => s.env)
  const [deploy, setDeploy] = useState<Deploy | null>(null)
  const [loading, setLoading] = useState(true)
  const [logExpanded, setLogExpanded] = useState(false)
  const [logLines, setLogLines] = useState<LogEntry[]>([])
  const logEndRef = useRef<HTMLDivElement>(null)

  // Fetch latest deploy
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setLogLines([])

    async function fetchDeploy() {
      const res = await api.get<Deploy[] | { deploys?: Deploy[] }>(
        `/api/debug/${projectRefId}/deploys`
      )
      if (cancelled) return
      if (res.ok && res.data) {
        const deploys = Array.isArray(res.data) ? res.data : (res.data.deploys || [])
        const envDeploys = deploys.filter((d) => d.env === env)
        setDeploy(envDeploys.length > 0 ? envDeploys[0] : deploys[0] || null)
      } else {
        setDeploy(null)
      }
      setLoading(false)
    }

    fetchDeploy()
    return () => { cancelled = true }
  }, [projectRefId, env])

  // SSE streaming for active deploys
  useEffect(() => {
    if (!deploy) return
    const status = deploy.status || ''
    const isActive = status === 'running' || status === 'building'
    if (!isActive) return

    const deployId = deploy.deploy_id || deploy.id
    if (!deployId) return

    let es: EventSource | null = null

    async function connectSSE() {
      const token = await useAuthStore.getState().getToken()
      if (!token) return

      es = new EventSource(
        `/api/projects/${projectRefId}/deploys/${deployId}/logs/stream?token=${token}`
      )
      es.onmessage = (event) => {
        try {
          const logEntry = JSON.parse(event.data) as LogEntry
          setLogLines((prev) => [...prev, logEntry])
        } catch {
          setLogLines((prev) => [...prev, { text: event.data }])
        }
      }
      es.onerror = () => {
        es?.close()
      }
    }

    connectSSE()
    return () => { es?.close() }
  }, [deploy, projectRefId])

  // Auto-scroll on new log entries
  useEffect(() => {
    if (logExpanded && logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logLines.length, logExpanded])

  const handleToggleLogs = useCallback(() => {
    setLogExpanded((prev) => !prev)
  }, [])

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold">Deploy</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="h-4 w-3/4 animate-pulse rounded bg-muted" />
            <div className="h-4 w-1/2 animate-pulse rounded bg-muted" />
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!deploy) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold">Deploy</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No deploys recorded. Trigger a deploy through the MCP tools to see logs here.
          </p>
        </CardContent>
      </Card>
    )
  }

  const deployId = (deploy.deploy_id || deploy.id || '-') as string
  const status = (deploy.status || 'unknown') as string

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Deploy</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Deploy status - always visible */}
          <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
            <dt className="text-xs text-muted-foreground">Deploy ID</dt>
            <dd className="font-mono text-xs">{deployId}</dd>
            <dt className="text-xs text-muted-foreground">Environment</dt>
            <dd>{deploy.env as string || env}</dd>
            <dt className="text-xs text-muted-foreground">Status</dt>
            <dd className="inline-flex items-center gap-1.5">
              <StatusDot status={getDeployStatusDot(status)} />
              {status}
            </dd>
            {deploy.started_at && (
              <>
                <dt className="text-xs text-muted-foreground">Started</dt>
                <dd className="text-xs">{formatTimestamp(deploy.started_at as string)}</dd>
              </>
            )}
            {deploy.finished_at && (
              <>
                <dt className="text-xs text-muted-foreground">Finished</dt>
                <dd className="text-xs">{formatTimestamp(deploy.finished_at as string)}</dd>
              </>
            )}
          </dl>

          {/* Collapsible log section */}
          <button
            onClick={handleToggleLogs}
            className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            {logExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            Logs {logLines.length > 0 && `(${logLines.length})`}
          </button>

          {logExpanded && (
            <ScrollArea className="max-h-[400px] overflow-auto rounded border bg-muted/50 p-2">
              <div className="font-mono text-xs space-y-0.5">
                {logLines.length === 0 ? (
                  <p className="text-muted-foreground p-2">No log entries yet.</p>
                ) : (
                  logLines.map((entry, idx) => (
                    <div key={idx} className="flex gap-2">
                      <span className="text-muted-foreground shrink-0">
                        [{entry.timestamp ? formatTimestamp(entry.timestamp) : '--:--:--'}]
                      </span>
                      <span>{entry.text || entry.message || JSON.stringify(entry)}</span>
                    </div>
                  ))
                )}
                <div ref={logEndRef} />
              </div>
            </ScrollArea>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
