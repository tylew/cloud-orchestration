import { useInsightStore } from '@/stores/insight-store'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { StatusDot } from './StatusDot'

const provisionStatusMap: Record<string, 'success' | 'warning' | 'error' | 'pending'> = {
  ready: 'success',
  provisioning: 'warning',
  failed: 'error',
  pending: 'pending',
}

function LabelValue({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="text-sm">{children}</dd>
    </>
  )
}

export function ProjectStatePanel() {
  const project = useInsightStore((s) => s.project)
  const env = useInsightStore((s) => s.env)
  const loading = useInsightStore((s) => s.loading)

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold">Project State</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="h-4 w-3/4 animate-pulse rounded bg-muted" />
            <div className="h-4 w-1/2 animate-pulse rounded bg-muted" />
            <div className="h-4 w-2/3 animate-pulse rounded bg-muted" />
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!project) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold">Project State</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No project data loaded.</p>
        </CardContent>
      </Card>
    )
  }

  const environments = (project.environments as Array<Record<string, unknown>>) || []
  const currentEnv = environments.find((e) => e.name === env)
  const gcpProjectId = (currentEnv?.gcp_project_id as string) || 'Not provisioned'
  const region = (currentEnv?.region as string) || (project.region as string) || 'us-central1'
  const provisionStatus = (currentEnv?.provision_status as string) || 'pending'

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Project State</CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-3">
          <LabelValue label="Project Name">
            {(project.display_name as string) || 'Untitled'}
          </LabelValue>
          <LabelValue label="Internal ID">
            {(project.internal_id as string) || '-'}
          </LabelValue>
          <LabelValue label="GCP Project ID">
            {gcpProjectId}
          </LabelValue>
          <LabelValue label="Region">
            {region}
          </LabelValue>
          <LabelValue label="Provision Status">
            <span className="inline-flex items-center gap-1.5">
              <StatusDot status={provisionStatusMap[provisionStatus] || 'pending'} />
              {provisionStatus}
            </span>
          </LabelValue>
          <LabelValue label="Environments">
            {environments.length}
          </LabelValue>
        </dl>
      </CardContent>
    </Card>
  )
}
