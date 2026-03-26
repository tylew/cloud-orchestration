import { useState, useCallback } from 'react'

type SplitPaneProps = {
  left: React.ReactNode
  right: React.ReactNode
  defaultLeftWidth?: number
}

export default function SplitPane({ left, right, defaultLeftWidth = 50 }: SplitPaneProps) {
  const [leftWidth, setLeftWidth] = useState(defaultLeftWidth)
  const [dragging, setDragging] = useState(false)

  const handleMouseDown = useCallback(() => {
    setDragging(true)
    const handleMouseMove = (e: MouseEvent) => {
      const pct = (e.clientX / window.innerWidth) * 100
      setLeftWidth(Math.min(Math.max(pct, 25), 75))
    }
    const handleMouseUp = () => {
      setDragging(false)
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }, [])

  return (
    <div className="flex h-full">
      <div style={{ width: `${leftWidth}%` }} className="overflow-auto">
        {left}
      </div>
      <div
        className={`w-1 cursor-col-resize hover:bg-blue-500/50 ${dragging ? 'bg-blue-500/50' : 'bg-zinc-800'}`}
        onMouseDown={handleMouseDown}
      />
      <div style={{ width: `${100 - leftWidth}%` }} className="overflow-auto">
        {right}
      </div>
    </div>
  )
}
