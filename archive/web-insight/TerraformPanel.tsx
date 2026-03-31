import { useState, useEffect } from 'react'
import { useInsightStore } from '@/stores/insight-store'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { api } from '@/lib/api-client'

type TerraformPanelProps = {
  projectRefId: string
}

type TerraformResponse = {
  files?: Record<string, string>
  terraform?: string
  [key: string]: unknown
}

export function TerraformPanel({ projectRefId }: TerraformPanelProps) {
  const env = useInsightStore((s) => s.env)
  const [tfContent, setTfContent] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)

    async function fetchTerraform() {
      const res = await api.get<TerraformResponse>(
        `/api/debug/${projectRefId}/${env}/terraform`
      )
      if (cancelled) return
      if (res.ok && res.data) {
        if (res.data.files && typeof res.data.files === 'object') {
          const parts = Object.entries(res.data.files).map(
            ([filename, content]) => `// --- ${filename} ---\n${content}`
          )
          setTfContent(parts.join('\n\n'))
        } else if (typeof res.data.terraform === 'string') {
          setTfContent(res.data.terraform)
        } else {
          setTfContent(JSON.stringify(res.data, null, 2))
        }
      } else {
        setTfContent(null)
      }
      setLoading(false)
    }

    fetchTerraform()
    return () => { cancelled = true }
  }, [projectRefId, env])

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold">Terraform Preview</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-48 animate-pulse rounded bg-muted" />
        </CardContent>
      </Card>
    )
  }

  if (!tfContent) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-semibold">Terraform Preview</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No Terraform generated yet. Add resources and validate to see compiled output.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Terraform Preview</CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="max-h-[500px] overflow-auto">
          <pre className="font-mono text-sm whitespace-pre-wrap break-all p-2 rounded bg-muted">
            {tfContent}
          </pre>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
