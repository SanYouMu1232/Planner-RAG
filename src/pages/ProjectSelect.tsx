import { Plus } from 'lucide-react'
import type { Project } from '../types'
import ProjectCard from '../components/ProjectCard'

interface Props {
  projects: Project[]
  onEnterProject: (projectId: string) => void
  onOpenCreate: () => void
  onRenameProject: (project: Project) => void
}

export default function ProjectSelect({ projects, onEnterProject, onOpenCreate, onRenameProject }: Props) {
  return (
    <main className="relative h-full w-full overflow-auto bg-canvas px-8 py-10">
      <div className="absolute inset-0 flex items-center justify-center opacity-50 pointer-events-none">
        <div className="h-[760px] w-[760px] rounded-full bg-gradient-to-br from-white via-[#eaf1f9] to-transparent blur-3xl" />
      </div>

      <div className="relative z-10 mx-auto flex min-h-[calc(100vh-136px)] w-full max-w-[1120px] flex-col items-center justify-center text-center">
        {projects.length === 0 ? (
          <section className="flex w-full max-w-[520px] flex-col items-center justify-center text-center page-fade">
            <button
              type="button"
              onClick={onOpenCreate}
              className="mb-12 flex h-64 w-64 items-center justify-center rounded-full border border-white/70 bg-[#f3f6fb]/88 text-[#1d5fc4] shadow-[0_28px_80px_rgba(9,52,89,0.10)] transition-all duration-200 hover:-translate-y-0.5 hover:bg-white hover:shadow-[0_32px_90px_rgba(9,52,89,0.14)] active:scale-[0.98]"
              aria-label="新建项目库"
            >
              <Plus size={54} strokeWidth={1.6} />
            </button>
            <h1 className="text-[32px] leading-[44px] font-light text-[#002440]">还没有项目库</h1>
            <p className="mt-3 text-base text-foreground-secondary">
              创建一个项目库，开始整理资料和进行 AI 问答。
            </p>
            <button onClick={onOpenCreate} className="mt-8 rounded-full bg-[#002440] px-9 py-4 text-base text-white shadow-card-hover transition-all duration-200 hover:-translate-y-0.5 hover:bg-[#073250] active:scale-[0.98] inline-flex items-center gap-2">
              <Plus size={18} />
              <span>新建项目库</span>
            </button>
          </section>
        ) : (
          <section className="flex w-full flex-col items-center text-center page-fade">
            <div className="mb-8">
              <h1 className="text-[32px] leading-[44px] font-light text-[#002440]">选择项目库</h1>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-foreground-secondary">
                选择一个项目库，开始基于资料进行问答、检索和方案文本生成。
              </p>
            </div>

            <div className="grid w-full max-w-[880px] grid-cols-1 justify-items-center gap-5 md:grid-cols-2 xl:grid-cols-3">
              {projects.map((project) => (
                <div key={project.id} className="w-full max-w-[320px]">
                  <ProjectCard project={project} onClick={() => onEnterProject(project.id)} onRename={() => onRenameProject(project)} />
                </div>
              ))}
            </div>

            <button onClick={onOpenCreate} className="mt-8 rounded-full bg-[#002440] px-8 py-4 text-base text-white shadow-card-hover transition-all duration-200 hover:-translate-y-0.5 hover:bg-[#073250] active:scale-[0.98] inline-flex items-center gap-2">
              <Plus size={18} />
              <span>新建项目库</span>
            </button>
          </section>
        )}
      </div>
    </main>
  )
}
