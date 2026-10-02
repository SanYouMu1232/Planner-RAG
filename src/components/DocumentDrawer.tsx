import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { X, FileText, Calendar, User, Globe, Loader2 } from 'lucide-react'
import type { Citation, KnowledgeDocument } from '../types'
import * as api from '../api/client'
import { locateCitation, parseTableRows } from '../lib/citationLocation'
import FileTypeIcon from './FileTypeIcon'
import StatusBadge from './StatusBadge'

interface Props {
  document: KnowledgeDocument | null
  citation?: Citation | null
  onClose: () => void
}

export default function DocumentDrawer({ document: doc, citation, onClose }: Props) {
  const [loading, setLoading] = useState(false)
  const [chunks, setChunks] = useState<api.DocumentChunk[]>([])
  const [error, setError] = useState('')
  const [loadedId, setLoadedId] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)
  const targetRef = useRef<HTMLElement>(null)
  const ready = !!doc && loadedId === doc.id && !loading
  const location = useMemo(() => locateCitation(chunks, citation), [chunks, citation])

  useEffect(() => {
    if (!doc) return

    let cancelled = false
    const controller = new AbortController()
    setLoading(true)
    setError('')
    setChunks([])

    api.getDocumentChunks(doc.id, controller.signal)
      .then((chunks) => {
        if (cancelled) return
        setChunks(chunks)
      })
      .catch((err) => {
        if (cancelled) return
        setError(err instanceof Error ? err.message : '原文切片加载失败')
      })
      .finally(() => {
        if (!cancelled) { setLoadedId(doc.id); setLoading(false) }
      })

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [doc?.id])

  useLayoutEffect(() => {
    if (!ready || !scrollRef.current) return
    const container = scrollRef.current
    const target = targetRef.current
    // Use unscaled layout coordinates: the opening animation scales the drawer.
    // Scroll only this drawer so the underlying conversation stays in place.
    container.scrollTop = target
      ? Math.max(0, target.offsetTop - 16)
      : 0
  }, [ready, doc?.id, citation, location?.chunkId])

  const summaryText = useMemo(() => {
    if (!doc) return ''
    return doc.summary?.trim() || '暂未生成摘要。'
  }, [doc])

  if (!doc) return null

  return (
    <>
      {/* Backdrop */}
      {/* 点击遮罩不会关闭抽屉，避免查看原文时误退出。 */}
      <div className="fixed inset-0 z-40 bg-black/30" />

      {/* Drawer */}
      <div className="fixed inset-y-0 right-0 z-50 w-full max-w-[600px] bg-white shadow-2xl flex flex-col animate-in">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-edge px-6 py-5 shrink-0">
          <div className="flex-1 min-w-0 mr-4">
            <div className="flex items-center gap-2.5 mb-2">
              <FileTypeIcon type={doc.fileType} size={22} />
              <h2 className="text-lg font-semibold text-foreground leading-6">
                {doc.fileName}
              </h2>
            </div>
            <div className="flex items-center gap-3 text-xs text-foreground-muted">
              <StatusBadge status={doc.policyStatus} />
              <span className="flex items-center gap-1">
                <Calendar size={12} />
                {doc.publishDate}
              </span>
              <span className="flex items-center gap-1">
                <User size={12} />
                {doc.source}
              </span>
              <span className="flex items-center gap-1">
                <Globe size={12} />
                {doc.category}
              </span>
            </div>
          </div>
          <button
            aria-label="关闭原文"
            onClick={onClose}
            className="p-2 rounded-card text-foreground-muted hover:text-foreground hover:bg-canvas shrink-0"
          >
            <X size={20} />
          </button>
        </div>

        {/* Metadata card */}
        <div className="border-b border-edge-light bg-canvas px-6 py-4 shrink-0">
          <div className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
            <div>
              <span className="text-foreground-muted">文件名</span>
              <p className="text-foreground mt-0.5 truncate"><a href={api.getDocumentFileUrl(doc, chunks.find(chunk => chunk.id === location?.chunkId)?.pageStart)} target="_blank" rel="noopener noreferrer" className="hover:text-primary hover:underline" title={doc.fileType === 'web' ? '打开原始网页' : doc.fileType === 'pdf' ? '打开原始 PDF（有页码时定位到引用页）' : '下载原始文件'}>{doc.fileName}</a></p>
            </div>
            <div>
              <span className="text-foreground-muted">来源</span>
              <p className="text-foreground mt-0.5">{doc.source}</p>
            </div>
            <div>
              <span className="text-foreground-muted">发布时间</span>
              <p className="text-foreground mt-0.5">{doc.publishDate}</p>
            </div>
            <div>
              <span className="text-foreground-muted">入库时间</span>
              <p className="text-foreground mt-0.5">{doc.ingestTime}</p>
            </div>
            <div>
              <span className="text-foreground-muted">分类</span>
              <p className="text-foreground mt-0.5">{doc.category}</p>
            </div>
            <div>
              <span className="text-foreground-muted">文件类型</span>
              <p className="text-foreground mt-0.5">{doc.fileType.toUpperCase()}</p>
            </div>
          </div>
        </div>

        {/* Original text */}
        <div ref={scrollRef} className="relative flex-1 overflow-auto px-6 py-5">
          <div className="flex items-center gap-2 mb-4">
            <FileText size={16} className="text-foreground-muted" />
            <h3 className="text-sm font-semibold text-foreground">原文内容</h3>
            <span className="text-xs text-foreground-muted" role="status">{!ready ? '（正在加载原文）' : citation ? location ? `（已定位${location.match === 'section' ? '相关章节' : `引用 [${citation.number}]`}）` : '（未匹配到引用位置，显示全文）' : '（真实切片预览）'}</span>
          </div>
          <div className="space-y-4">
            {!ready && <div className="rounded-card border border-edge bg-canvas p-5 text-sm">正在加载真实原文切片…</div>}
            {ready && error && <div role="alert" className="rounded-card border border-red-200 bg-red-50 p-5 text-sm text-red-700">{error}</div>}
            {ready && !error && chunks.length === 0 && <div className="rounded-card border border-edge bg-canvas p-5 text-sm">当前文档暂无可展示的正文切片。扫描件请在上传时选择云端版面/表格解析。</div>}
            {ready && !error && chunks.filter(chunk => chunk.chunkType !== 'parent').map((chunk) => <ChunkPreview key={chunk.id} chunk={chunk} active={chunk.id === location?.chunkId} targetRef={targetRef} />)}
          </div>

          {loading && (
            <div className="mt-3 flex items-center justify-center gap-2 text-xs text-foreground-muted">
              <Loader2 size={14} className="animate-spin" />
              正在读取文档内容…
            </div>
          )}

          {/* Summary */}
          <div className="mt-5 rounded-card bg-primary-light/50 p-4 border border-primary/10">
            <p className="text-xs text-foreground-muted mb-1">AI 摘要</p>
            <p className="text-sm text-foreground-secondary leading-relaxed">{summaryText}</p>
          </div>

          <p className="mt-6 text-xs text-foreground-muted text-center">
            以上内容来自后端解析后的真实切片，可用于问答引用与条款核验。
          </p>
        </div>
      </div>
    </>
  )
}


function ChunkPreview({ chunk, active, targetRef }: { chunk: api.DocumentChunk; active: boolean; targetRef: React.RefObject<HTMLElement> }) {
  const title = chunk.headingPath || chunk.section || `内容块 #${chunk.readingOrder || chunk.chunkIndex}`
  const page = chunk.pageStart ? ` · 第 ${chunk.pageStart}${chunk.pageEnd && chunk.pageEnd !== chunk.pageStart ? `-${chunk.pageEnd}` : ''} 页` : ''
  const rows = chunk.chunkType === 'table' ? parseTableRows(chunk.tableJson) : null
  return <article ref={active ? targetRef : undefined} data-chunk-id={chunk.id} aria-current={active ? 'location' : undefined} className={`rounded-card border p-4 ${active ? 'border-primary bg-primary-light/60 ring-2 ring-primary/20' : 'border-edge bg-canvas'}`}><p className="mb-2 text-xs font-medium text-foreground-muted">【{title}{page} · 阅读序 {chunk.readingOrder}】{active && <span className="ml-2 text-primary">引用位置</span>}</p>{rows ? <div className="overflow-auto"><table className="min-w-full border-collapse text-sm"><tbody>{rows.map((row, ri) => <tr key={ri}>{row.map((cell, ci) => <td key={ci} className={`border border-edge px-2 py-1.5 align-top ${ri===0?'bg-white font-medium':''}`}>{cell}</td>)}</tr>)}</tbody></table></div> : <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-foreground">{chunk.text}</pre>}</article>
}
