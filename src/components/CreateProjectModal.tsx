import { useState } from 'react'
import { X } from 'lucide-react'

interface CreateProjectPayload {
  name: string
  projectType: string
  region: string
  description: string
}

interface Props {
  open: boolean
  onClose: () => void
  onCreate: (payload: CreateProjectPayload) => void
}

const projectTypes = ['总体规划', '详细规划', '专项规划', '城市设计', '城市更新', '其他']

export default function CreateProjectModal({ open, onClose, onCreate }: Props) {
  const [name, setName] = useState('')
  const [projectType, setProjectType] = useState('总体规划')
  const [region, setRegion] = useState('')
  const [description, setDescription] = useState('')

  if (!open) return null

  const reset = () => {
    setName('')
    setProjectType('总体规划')
    setRegion('')
    setDescription('')
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) return
    onCreate({
      name: trimmed,
      projectType,
      region: region.trim(),
      description: description.trim(),
    })
    reset()
  }

  const handleClose = () => {
    reset()
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40" />

      <div className="relative w-full max-w-[550px] overflow-hidden rounded-card border border-edge bg-white shadow-xl animate-in">
        <div className="flex items-center justify-between border-b border-edge bg-canvas px-6 py-4">
          <h2 className="text-xl font-semibold text-foreground">新建项目库</h2>
          <button
            onClick={handleClose}
            className="p-1 rounded-card text-foreground-muted hover:text-foreground hover:bg-canvas"
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="space-y-5 p-6">
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">
                项目库名称 <span className="text-status-repealed">*</span>
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="请输入项目库名称"
                className="input-styled w-full"
                autoFocus
              />
            </div>

            <div className="grid grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">项目类型</label>
                <select
                  value={projectType}
                  onChange={(e) => setProjectType(e.target.value)}
                  className="input-styled w-full"
                >
                  {projectTypes.map((type) => (
                    <option key={type}>{type}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">项目地区</label>
                <input
                  type="text"
                  value={region}
                  onChange={(e) => setRegion(e.target.value)}
                  placeholder="请输入地区"
                  className="input-styled w-full"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">项目备注</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="可填写项目背景、工作重点或资料情况"
                rows={4}
                className="input-styled w-full resize-none py-3"
              />
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 border-t border-edge bg-canvas px-6 py-4">
            <button type="button" onClick={handleClose} className="btn-secondary">取消</button>
            <button type="submit" disabled={!name.trim()} className="btn-primary">创建</button>
          </div>
        </form>
      </div>
    </div>
  )
}
