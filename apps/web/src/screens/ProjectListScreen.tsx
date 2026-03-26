import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useProjectStore } from '@/stores/project-store'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'

export default function ProjectListScreen() {
  const { projects, loading, fetchProjects, createProject, deleteProject } = useProjectStore()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ display_name: '', region: 'us-central1' })
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    fetchProjects()
  }, [fetchProjects])

  const handleCreate = async () => {
    if (!form.display_name.trim()) return
    setCreating(true)
    const result = await createProject(form)
    setCreating(false)
    if (result) {
      setOpen(false)
      setForm({ display_name: '', region: 'us-central1' })
      navigate(`/projects/${result.project_ref_id}`)
    }
  }

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    if (confirm('Delete this project?')) {
      await deleteProject(id)
    }
  }

  return (
    <div className="max-w-5xl mx-auto p-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Projects</h1>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger render={<Button />}>
            Create Project
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Project</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 mt-4">
              <div>
                <label className="text-sm text-zinc-400">Project Name</label>
                <Input
                  value={form.display_name}
                  onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                  placeholder="My Project"
                  autoFocus
                />
              </div>
              <div>
                <label className="text-sm text-zinc-400">Region</label>
                <Input
                  value={form.region}
                  onChange={(e) => setForm({ ...form, region: e.target.value })}
                  placeholder="us-central1"
                />
              </div>
              <Button onClick={handleCreate} className="w-full" disabled={creating}>
                {creating ? 'Provisioning...' : 'Create Project'}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {loading ? (
        <div className="text-zinc-500">Loading...</div>
      ) : projects.length === 0 ? (
        <div className="text-zinc-500">No projects yet. Create one to get started.</div>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-800 text-zinc-400 text-left">
              <th className="pb-3 font-medium">Name</th>
              <th className="pb-3 font-medium">Region</th>
              <th className="pb-3 font-medium">Environments</th>
              <th className="pb-3 font-medium w-20"></th>
            </tr>
          </thead>
          <tbody>
            {projects.map((p) => (
              <tr
                key={p.id}
                className="border-b border-zinc-800/50 hover:bg-zinc-900 cursor-pointer"
                onClick={() => navigate(`/projects/${p.id}`)}
              >
                <td className="py-3 font-medium">{p.display_name}</td>
                <td className="py-3 text-zinc-400">{p.region}</td>
                <td className="py-3">
                  <div className="flex gap-1.5">
                    {(p.environments || []).map((env) => {
                      const name = typeof env === 'string' ? env : env.name
                      const status = typeof env === 'object' ? env.provision_status : undefined
                      const statusColor = status === 'ready' ? 'text-green-400'
                        : status === 'provisioning' ? 'text-yellow-400'
                        : status === 'failed' ? 'text-red-400'
                        : 'text-zinc-400'
                      return (
                        <span
                          key={name}
                          className="px-2 py-0.5 rounded text-xs bg-zinc-800 text-zinc-300"
                        >
                          <span className={statusColor}>●</span> {name}
                        </span>
                      )
                    })}
                  </div>
                </td>
                <td className="py-3">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-zinc-500 hover:text-red-400"
                    onClick={(e) => handleDelete(e, p.id)}
                  >
                    Delete
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
