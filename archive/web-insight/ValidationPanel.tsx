import { useInsightStore } from '@/stores/insight-store'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

type ValidationIssue = {
  severity: 'error' | 'warning'
  node: string | null
  message: string
}

export function ValidationPanel() {
  const validation = useInsightStore((s) => s.validation)
  const loading = useInsightStore((s) => s.loading)

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold">Validation</CardTitle>
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

  if (!validation) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold">Validation</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Validation not yet run.</p>
        </CardContent>
      </Card>
    )
  }

  const issues = (validation.issues as ValidationIssue[]) || []

  if (issues.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold">Validation</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No validation issues. Blueprint is clean.
          </p>
        </CardContent>
      </Card>
    )
  }

  // Group by node slug, sort errors before warnings
  const sorted = [...issues].sort((a, b) => {
    if (a.severity === 'error' && b.severity !== 'error') return -1
    if (a.severity !== 'error' && b.severity === 'error') return 1
    return 0
  })

  const grouped = sorted.reduce<Record<string, ValidationIssue[]>>((acc, issue) => {
    const key = issue.node || 'Global'
    if (!acc[key]) acc[key] = []
    acc[key].push(issue)
    return acc
  }, {})

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Validation</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {Object.entries(grouped).map(([node, nodeIssues]) => (
            <div key={node}>
              <h4 className="text-sm font-semibold mb-2">{node}</h4>
              <ul className="space-y-1.5">
                {nodeIssues.map((issue, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm">
                    <Badge
                      variant={issue.severity === 'error' ? 'destructive' : 'secondary'}
                      className={
                        issue.severity === 'warning'
                          ? 'bg-amber-500/10 text-amber-700'
                          : ''
                      }
                    >
                      {issue.severity}
                    </Badge>
                    <span>{issue.message}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
