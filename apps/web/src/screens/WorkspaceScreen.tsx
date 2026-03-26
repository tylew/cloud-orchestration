import { useEffect, useCallback, useState, useMemo } from 'react'
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

function getDevEnv(project: Project | null): Environment | undefined {
  if (!project) return undefined
  return (project.environments || []).find(
    (e): e is Environment => typeof e === 'object' && e.name === 'dev'
  )
}

export default function WorkspaceScreen() {
  const { projectRefId } = useParams<{ projectRefId: string }>()
  const { user } = useAuthStore()
  const { currentProject, selectedEnv, loadProject } = useProjectStore()
  const { fetchBlueprint } = useBlueprintStore()
  const [firestoreProject, setFirestoreProject] = useState<Project | null>(null)

  // Subscribe to project doc in Firestore for real-time provision status
  useEffect(() => {
    if (!user || !projectRefId) return

    const ref = doc(db, 'tenants', user.uid, 'projects', projectRefId)
    const unsub = onSnapshot(ref, (snap) => {
      if (!snap.exists()) return
      const data = snap.data() as Omit<Project, 'id'>
      setFirestoreProject({ ...data, id: snap.id })
    })

    return unsub
  }, [user, projectRefId])

  // Load project via store for API operations
  useEffect(() => {
    if (projectRefId) {
      loadProject(projectRefId)
    }
  }, [projectRefId, loadProject])

  const activeProject = firestoreProject || currentProject
  const devEnv = useMemo(() => getDevEnv(activeProject), [activeProject])
  const isDevReady = devEnv?.provision_status === 'ready'

  // Load blueprint only when dev env is provisioned
  useEffect(() => {
    if (projectRefId && selectedEnv && isDevReady) {
      fetchBlueprint(projectRefId, selectedEnv)
    }
  }, [projectRefId, selectedEnv, isDevReady, fetchBlueprint])

  const handleProvisionReady = useCallback(() => {
    if (projectRefId) {
      loadProject(projectRefId)
    }
  }, [projectRefId, loadProject])

  if (!activeProject) {
    return (
      <div className="h-screen bg-zinc-950 flex items-center justify-center">
        <div className="text-zinc-500">Loading project...</div>
      </div>
    )
  }

  // Show provisioning screen if dev env is not ready
  if (!isDevReady) {
    return (
      <div className="h-screen bg-zinc-950 flex flex-col">
        <div className="h-12 border-b border-zinc-800 bg-zinc-900 flex items-center px-4">
          <span className="font-semibold text-sm text-zinc-100">{activeProject.display_name}</span>
          <span className="ml-3 px-2 py-0.5 rounded text-xs bg-yellow-500/10 text-yellow-400 border border-yellow-500/20">
            Provisioning
          </span>
        </div>
        <div className="flex-1">
          <ProvisioningView
            provisionId={devEnv?.provision_id || ''}
            onReady={handleProvisionReady}
          />
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
