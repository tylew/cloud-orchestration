import { useInsightStore } from '@/stores/insight-store'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'

type ActivityEntry = Record<string, unknown>

function formatRelativeTime(timestamp: unknown): string {
  if (!timestamp) return ''
  try {
    let date: Date
    if (typeof timestamp === 'object' && timestamp !== null && 'seconds' in timestamp) {
      date = new Date((timestamp as { seconds: number }).seconds * 1000)
    } else if (typeof timestamp === 'string') {
      date = new Date(timestamp)
    } else {
      return ''
    }

    const now = Date.now()
    const diffMs = now - date.getTime()
    const diffMin = Math.floor(diffMs / 60000)

    if (diffMin < 1) return 'just now'
    if (diffMin < 60) return `${diffMin}m ago`
    return date.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

export function ActivityFeed() {
  const activity = useInsightStore((s) => s.activity)
  const loading = useInsightStore((s) => s.loading)

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold">Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-4 animate-pulse rounded bg-muted" />
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  if (activity.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold">Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No recent activity. Operations will appear here as the agent works.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Activity</CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="max-h-[400px] overflow-auto">
          <ul className="space-y-2">
            {activity.map((entry: ActivityEntry, idx: number) => (
              <li key={(entry.id as string) || idx} className="flex items-start gap-2">
                <span className="text-xs text-muted-foreground shrink-0 pt-0.5">
                  {formatRelativeTime(entry.timestamp)}
                </span>
                <span className="text-sm">
                  {(entry.description as string) || (entry.message as string) || (entry.operation as string) || ''}
                </span>
              </li>
            ))}
          </ul>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
