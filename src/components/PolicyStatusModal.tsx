import { useRef, useState, type FormEvent } from 'react'
import { Loader2, X } from 'lucide-react'
import type { KnowledgeDocument, PolicyStatus } from '../types'
import { policyStatusOptions } from '../lib/policyStatus'
import StatusBadge from './StatusBadge'

interface Props {
  document: KnowledgeDocument
  onClose: () => void
  onSave: (docId: string, status: PolicyStatus) => Promise<void>
}

export default function PolicyStatusModal({ document: doc, onClose, onSave }: Props) {
  const [status, setStatus] = useState<PolicyStatus>(doc.policyStatus)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const savingRef = useRef(false)

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (savingRef.current || status === doc.policyStatus) return
    savingRef.current = true
    setSaving(true)
    setError('')
    try {
      await onSave(doc.id, status)
      onClose()
    } catch (error) {
      setError(error instanceof Error ? error.message : '保存失败，请稍后重试。')
    } finally {
      savingRef.current = false
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40" />
      <div role="dialog" aria-modal="true" aria-labelledby="policy-status-title" aria-busy={saving} className="relative w-full max-w-[460px] overflow-hidden rounded-card border border-edge bg-white shadow-xl modal-pop">
        <div className="flex items-center justify-between border-b border-edge bg-canvas px-6 py-4">
          <h2 id="policy-status-title" className="text-lg font-semibold text-foreground">修改效力状态</h2>
          <button type="button" onClick={onClose} disabled={saving} aria-label="关闭效力状态编辑" className="rounded-card p-1 text-foreground-muted hover:bg-canvas hover:text-foreground disabled:opacity-50">
            <X size={20} />
          </button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="space-y-4 p-6">
            <p className="break-words text-sm font-medium text-foreground">{doc.fileName}</p>
            <div className="flex items-center gap-2 text-sm text-foreground-secondary">当前效力状态<StatusBadge status={doc.policyStatus} /></div>
            <label className="block">
              <span className="mb-1.5 block text-sm font-medium text-foreground">效力状态</span>
              <select value={status} onChange={event => { setStatus(event.target.value as PolicyStatus); setError('') }} disabled={saving} className="input-styled w-full" autoFocus>
                {policyStatusOptions.map(option => <option key={option.value} value={option.value}>{option.value === 'unknown' ? '未知（待核验）' : option.label}</option>)}
              </select>
            </label>
            <p className="text-xs leading-5 text-foreground-muted">请根据文件发布、修订或废止信息选择；尚未核实可保留“未知”。保存后，原文详情和引用标签会显示最新状态。</p>
            {error && <p role="alert" className="rounded-card bg-red-50 p-3 text-sm text-red-700">{error}</p>}
          </div>
          <div className="flex justify-end gap-3 border-t border-edge bg-canvas px-6 py-4">
            <button type="button" onClick={onClose} disabled={saving} className="btn-secondary">取消</button>
            <button type="submit" disabled={saving || status === doc.policyStatus} className="btn-primary">{saving && <Loader2 size={16} className="animate-spin" />}{saving ? '保存中…' : '保存'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}
