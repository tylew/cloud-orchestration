import { useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useProjectStore } from '@/stores/project-store'
import { useBlueprintStore } from '@/stores/blueprint-store'
import TopBar from '@/components/layout/TopBar'
import SplitPane from '@/components/layout/SplitPane'
import ResourceList from '@/components/resources/ResourceList'

export default function WorkspaceScreen() {
  const { projectRefId } = useParams<{ projectRefId: string }>()
  const { currentProject, selectedEnv, loadProject } = useProjectStore()
  const { fetchBlueprint } = useBlueprintStore()

  useEffect(() => {
    if (projectRefId) {
      loadProject(projectRefId)
    }
  }, [projectRefId, loadProject])

  useEffect(() => {
    if (projectRefId && selectedEnv) {
      fetchBlueprint(projectRefId, selectedEnv)
    }
  }, [projectRefId, selectedEnv, fetchBlueprint])

  if (!currentProject) {
    return <div className="p-8 text-zinc-500">Loading project...</div>
  }

  return (
    <div className="h-screen flex flex-col">
      <TopBar />
      <div className="flex-1 overflow-hidden">
        <SplitPane
          left={<ResourceList />}
          right={<div className="p-4 text-zinc-500 text-sm">Preview Panel — next task</div>}
        />
      </div>
    </div>
  )
}
