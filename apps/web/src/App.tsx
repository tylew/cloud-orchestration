import { Routes, Route } from 'react-router-dom'

function Placeholder({ name }: { name: string }) {
  return <div className="p-8 text-zinc-400">{name} — coming soon</div>
}

export default function App() {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <Routes>
        <Route path="/" element={<Placeholder name="Project List" />} />
        <Route path="/projects/:projectRefId" element={<Placeholder name="Workspace" />} />
        <Route path="/projects/:projectRefId/resources/:slug" element={<Placeholder name="Resource Config" />} />
      </Routes>
    </div>
  )
}
