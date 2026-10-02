import { FileText, X } from 'lucide-react'
import type { KnowledgeDocument } from '../types'
import FileTypeIcon from './FileTypeIcon'
import StatusBadge from './StatusBadge'

interface Props {
  document: KnowledgeDocument | null
  onClose: () => void
}

export default function SummaryDrawer({ document: doc, onClose }: Props) {
  if (!doc) return null

  const summary = doc.summary?.trim()

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/30" />
      <div className="fixed inset-y-0 right-0 z-50 flex w-full max-w-[520px] flex-col bg-white shadow-2xl animate-in">
        <div className="flex shrink-0 items-start justify-between border-b border-edge px-6 py-5">
          <div className="min-w-0 flex-1 pr-4">
            <div className="mb-2 flex items-center gap-2.5">
              <FileTypeIcon type={doc.fileType} size={22} />
              <h2 className="truncate text-lg font-semibold leading-6 text-foreground">{doc.fileName}</h2>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-xs text-foreground-muted">
              <StatusBadge status={doc.policyStatus} />
              <span>{doc.category}</span>
              <span>入库：{doc.ingestTime}</span>
            </div>
          </div>
          <button onClick={onClose} className="shrink-0 rounded-card p-2 text-foreground-muted hover:bg-canvas hover:text-foreground">
            <X size={20} />
          </button>
        </div>

        <div className="flex-1 overflow-auto px-6 py-5">
          <div className="mb-4 flex items-center gap-2">
            <FileText size={16} className="text-foreground-muted" />
            <h3 className="text-sm font-semibold text-foreground">文档摘要</h3>
          </div>
          {summary ? (
            <div className="rounded-card border border-edge bg-canvas p-5 text-sm leading-7 text-foreground-secondary whitespace-pre-wrap">
              {summary}
            </div>
          ) : (
            <div className="rounded-card border border-dashed border-edge bg-canvas p-8 text-center text-sm text-foreground-secondary">
              该文档暂未生成摘要。
            </div>
          )}
        </div>
      </div>
    </>
  )
}
