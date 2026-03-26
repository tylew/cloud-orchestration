import { Routes, Route } from 'react-router-dom'
import ProjectListScreen from '@/screens/ProjectListScreen'
import WorkspaceScreen from '@/screens/WorkspaceScreen'

export default function App() {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <Routes>
        <Route path="/" element={<ProjectListScreen />} />
        <Route path="/projects/:projectRefId" element={<WorkspaceScreen />} />
        <Route path="/projects/:projectRefId/resources/:slug" element={<WorkspaceScreen />} />
      </Routes>
    </div>
  )
}
