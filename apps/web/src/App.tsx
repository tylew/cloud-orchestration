import { useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth-store'
import LoginScreen from '@/screens/LoginScreen'
import ProjectListScreen from '@/screens/ProjectListScreen'
import WorkspaceScreen from '@/screens/WorkspaceScreen'
import InsightBoard from '@/screens/InsightBoard'

export default function App() {
  const { user, loading, init } = useAuthStore()

  useEffect(() => {
    init()
  }, [init])

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <div className="text-zinc-500">Loading...</div>
      </div>
    )
  }

  if (!user) {
    return <LoginScreen />
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <Routes>
        <Route path="/" element={<ProjectListScreen />} />
        <Route path="/projects/:projectRefId" element={<WorkspaceScreen />} />
        <Route path="/projects/:projectRefId/resources/:slug" element={<WorkspaceScreen />} />
        <Route path="/insight/:projectRefId" element={<InsightBoard />} />
      </Routes>
    </div>
  )
}
