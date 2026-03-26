import { useEffect, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { doc, onSnapshot } from 'firebase/firestore'
import { db } from '@/lib/firebase'
import { useProjectStore } from '@/stores/project-store'
import { useAuthStore } from '@/stores/auth-store'
import { useBlueprintStore } from '@/stores/blueprint-store'
import TopBar from '@/components/layout/TopBar'
import SplitPane from '@/components/layout/SplitPane'
import ResourceList from '@/components/resources/ResourceList'
import PreviewPanel from '@/components/preview/PreviewPanel'
import ProvisioningView from '@/components/provisioning/ProvisioningView'
import type { Project, Environment } from '@/types/project'
import { useState } from 'react'

function getDevEnv(project: Project | null): Environment | undefined {
  if (!project) return undefined
  return (project.environments || []).find(
    (e): e is Environment => typeof e === 'object' && e.name === 'dev'
  )
}

export default function WorkspaceScreen() {
  const { projectRefId } = useParams<{ projectRefId: string }>()
  const { user } = useAuthStore()
  const { selectedEnv, loadProject, selectEnv } = useProjectStore()
  const { fetchBlueprint } = useBlueprintStore()
  const [project, setProject] = useState<Project | null>(null)

  // Single source of truth: Firestore listener on the project doc
  useEffect(() => {
    if (!user || !projectRefId) return

    const ref = doc(db, 'tenants', user.uid, 'projects', projectRefId)
    const unsub = onSnapshot(ref, (snap) => {
      if (!snap.exists()) return
      const data = snap.data() as Omit<Project, 'id'>
      const p = { ...data, id: snap.id } as Project
      setProject(p)

      // Set selected env to first env if not set
      const envs = p.environments || []
      if (envs.length > 0 && !selectedEnv) {
        const first = typeof envs[0] === 'object' ? envs[0].name : 'dev'
        selectEnv(first)
      }
    })

    return unsub
  }, [user, projectRefId])

  // Also load via API store (for other components that read from store)
  useEffect(() => {
    if (projectRefId) {
      loadProject(projectRefId)
    }
  }, [projectRefId, loadProject])

  const devEnv = useMemo(() => getDevEnv(project), [project])
  const isDevReady = devEnv?.provision_status === 'ready'

  // Load blueprint only when dev env is provisioned and env is selected
  useEffect(() => {
    if (projectRefId && selectedEnv && isDevReady) {
      fetchBlueprint(projectRefId, selectedEnv)
    }
  }, [projectRefId, selectedEnv, isDevReady, fetchBlueprint])

  if (!project) {
    return (
      <div className="h-screen bg-zinc-950 flex items-center justify-center">
        <div className="text-zinc-500">Loading project...</div>
      </div>
    )
  }

  // Gate: show provisioning screen until dev env is ready
  if (!isDevReady) {
    return (
      <div className="h-screen bg-zinc-950 flex flex-col">
        <div className="h-12 border-b border-zinc-800 bg-zinc-900 flex items-center px-4">
          <span className="font-semibold text-sm text-zinc-100">{project.display_name}</span>
          <span className="ml-3 px-2 py-0.5 rounded text-xs bg-yellow-500/10 text-yellow-400 border border-yellow-500/20">
            Provisioning
          </span>
        </div>
        <div className="flex-1">
          <ProvisioningView provisionId={devEnv?.provision_id || ''} />
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col">
      <TopBar />
      <div className="flex-1 overflow-hidden">
        <SplitPane
          left={<ResourceList />}
          right={<PreviewPanel />}
        />
      </div>
    </div>
  )
}
