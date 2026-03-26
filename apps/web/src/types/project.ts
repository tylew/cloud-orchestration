export type ProvisionStatus = 'pending' | 'provisioning' | 'ready' | 'failed'

export type Environment = {
  id: string
  name: string
  order: number
  deployed: boolean
  deployed_at: string | null
  gcp_project_id: string
  region: string
  provision_status: ProvisionStatus
  provision_id: string
}

export type Project = {
  id: string
  project_id: string
  display_name: string
  region: string
  environments: Environment[]
  owner_uid: string
  created_at: string
  updated_at?: string
}
