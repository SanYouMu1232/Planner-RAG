import { useEffect, useState, type FormEvent } from 'react'
import { X } from 'lucide-react'
import type { Project } from '../types'

interface Props {
  project: Project | null
  onClose: () => void
  onRename: (projectId: string, name: string) => void
}

export default function RenameProjectModal({ project, onClose, onRename }: Props) {
  const [name, setName] = useState('')

  useEffect(() => {
    setName(project?.name ?? '')
  }, [project])

  if (!project) return null

  const trimmed = name.trim()

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (!trimmed || trimmed === project.name) return
    onRename(project.id, trimmed)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40" />
      <div className="relative w-full max-w-[460px] overflow-hidden rounded-card border border-edge bg-white shadow-xl modal-pop">
        <div className="flex items-center justify-between border-b border-edge bg-canvas px-6 py-4">
          <h2 className="text-lg font-semibold text-foreground">项目库改名</h2>
          <button onClick={onClose} className="rounded-card p-1 text-foreground-muted hover:bg-canvas hover:text-foreground">
            <X size={20} />
          </button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="space-y-3 p-6">
            <label className="block">
              <span className="mb-1.5 block text-sm font-medium text-foreground">项目库名称</span>
              <input value={name} onChange={(event) => setName(event.target.value)} className="input-styled w-full" autoFocus />
            </label>
          </div>
          <div className="flex justify-end gap-3 border-t border-edge bg-canvas px-6 py-4">
            <button type="button" onClick={onClose} className="btn-secondary">取消</button>
            <button type="submit" disabled={!trimmed || trimmed === project.name} className="btn-primary">保存</button>
          </div>
        </form>
      </div>
    </div>
  )
}
