import { useNavigate } from 'react-router-dom'
import { useProjectStore } from '@/stores/project-store'
import { Button } from '@/components/ui/button'
import type { Environment } from '@/types/project'

export default function TopBar() {
  const navigate = useNavigate()
  const { currentProject, selectedEnv, selectEnv } = useProjectStore()

  if (!currentProject) return null

  const envs: Environment[] = (currentProject.environments || []).filter(
    (e): e is Environment => typeof e === 'object'
  )

  return (
    <div className="h-12 border-b border-zinc-800 bg-zinc-900 flex items-center justify-between px-4">
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate('/')}
          className="text-zinc-500 hover:text-zinc-300 text-sm"
        >
          ← Projects
        </button>
        <span className="text-zinc-600">|</span>
        <span className="font-semibold text-sm">{currentProject.display_name}</span>
        <select
          value={selectedEnv}
          onChange={(e) => selectEnv(e.target.value)}
          className="h-8 px-2 text-xs bg-zinc-800 border border-zinc-700 rounded text-zinc-200"
        >
          {envs.map((env) => (
            <option key={env.id} value={env.name}>
              {env.name} ({env.provision_status})
            </option>
          ))}
        </select>
      </div>
      <div className="flex items-center gap-2">
        <Button size="sm">Deploy</Button>
      </div>
    </div>
  )
}
