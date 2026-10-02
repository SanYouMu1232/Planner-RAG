import { Search } from 'lucide-react'
import type { Project } from '../types'

interface Props {
  project: Project
}

export default function SearchPage({ project }: Props) {
  return (
    <main className="relative flex-1 overflow-auto bg-canvas">
      <div className="absolute inset-x-0 top-0 h-80 bg-gradient-to-b from-edge/50 to-transparent pointer-events-none" />

      <div className="relative mx-auto flex min-h-full max-w-[896px] flex-col px-8 py-20">
        <section className="text-center">
          <div className="mx-auto mb-8 flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-primary-light to-white text-primary shadow-card">
            <Search size={36} strokeWidth={1.4} />
          </div>
          <h2 className="text-[32px] leading-[44px] font-light text-[#002440]">
            政策查找
          </h2>
          <p className="mt-2 text-base text-foreground-secondary">
            输入关键词搜索公开政策、技术标准与行业资料，结果可选择加入知识库
          </p>
        </section>

        {/* Search input */}
        <section className="mt-10">
          <div className="relative">
            <Search size={20} className="absolute left-4 top-1/2 -translate-y-1/2 text-foreground-muted" />
            <input
              type="text"
              placeholder="搜索政策、规范、标准… 例如：XX市 控制性详细规划 最新政策"
              className="input-styled w-full pl-11 text-base"
            />
          </div>
          <p className="mt-3 text-center text-xs text-foreground-muted">
            当前搜索项目库：{project.name}
          </p>
        </section>

        {/* Suggestions */}
        <section className="mt-10">
          <h3 className="px-1 text-sm text-foreground-muted">推荐搜索</h3>
          <div className="mt-4 flex flex-wrap gap-3">
            {[
              '国土空间规划 最新政策',
              '控制性详细规划 编制技术指南',
              '城市更新条例 解读',
              '居住区规划设计标准',
              '深圳市 城市规划标准',
            ].map((kw) => (
              <button
                key={kw}
                className="rounded-full border border-edge bg-white px-5 py-2.5 text-sm text-foreground-secondary shadow-card transition hover:border-primary/30 hover:text-primary"
              >
                {kw}
              </button>
            ))}
          </div>
        </section>

        {/* Empty results placeholder */}
        <section className="mt-14 flex flex-1 flex-col items-center justify-center text-center">
          <div className="rounded-card border border-dashed border-edge bg-white/60 p-12">
            <p className="text-base text-foreground-secondary">
              输入关键词后，系统将从公开来源检索相关政策与标准
            </p>
            <p className="mt-2 text-sm text-foreground-muted">
              搜索结果不会自动入库，需手动选择加入通用库或当前项目库
            </p>
          </div>
        </section>

        <p className="mt-auto pt-16 text-center text-xs text-foreground-muted">
          搜索功能为静态原型。实际使用时需配置联网搜索 API。
        </p>
      </div>
    </main>
  )
}
