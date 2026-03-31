export type EnvVarEntry = {
  name: string
  type: 'value' | 'secret'
  value?: string | null
  secret?: string | null
  version?: string
}

export type BaseNode = {
  id?: string
  resource_id?: string
  slug: string
  name: string
  type: string
  depends_on?: string[]
  config: Record<string, unknown>
  env_vars?: EnvVarEntry[]
}

export type Blueprint = {
  env: string
  envelope: {
    version: string
    global: {
      project_id: string
      region: string
      environment: string
    }
    nodes: BaseNode[]
  } | null
}
