import { useEffect, useState } from 'react'
import { CheckCircle, Loader2, Search, X } from 'lucide-react'
import type { CandidateDocument, KnowledgeBaseType, KnowledgeDocument } from '../types'
import * as api from '../api/client'

interface Props {
  open: boolean
  defaultKeyword?: string
  projectId: string
  onClose: () => void
  onAddDocument: (doc: KnowledgeDocument) => void
  onInserted?: () => void
}

type SearchState = 'idle' | 'searching' | 'results'
type IngestingMap = Record<string, KnowledgeBaseType | 'done' | undefined>

export default function ResearchDrawer({
  open,
  defaultKeyword = '',
  projectId,
  onClose,
  onAddDocument,
  onInserted,
}: Props) {
  const [keyword, setKeyword] = useState(defaultKeyword)
  const [target, setTarget] = useState('不限')
  const [region, setRegion] = useState('')
  const [timeRange, setTimeRange] = useState('')
  const [generateSummary, setGenerateSummary] = useState(false)
  const [searchState, setSearchState] = useState<SearchState>('idle')
  const [ingesting, setIngesting] = useState<IngestingMap>({})

  const [candidates, setCandidates] = useState<CandidateDocument[]>([])

  useEffect(() => {
    if (open) {
      setKeyword(defaultKeyword)
      setSearchState(defaultKeyword ? 'results' : 'idle')
      setGenerateSummary(false)
      setIngesting({})
    }
  }, [defaultKeyword, open])

  if (!open) return null

  const handleSearch = async () => {
    setSearchState('searching')
    try {
      const results = await api.searchCandidates({
        keyword: keyword || '城市规划',
        target,
        region,
        time_range: timeRange,
      })
      setCandidates(results)
      setSearchState('results')
    } catch {
      setSearchState('results')
    }
  }

  const handleAdd = async (candidate: CandidateDocument, knowledgeBase: KnowledgeBaseType) => {
    setIngesting((prev) => ({ ...prev, [candidate.id]: knowledgeBase }))
    try {
      const doc = await api.ingestCandidate(candidate.id, {
        knowledge_base: knowledgeBase,
        project_id: knowledgeBase === 'project' ? projectId : undefined,
        generate_summary: generateSummary,
      })
      const now = new Date().toISOString().slice(0, 10)
      onAddDocument({
        id: doc.id,
        fileName: doc.fileName,
        fileType: doc.fileType,
        category: doc.category,
        tags: doc.tags,
        source: doc.source,
        publishDate: doc.publishDate,
        policyStatus: doc.policyStatus,
        ingestTime: now,
        parseStatus: doc.parseStatus,
        summaryStatus: doc.summaryStatus,
        knowledgeBase: doc.knowledgeBase,
        projectId: doc.projectId,
        summary: doc.summary,
      })
    } catch (error) {
      alert(error instanceof Error ? error.message : '候选资料入库失败，请确认后端已启动或搜索结果仍有效。')
      setIngesting((prev) => ({ ...prev, [candidate.id]: undefined }))
      return
    }
    setIngesting((prev) => ({ ...prev, [candidate.id]: 'done' }))
    onInserted?.()
  }

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/25" />
      <aside className="fixed inset-y-0 right-0 z-50 flex w-full max-w-[720px] flex-col bg-white shadow-2xl drawer-slide">
        <div className="flex items-start justify-between border-b border-edge px-6 py-5">
          <div>
            <h2 className="text-lg font-semibold text-foreground">网络检索资料</h2>
            <p className="mt-1 text-sm text-foreground-secondary">
              搜索结果仅作为候选资料，确认入库后才能参与问答和引用。
            </p>
          </div>
          <button onClick={onClose} className="rounded-card p-2 text-foreground-muted hover:bg-canvas hover:text-foreground">
            <X size={20} />
          </button>
        </div>

        <div className="border-b border-edge bg-canvas px-6 py-5">
          <div className="grid grid-cols-2 gap-4">
            <label className="col-span-2 block">
              <span className="mb-1 block text-sm text-foreground-secondary">检索关键词</span>
              <div className="relative">
                <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-foreground-muted" />
                <input
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                  className="input-styled w-full pl-10"
                  placeholder="请输入政策、标准、导则或案例关键词"
                />
              </div>
            </label>
            <label className="block">
              <span className="mb-1 block text-sm text-foreground-secondary">检索目标</span>
              <select value={target} onChange={(e) => setTarget(e.target.value)} className="input-styled w-full">
                {['政策法规', '技术标准', '规划导则', '案例参考', '不限'].map((item) => <option key={item}>{item}</option>)}
              </select>
            </label>
            <label className="block">
              <span className="mb-1 block text-sm text-foreground-secondary">可选地区</span>
              <input value={region} onChange={(e) => setRegion(e.target.value)} className="input-styled w-full" placeholder="例如：XX市" />
            </label>
            <label className="block">
              <span className="mb-1 block text-sm text-foreground-secondary">可选时间范围</span>
              <input value={timeRange} onChange={(e) => setTimeRange(e.target.value)} className="input-styled w-full" placeholder="例如：近三年" />
            </label>
            <label className="flex items-start gap-2 rounded-card border border-edge bg-white px-3 py-3 text-sm text-foreground-secondary">
              <input type="checkbox" checked={generateSummary} onChange={(e) => setGenerateSummary(e.target.checked)} className="mt-0.5 h-4 w-4" />
              <span>
                <span className="font-medium text-foreground">是否生成摘要</span>
                <span className="block text-xs text-foreground-muted">默认不生成，入库后可按需生成。</span>
              </span>
            </label>
            <div className="flex items-end justify-end">
              <button onClick={handleSearch} className="btn-primary w-full">
                <Search size={16} />
                <span>搜索</span>
              </button>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-auto p-6">
          {searchState === 'idle' && (
            <div className="rounded-card border border-dashed border-edge bg-canvas p-10 text-center text-sm text-foreground-secondary">
              输入关键词后，可检索政策法规、技术标准、规划导则和案例参考。
            </div>
          )}
          {searchState === 'searching' && (
            <div className="flex items-center justify-center gap-3 rounded-card border border-edge bg-canvas p-10 text-sm text-foreground-secondary">
              <Loader2 size={18} className="animate-spin text-primary" />
              正在检索候选资料…
            </div>
          )}
          {searchState === 'results' && (
            <div className="space-y-4">
              {candidates.length === 0 ? (
                <div className="rounded-card border border-dashed border-edge bg-canvas p-10 text-center text-sm text-foreground-secondary">
                  未搜索到候选资料，请尝试其他关键词。
                </div>
              ) : (
                candidates.map((item) => {
                const state = ingesting[item.id]
                return (
                  <article key={item.id} className="rounded-card border border-edge bg-white p-5 shadow-card">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <h3 className="text-base font-semibold text-foreground">{item.title}</h3>
                        <p className="mt-1 text-xs text-foreground-muted">
                          {item.source} · {item.publishDate} · {item.credibility}
                        </p>
                      </div>
                      <span className="rounded-full bg-primary-light px-2.5 py-1 text-xs text-primary">{item.category}</span>
                    </div>
                    <p className="mt-3 text-sm leading-6 text-foreground-secondary">{item.summary}</p>
                    <div className="mt-3 rounded-card bg-canvas px-3 py-2 text-xs text-foreground-secondary">
                      推荐入库理由：{item.reason}
                    </div>
                    <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
                      <span className="text-xs text-foreground-muted">{generateSummary ? '入库时生成摘要' : '入库时不生成摘要'}</span>
                      <div className="flex flex-wrap items-center justify-end gap-2">
                        {state === 'done' ? (
                          <span className="inline-flex items-center gap-2 rounded-card bg-status-active/10 px-3 py-2 text-sm text-status-active">
                            <CheckCircle size={15} /> 资料已入库
                          </span>
                        ) : state ? (
                          <span className="inline-flex items-center gap-2 rounded-card bg-primary-light px-3 py-2 text-sm text-primary">
                            <Loader2 size={15} className="animate-spin" /> 入库中
                          </span>
                        ) : (
                          <>
                            <button onClick={() => handleAdd(item, 'project')} className="btn-secondary text-primary">加入当前项目知识库</button>
                            <button onClick={() => handleAdd(item, 'general')} className="btn-secondary">加入通用知识库</button>
                            <button className="btn-ghost">忽略</button>
                          </>
                        )}
                      </div>
                    </div>
                  </article>
                )
              })
            )}
            </div>
          )}
        </div>
      </aside>
    </>
  )
}
