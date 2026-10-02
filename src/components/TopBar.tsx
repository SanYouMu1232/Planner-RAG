import { Plus, Settings, X } from 'lucide-react'
import type { Project } from '../types'

interface Props {
  activeProject?: Project
  openProjects: Project[]
  onSelectProject: (projectId: string) => void
  onCloseProject: (projectId: string) => void
  onSwitchProject: () => void
  onOpenApiConfig: () => void
}

export default function TopBar({
  activeProject,
  openProjects,
  onSelectProject,
  onCloseProject,
  onSwitchProject,
  onOpenApiConfig,
}: Props) {
  return (
    <header className="topbar flex h-16 shrink-0 items-center gap-5 px-6 shadow-topbar">
      <button
        type="button"
        onClick={onSwitchProject}
        className="shrink-0 whitespace-nowrap text-2xl font-semibold tracking-tight text-white transition-opacity hover:opacity-90"
        title="返回项目库选择页"
      >
        规划智库
      </button>

      <div className="flex min-w-0 flex-1 items-end gap-1.5 self-end overflow-x-auto browser-tabs pr-2">
        {openProjects.map((project) => {
          const active = activeProject?.id === project.id
          return (
            <div
              key={project.id}
              className={`group mb-0 flex h-11 w-[238px] shrink-0 items-center gap-2 rounded-t-xl border border-b-0 px-3 transition-all duration-200 ${
                active
                  ? 'border-white/35 bg-white text-[#0b2440] shadow-[0_-2px_14px_rgba(255,255,255,0.14)]'
                  : 'border-white/25 bg-white/16 text-white/90 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] hover:bg-white/24 hover:text-white'
              }`}
            >
              <button
                type="button"
                onClick={() => onSelectProject(project.id)}
                className="min-w-0 flex-1 truncate text-left text-sm font-medium"
                title={project.name}
              >
                {project.name}
              </button>
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation()
                  onCloseProject(project.id)
                }}
                className={`rounded p-1 transition-colors ${active ? 'text-slate-500 hover:bg-slate-200 hover:text-slate-800' : 'text-white/45 hover:bg-white/10 hover:text-white'}`}
                title="关闭项目库标签"
              >
                <X size={13} />
              </button>
            </div>
          )
        })}
        {openProjects.length > 0 && (
          <button
            type="button"
            onClick={onSwitchProject}
            className="mb-1 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-white/25 bg-white/16 text-white/90 transition-all hover:bg-white/24 hover:text-white"
            title="打开或创建更多项目库"
          >
            <Plus size={16} />
          </button>
        )}
      </div>

      <div className="ml-auto flex shrink-0 items-center gap-3 self-center">
        <button
          type="button"
          onClick={onSwitchProject}
          className="rounded-md bg-white/10 px-4 py-2 text-sm text-[#b7c8dc] transition-colors hover:bg-white/15 hover:text-white"
        >
          切换项目库
        </button>
        <button
          type="button"
          onClick={onOpenApiConfig}
          className="inline-flex items-center gap-2 rounded-md bg-white/10 px-4 py-2 text-sm text-[#b7c8dc] transition-colors hover:bg-white/15 hover:text-white"
        >
          <Settings size={16} />
          <span>API 配置</span>
        </button>
      </div>
    </header>
  )
}
