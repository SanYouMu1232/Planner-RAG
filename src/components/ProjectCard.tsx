import { ArrowRight, Building2, Clock3, FileText, MapPin, Pencil } from 'lucide-react'
import type { Project } from '../types'

interface Props {
  project: Project
  onClick: () => void
  onRename?: () => void
}

export default function ProjectCard({ project, onClick, onRename }: Props) {
  return (
    <button
      onClick={onClick}
      className="group relative min-h-[220px] w-full overflow-hidden rounded-xl border border-edge bg-white p-6 text-left shadow-card transition-all duration-200 hover:-translate-y-1 hover:border-primary/25 hover:shadow-card-hover"
    >
      <div className="absolute inset-x-0 top-0 h-1 bg-[#0060ac] opacity-0 transition-opacity duration-200 group-hover:opacity-100" />

      <div className="flex items-start justify-between gap-3">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-[rgba(27,58,87,0.1)] text-[#002440]">
          <Building2 size={20} />
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-[#f3f4f5] px-3 py-1 text-xs text-foreground-secondary">
            {project.projectType}
          </span>
          {onRename && (
            <span
              role="button"
              tabIndex={0}
              onClick={(event) => {
                event.stopPropagation()
                onRename()
              }}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault()
                  event.stopPropagation()
                  onRename()
                }
              }}
              className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-canvas text-foreground-muted transition-colors hover:bg-primary-light hover:text-primary"
              title="项目库改名"
            >
              <Pencil size={14} />
            </span>
          )}
        </div>
      </div>

      <h3 className="mt-5 min-h-[56px] text-xl font-light leading-7 text-foreground line-clamp-2">
        {project.name}
      </h3>

      <div className="mt-2 flex items-center gap-1.5 text-xs text-foreground-muted">
        <MapPin size={13} />
        <span>{project.region}</span>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3 rounded-lg bg-canvas px-4 py-3">
        <div className="flex items-center gap-2">
          <FileText size={14} className="text-primary" />
          <div>
            <div className="text-xs text-foreground-muted">资料数量</div>
            <div className="mt-0.5 text-sm text-foreground">{project.docCount} 份</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Clock3 size={14} className="text-primary" />
          <div>
            <div className="text-xs text-foreground-muted">最近使用</div>
            <div className="mt-0.5 text-sm text-foreground">{project.lastUsed}</div>
          </div>
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between border-t border-edge-light pt-4 text-xs text-foreground-muted">
        <span>最近问答：{project.lastQaTime}</span>
        <span className="inline-flex items-center gap-1 text-primary transition-transform group-hover:translate-x-1">
          进入工作台 <ArrowRight size={13} />
        </span>
      </div>
    </button>
  )
}
