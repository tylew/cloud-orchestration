import { useInsightStore } from '@/stores/insight-store'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
} from '@/components/ui/table'

const TYPE_LABELS: Record<string, string> = {
  cloud_run: 'Cloud Run',
  cloud_run_job: 'Cloud Run Job',
  cloud_function: 'Cloud Function',
  cloud_sql: 'Cloud SQL',
  firestore: 'Firestore',
  bigquery: 'BigQuery',
  bigtable: 'Bigtable',
  gcs_bucket: 'GCS Bucket',
  pubsub_topic: 'Pub/Sub Topic',
  pubsub_subscription: 'Pub/Sub Sub',
  pubsub_schema: 'Pub/Sub Schema',
  cloud_task_queue: 'Cloud Tasks',
  vpc: 'VPC',
  subnet: 'Subnet',
  vpc_connector: 'VPC Connector',
  external_lb: 'External LB',
  secret_manager: 'Secret Manager',
  service_account: 'Service Account',
  third_party_api: 'Third Party API',
}

type NodeRecord = Record<string, unknown>

function getNodeValidation(node: NodeRecord, validation: Record<string, unknown> | null) {
  if (!validation) return { errors: 0, warnings: 0 }
  const issues = (validation.issues as Array<Record<string, unknown>>) || []
  const nodeSlug = node.slug as string
  const nodeIssues = issues.filter((i) => i.node === nodeSlug || i.node === (node.name as string))
  const errors = nodeIssues.filter((i) => i.severity === 'error').length
  const warnings = nodeIssues.filter((i) => i.severity === 'warning').length
  return { errors, warnings }
}

function getDeployStatusVariant(status: string): 'default' | 'secondary' | 'outline' {
  switch (status) {
    case 'deployed':
      return 'default'
    case 'modified':
      return 'secondary'
    default:
      return 'outline'
  }
}

export function ResourceListPanel() {
  const nodes = useInsightStore((s) => s.nodes)
  const validation = useInsightStore((s) => s.validation)
  const loading = useInsightStore((s) => s.loading)

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold">Resources</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-8 animate-pulse rounded bg-muted" />
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  if (nodes.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold">Resources</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No resources in this environment. The agent has not added any nodes yet.
          </p>
        </CardContent>
      </Card>
    )
  }

  const sortedNodes = [...nodes].sort((a, b) => {
    const aVal = getNodeValidation(a, validation)
    const bVal = getNodeValidation(b, validation)
    if (aVal.errors !== bVal.errors) return bVal.errors - aVal.errors
    if (aVal.warnings !== bVal.warnings) return bVal.warnings - aVal.warnings
    return 0
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Resources</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Type</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Validation</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedNodes.map((node) => {
              const nodeType = node.type as string
              const { errors, warnings } = getNodeValidation(node, validation)
              const deployStatus = (node.deploy_status as string) || 'pending'
              const autoProvisioned = node.auto_provisioned as boolean

              return (
                <TableRow key={node.id as string}>
                  <TableCell className="text-xs text-muted-foreground">
                    {TYPE_LABELS[nodeType] || nodeType}
                  </TableCell>
                  <TableCell className="text-sm">
                    {node.name as string}
                  </TableCell>
                  <TableCell>
                    <span className="inline-flex items-center gap-1.5">
                      <Badge
                        variant={getDeployStatusVariant(deployStatus)}
                        className={
                          deployStatus === 'deployed'
                            ? 'bg-green-500/10 text-green-700'
                            : deployStatus === 'modified'
                              ? 'bg-amber-500/10 text-amber-700'
                              : ''
                        }
                      >
                        {deployStatus}
                      </Badge>
                      {autoProvisioned && (
                        <Badge variant="secondary">Auto</Badge>
                      )}
                    </span>
                  </TableCell>
                  <TableCell>
                    {errors > 0 ? (
                      <Badge variant="destructive">{errors} error{errors > 1 ? 's' : ''}</Badge>
                    ) : warnings > 0 ? (
                      <Badge
                        variant="secondary"
                        className="bg-amber-500/10 text-amber-700"
                      >
                        {warnings} warning{warnings > 1 ? 's' : ''}
                      </Badge>
                    ) : (
                      <Badge
                        variant="secondary"
                        className="bg-green-500/10 text-green-700"
                      >
                        Valid
                      </Badge>
                    )}
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
