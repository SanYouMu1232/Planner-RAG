import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { Check, Filter, RefreshCw, Search, Trash2, Upload, X } from 'lucide-react'
import type { KnowledgeBaseType, KnowledgeDocument, ParseStatus, PolicyStatus, Project } from '../types'
import * as api from '../api/client'
import FileTypeIcon from '../components/FileTypeIcon'
import UploadModal from '../components/UploadModal'
import DocumentDrawer from '../components/DocumentDrawer'
import SummaryDrawer from '../components/SummaryDrawer'
import ResearchDrawer from '../components/ResearchDrawer'
import PolicyStatusModal from '../components/PolicyStatusModal'
import { getPolicyStatusDisplay } from '../lib/policyStatus'

interface Props {
  project: Project
  documents: KnowledgeDocument[]
  onAddDocument: (doc: KnowledgeDocument) => void
  onDeleteDocument: (docId: string) => void
  onUpdateDocument: (docId: string, patch: Partial<KnowledgeDocument>) => void
  onUpdatePolicyStatus: (docId: string, status: PolicyStatus) => Promise<void>
  onAskFromDocument: (doc: KnowledgeDocument) => void
}

const tabs: { key: KnowledgeBaseType; label: string; desc: string }[] = [
  {
    key: 'project',
    label: '当前项目知识库',
    desc: '存放当前项目专属资料，如甲方任务书、上位规划、会议纪要、评审意见、控规图则说明等。这些资料只服务于当前项目。',
  },
  {
    key: 'general',
    label: '通用知识库',
    desc: '存放跨项目复用资料，如国家政策、省市政策、技术标准、规划导则、公开案例等。所有项目都可以调用通用知识库。',
  },
]

const parseStatusMap: Record<ParseStatus, { label: string; className: string }> = {
  uploading: { label: '上传中', className: 'bg-blue-50 text-blue-700' },
  parsing: { label: '解析中', className: 'bg-amber-50 text-amber-700' },
  summarizing: { label: '摘要生成中', className: 'bg-amber-50 text-amber-700' },
  vectorizing: { label: '向量化中', className: 'bg-purple-50 text-purple-700' },
  ready: { label: '已入库', className: 'bg-green-50 text-green-700' },
  failed: { label: '解析失败', className: 'bg-red-50 text-red-700' },
}

function hasGeneratedSummary(doc: KnowledgeDocument) {
  return doc.summaryStatus === 'generated' && Boolean(doc.summary?.trim())
}

export default function KnowledgeBase({
  project,
  documents,
  onAddDocument,
  onDeleteDocument,
  onUpdateDocument,
  onUpdatePolicyStatus,
  onAskFromDocument,
}: Props) {
  const [activeTab, setActiveTab] = useState<KnowledgeBaseType>('project')
  const [showUpload, setShowUpload] = useState(false)
  const [showResearch, setShowResearch] = useState(false)
  const [selectedDoc, setSelectedDoc] = useState<KnowledgeDocument | null>(null)
  const [selectedSummaryDoc, setSelectedSummaryDoc] = useState<KnowledgeDocument | null>(null)
  const [deleteDoc, setDeleteDoc] = useState<KnowledgeDocument | null>(null)
  const [editingPolicyDoc, setEditingPolicyDoc] = useState<KnowledgeDocument | null>(null)
  const [showBatchDelete, setShowBatchDelete] = useState(false)
  const [keyword, setKeyword] = useState('')
  const [showTagFilter, setShowTagFilter] = useState(false)
  const [showTypeFilter, setShowTypeFilter] = useState(false)
  const [selectedTags, setSelectedTags] = useState<string[]>([])
  const [selectedTypes, setSelectedTypes] = useState<string[]>([])
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([])
  const [editingTag, setEditingTag] = useState('')
  const [tagInput, setTagInput] = useState('')
  const [renameTagInput, setRenameTagInput] = useState('')

  useEffect(() => {
    setSelectedDocIds([])
    setSelectedTags([])
    setSelectedTypes([])
    setShowTagFilter(false)
    setShowTypeFilter(false)
  }, [activeTab])

  const scopedDocuments = useMemo(() => {
    return documents.filter((doc) => {
      if (activeTab === 'general') return doc.knowledgeBase === 'general'
      return doc.knowledgeBase === 'project' && doc.projectId === project.id
    })
  }, [activeTab, documents, project.id])

  const allTags = useMemo(() => {
    return Array.from(new Set(scopedDocuments.flatMap((doc) => doc.tags))).sort()
  }, [scopedDocuments])

  const allTypes = useMemo(() => {
    return Array.from(new Set(scopedDocuments.map((doc) => doc.category))).sort()
  }, [scopedDocuments])

  const documentsInTab = useMemo(() => {
    const keywordTrimmed = keyword.trim()
    return scopedDocuments.filter((doc) => {
      const matchKeyword = !keywordTrimmed
        || doc.fileName.includes(keywordTrimmed)
        || doc.category.includes(keywordTrimmed)
        || doc.tags.join(',').includes(keywordTrimmed)
      const matchTags = selectedTags.length === 0 || selectedTags.every((tag) => doc.tags.includes(tag))
      const matchTypes = selectedTypes.length === 0 || selectedTypes.includes(doc.category)
      return matchKeyword && matchTags && matchTypes
    })
  }, [keyword, scopedDocuments, selectedTags, selectedTypes])

  const projectCount = documents.filter((doc) => doc.knowledgeBase === 'project' && doc.projectId === project.id).length
  const generalCount = documents.filter((doc) => doc.knowledgeBase === 'general').length
  const activeTabInfo = tabs.find((tab) => tab.key === activeTab) ?? tabs[0]

  const handleReparse = (doc: KnowledgeDocument) => {
    onUpdateDocument(doc.id, { parseStatus: 'parsing', summaryStatus: 'not-generated' })
    window.setTimeout(() => {
      onUpdateDocument(doc.id, { parseStatus: 'ready', summaryStatus: 'not-generated' })
    }, 1000)
  }

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) => prev.includes(tag) ? prev.filter((item) => item !== tag) : [...prev, tag])
  }

  const toggleType = (type: string) => {
    setSelectedTypes((prev) => prev.includes(type) ? prev.filter((item) => item !== type) : [...prev, type])
  }

  const toggleDoc = (docId: string) => {
    setSelectedDocIds((prev) => prev.includes(docId) ? prev.filter((id) => id !== docId) : [...prev, docId])
  }

  const toggleAllVisibleDocs = () => {
    const visibleIds = documentsInTab.map((doc) => doc.id)
    const allSelected = visibleIds.length > 0 && visibleIds.every((id) => selectedDocIds.includes(id))
    setSelectedDocIds(allSelected ? [] : visibleIds)
  }

  const handleGenerateSummary = async (doc: KnowledgeDocument) => {
    try {
      onUpdateDocument(doc.id, { summaryStatus: 'not-generated' })
      const updated = await api.summarizeDocument(doc.id)
      onUpdateDocument(doc.id, {
        summaryStatus: updated.summaryStatus,
        summary: updated.summary,
      })
    } catch (error) {
      alert(error instanceof Error ? error.message : '摘要生成失败，请确认后端和大模型配置是否正常。')
    }
  }

  const handleBatchGenerateSummary = async () => {
    for (const docId of selectedDocIds) {
      const doc = documents.find((item) => item.id === docId)
      if (doc && !hasGeneratedSummary(doc)) {
        await handleGenerateSummary(doc)
      }
    }
  }

  const updateDocTags = (doc: KnowledgeDocument, nextTags: string[]) => {
    const uniqueTags = Array.from(new Set(nextTags.map((tag) => tag.trim()).filter(Boolean)))
    onUpdateDocument(doc.id, { tags: uniqueTags })
  }

  const docsForTagOperation = () => {
    if (selectedDocIds.length > 0) {
      return scopedDocuments.filter((doc) => selectedDocIds.includes(doc.id))
    }
    return scopedDocuments
  }

  const handleManageTag = (tag: string) => {
    setEditingTag(tag)
    setRenameTagInput(tag)
    setShowTagFilter(true)
  }

  const handleAddTag = () => {
    const nextTag = tagInput.trim()
    if (!nextTag) return
    const targetDocs = docsForTagOperation()
    targetDocs.forEach((doc) => {
      if (!doc.tags.includes(nextTag)) updateDocTags(doc, [...doc.tags, nextTag])
    })
    setTagInput('')
  }

  const handleDeleteTag = () => {
    if (!editingTag) return
    scopedDocuments
      .filter((doc) => doc.tags.includes(editingTag))
      .forEach((doc) => updateDocTags(doc, doc.tags.filter((tag) => tag !== editingTag)))
    setSelectedTags((prev) => prev.filter((tag) => tag !== editingTag))
    setEditingTag('')
    setRenameTagInput('')
  }

  const handleRenameTag = () => {
    const nextTag = renameTagInput.trim()
    if (!editingTag || !nextTag) return
    scopedDocuments
      .filter((doc) => doc.tags.includes(editingTag))
      .forEach((doc) => updateDocTags(doc, doc.tags.map((tag) => tag === editingTag ? nextTag : tag)))
    setSelectedTags((prev) => prev.map((tag) => tag === editingTag ? nextTag : tag))
    setEditingTag(nextTag)
    setRenameTagInput(nextTag)
  }

  const selectedNeedSummaryCount = selectedDocIds.filter((docId) => {
    const doc = documents.find((item) => item.id === docId)
    return doc ? !hasGeneratedSummary(doc) : false
  }).length

  const handleBatchDelete = () => {
    selectedDocIds.forEach(onDeleteDocument)
    setSelectedDocIds([])
    setShowBatchDelete(false)
  }

  return (
    <div className="flex-1 overflow-auto">
      <div className="mx-auto max-w-[1180px] space-y-6 px-8 py-8">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-foreground">知识库</h2>
            <p className="mt-1 text-sm text-foreground-secondary">管理当前项目资料和跨项目通用资料</p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => setShowUpload(true)} className="btn-primary">
              <Upload size={18} /> 上传资料
            </button>
            <button onClick={() => setShowResearch(true)} className="btn-secondary">
              <Search size={18} /> 网络检索资料
            </button>
          </div>
        </div>

        <div className="flex items-center gap-1 rounded-card bg-canvas-alt p-1 w-fit">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`rounded-card px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? 'bg-surface text-foreground shadow-card'
                  : 'text-foreground-secondary hover:text-foreground'
              }`}
            >
              {tab.label}
              <span className="ml-1.5 text-xs text-foreground-muted">({tab.key === 'general' ? generalCount : projectCount})</span>
            </button>
          ))}
        </div>

        <div className="rounded-card border border-edge bg-white p-4 text-sm text-foreground-secondary">
          {activeTabInfo.desc}
        </div>

        <div className="space-y-3 rounded-card border border-edge bg-white p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="relative w-full max-w-sm">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-foreground-muted" />
              <input
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                className="input-styled w-full pl-9"
                placeholder="搜索资料名称、类型或标签"
              />
            </div>
            <div className="flex flex-wrap gap-2">
              <button onClick={() => setShowTypeFilter((prev) => !prev)} className="btn-secondary">
                <Filter size={16} /> 类型筛选{selectedTypes.length > 0 ? `（${selectedTypes.length}）` : ''}
              </button>
              <button onClick={() => setShowTagFilter((prev) => !prev)} className="btn-secondary">
                标签筛选{selectedTags.length > 0 ? `（${selectedTags.length}）` : ''}
              </button>
              <button
                onClick={handleBatchGenerateSummary}
                disabled={selectedNeedSummaryCount === 0}
                className="btn-secondary text-primary"
              >
                批量生成摘要{selectedNeedSummaryCount > 0 ? `（${selectedNeedSummaryCount}）` : ''}
              </button>
              <button
                onClick={() => setShowBatchDelete(true)}
                disabled={selectedDocIds.length === 0}
                className="btn-secondary text-status-repealed"
              >
                批量删除{selectedDocIds.length > 0 ? `（${selectedDocIds.length}）` : ''}
              </button>
            </div>
          </div>

          {showTypeFilter && (
            <FilterPanel
              title="按资料类型筛选"
              emptyText="当前知识库暂无可筛选类型。"
              items={allTypes}
              selected={selectedTypes}
              onToggle={toggleType}
              onClear={() => setSelectedTypes([])}
            />
          )}

          {showTagFilter && (
            <FilterPanel
              title="标签管理 / 筛选"
              emptyText="当前知识库暂无标签。"
              items={allTags}
              selected={selectedTags}
              onToggle={toggleTag}
              onClear={() => setSelectedTags([])}
              onManage={handleManageTag}
              editingItem={editingTag}
            >
              <div className="mt-3 rounded-card border border-edge bg-white p-3">
                <div className="flex flex-wrap items-end gap-2">
                  <label className="min-w-[220px] flex-1">
                    <span className="mb-1 block text-xs text-foreground-muted">新增标签{selectedDocIds.length > 0 ? '（添加到已选资料）' : '（添加到当前列表资料）'}</span>
                    <input value={tagInput} onChange={(e) => setTagInput(e.target.value)} className="input-styled w-full" placeholder="输入新标签" />
                  </label>
                  <button onClick={handleAddTag} disabled={!tagInput.trim()} className="btn-secondary text-primary">添加标签</button>
                </div>
                {editingTag && (
                  <div className="mt-3 rounded-card border border-primary/20 bg-primary-light/50 p-3">
                    <p className="text-xs text-foreground-secondary">正在管理标签：<strong className="text-primary">{editingTag}</strong></p>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <input value={renameTagInput} onChange={(e) => setRenameTagInput(e.target.value)} className="input-styled min-w-[220px] flex-1" placeholder="输入新的标签名称" />
                      <button onClick={handleRenameTag} disabled={!renameTagInput.trim()} className="btn-secondary text-primary">改名</button>
                      <button onClick={handleDeleteTag} className="btn-secondary text-status-repealed">删除标签</button>
                      <button onClick={() => setEditingTag('')} className="btn-secondary">退出管理</button>
                    </div>
                  </div>
                )}
                <p className="mt-2 text-xs text-foreground-muted">点击标签进入管理状态；勾选资料后新增标签只应用到已选资料。</p>
              </div>
            </FilterPanel>
          )}
        </div>

        <KnowledgeDocumentTable
          activeTab={activeTab}
          documents={documentsInTab}
          selectedDocIds={selectedDocIds}
          onToggleDoc={toggleDoc}
          onToggleAll={toggleAllVisibleDocs}
          onOpen={setSelectedDoc}
          onOpenSummary={setSelectedSummaryDoc}
          onAsk={onAskFromDocument}
          onDelete={setDeleteDoc}
          onReparse={handleReparse}
          onGenerateSummary={handleGenerateSummary}
          onManageTag={handleManageTag}
          onEditPolicyStatus={setEditingPolicyDoc}
        />
      </div>

      <UploadModal
        open={showUpload}
        onClose={() => setShowUpload(false)}
        projectId={project.id}
        defaultKnowledgeBase={activeTab}
        onUploaded={onAddDocument}
        existingDocuments={documents}
      />
      <ResearchDrawer
        open={showResearch}
        projectId={project.id}
        onClose={() => setShowResearch(false)}
        onAddDocument={onAddDocument}
      />
      <DocumentDrawer document={documents.find(doc => doc.id === selectedDoc?.id) ?? selectedDoc} onClose={() => setSelectedDoc(null)} />
      <SummaryDrawer document={documents.find(doc => doc.id === selectedSummaryDoc?.id) ?? selectedSummaryDoc} onClose={() => setSelectedSummaryDoc(null)} />
      {editingPolicyDoc && <PolicyStatusModal key={editingPolicyDoc.id} document={editingPolicyDoc} onClose={() => setEditingPolicyDoc(null)} onSave={onUpdatePolicyStatus} />}

      {deleteDoc && (
        <ConfirmModal
          title="确认删除资料"
          desc={`删除后，该资料将不再参与后续问答和引用。确定删除《${deleteDoc.fileName}》吗？`}
          confirmText="删除"
          onCancel={() => setDeleteDoc(null)}
          onConfirm={() => {
            onDeleteDocument(deleteDoc.id)
            setSelectedDocIds((prev) => prev.filter((id) => id !== deleteDoc.id))
            setDeleteDoc(null)
          }}
        />
      )}

      {showBatchDelete && (
        <ConfirmModal
          title="确认批量删除资料"
          desc={`将删除已选中的 ${selectedDocIds.length} 份资料。删除后，这些资料将不再参与后续问答和引用。`}
          confirmText="批量删除"
          onCancel={() => setShowBatchDelete(false)}
          onConfirm={handleBatchDelete}
        />
      )}
    </div>
  )
}

function FilterPanel({ title, emptyText, items, selected, onToggle, onClear, onManage, editingItem, children }: {
  title: string
  emptyText: string
  items: string[]
  selected: string[]
  onToggle: (item: string) => void
  onClear: () => void
  onManage?: (item: string) => void
  editingItem?: string
  children?: ReactNode
}) {
  return (
    <div className="rounded-card border border-edge bg-canvas p-3">
      <div className="mb-2 flex items-center justify-between text-sm">
        <span className="font-medium text-foreground">{title}</span>
        {selected.length > 0 && <button onClick={onClear} className="text-xs text-primary">清空筛选</button>}
      </div>
      {items.length === 0 ? (
        <p className="text-xs text-foreground-muted">{emptyText}</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {items.map((item) => {
            const checked = selected.includes(item)
            const editing = editingItem === item
            return (
              <div key={item} className={`inline-flex items-center overflow-hidden rounded-full border text-xs transition-colors ${editing ? 'border-primary bg-primary-light text-primary' : checked ? 'border-primary/70 bg-primary-light/70 text-primary' : 'border-edge bg-white text-foreground-secondary hover:border-primary/40'}`}>
                <button type="button" onClick={() => onManage ? onManage(item) : onToggle(item)} className="px-3 py-1">
                  {editing && <Check size={12} className="mr-1 inline" />}
                  {item}
                </button>
                {onManage && (
                  <button type="button" onClick={() => onToggle(item)} className="border-l border-edge/70 px-2 py-1 text-[11px] hover:bg-white/70">
                    {checked ? '取消筛选' : '筛选'}
                  </button>
                )}
              </div>
            )
          })}
        </div>
      )}
      {children}
    </div>
  )
}

function ConfirmModal({ title, desc, confirmText, onCancel, onConfirm }: {
  title: string
  desc: string
  confirmText: string
  onCancel: () => void
  onConfirm: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40" />
      <div className="relative w-full max-w-md rounded-card border border-edge bg-white p-6 shadow-xl modal-pop">
        <div className="flex items-start justify-between gap-4">
          <h3 className="text-lg font-semibold text-foreground">{title}</h3>
          <button onClick={onCancel} className="rounded p-1 text-foreground-muted hover:bg-canvas"><X size={18} /></button>
        </div>
        <p className="mt-2 text-sm leading-6 text-foreground-secondary">{desc}</p>
        <div className="mt-6 flex justify-end gap-2">
          <button onClick={onCancel} className="btn-secondary">取消</button>
          <button onClick={onConfirm} className="btn-primary bg-status-repealed hover:bg-red-700">
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  )
}

function KnowledgeDocumentTable({
  activeTab,
  documents,
  selectedDocIds,
  onToggleDoc,
  onToggleAll,
  onOpen,
  onOpenSummary,
  onAsk,
  onDelete,
  onReparse,
  onGenerateSummary,
  onManageTag,
  onEditPolicyStatus,
}: {
  activeTab: KnowledgeBaseType
  documents: KnowledgeDocument[]
  selectedDocIds: string[]
  onToggleDoc: (docId: string) => void
  onToggleAll: () => void
  onOpen: (doc: KnowledgeDocument) => void
  onOpenSummary: (doc: KnowledgeDocument) => void
  onAsk: (doc: KnowledgeDocument) => void
  onDelete: (doc: KnowledgeDocument) => void
  onReparse: (doc: KnowledgeDocument) => void
  onGenerateSummary: (doc: KnowledgeDocument) => void
  onManageTag: (tag: string) => void
  onEditPolicyStatus: (doc: KnowledgeDocument) => void
}) {
  if (documents.length === 0) {
    return (
      <div className="card p-12 text-center">
        <Upload size={40} className="mx-auto mb-4 text-foreground-muted" />
        <h3 className="mb-2 text-base font-semibold text-foreground">
          {activeTab === 'project' ? '当前项目知识库暂无资料' : '通用知识库暂无资料'}
        </h3>
        <p className="text-sm text-foreground-secondary">
          {activeTab === 'project'
            ? '你可以上传甲方资料，或联网搜索项目相关资料。'
            : '你可以上传通用政策标准，或联网搜索公开资料。'}
        </p>
      </div>
    )
  }

  const allVisibleSelected = documents.length > 0 && documents.every((doc) => selectedDocIds.includes(doc.id))

  return (
    <div className="card overflow-hidden">
      <div className="max-h-[calc(100vh-360px)] overflow-y-auto overflow-x-hidden">
        <table className="w-full table-fixed text-sm">
          <thead className="sticky top-0 z-10">
            <tr className="border-b border-edge bg-canvas/95 backdrop-blur">
              <th className="w-[42px] px-2 py-3 text-center align-middle font-medium text-foreground-secondary">
                <input type="checkbox" checked={allVisibleSelected} onChange={onToggleAll} className="align-middle" />
              </th>
              <th className="w-[24%] px-3 py-3 text-center font-medium text-foreground-secondary">文档名称</th>
              <th className="w-[10%] px-3 py-3 text-center font-medium text-foreground-secondary">资料类型</th>
              <th className="w-[18%] px-3 py-3 text-center font-medium text-foreground-secondary">标签</th>
              <th className="w-[12%] px-3 py-3 text-center font-medium text-foreground-secondary">上传/入库时间</th>
              <th className="w-[10%] px-3 py-3 text-center font-medium text-foreground-secondary">解析状态</th>
              <th className="w-[8%] px-3 py-3 text-center font-medium text-foreground-secondary">摘要</th>
              <th className="w-[18%] px-3 py-3 text-center font-medium text-foreground-secondary">操作</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((doc) => {
              const selected = selectedDocIds.includes(doc.id)
              const summaryReady = hasGeneratedSummary(doc)
              return (
                <tr key={doc.id} className={`border-b border-edge-light hover:bg-surface-hover ${selected ? 'bg-primary-light/40' : ''}`}>
                  <td className="px-2 py-4 text-center align-middle">
                    <input type="checkbox" checked={selected} onChange={() => onToggleDoc(doc.id)} className="align-middle" />
                  </td>
                  <td className="px-3 py-4 align-middle">
                    <div className="flex min-w-0 items-center gap-2">
                      <FileTypeIcon type={doc.fileType} />
                      <div className="min-w-0 truncate font-medium text-foreground" title={doc.fileName}>{doc.fileName}</div>
                    </div>
                  </td>
                  <td className="truncate px-3 py-4 text-center align-middle text-foreground-secondary" title={doc.category}>{doc.category}</td>
                  <td className="px-3 py-4 text-center align-middle">
                    <div className="flex min-w-0 flex-nowrap justify-center gap-1 overflow-hidden">
                      {doc.tags.slice(0, 2).map((tag) => (
                        <button
                          key={tag}
                          type="button"
                          onClick={() => onManageTag(tag)}
                          title={`管理标签：${tag}`}
                          className="max-w-[72px] shrink-0 truncate whitespace-nowrap rounded-full bg-canvas px-2 py-0.5 text-xs text-foreground-muted hover:bg-primary-light hover:text-primary"
                        >
                          {tag}
                        </button>
                      ))}
                      {doc.tags.length > 2 && <span className="shrink-0 rounded-full bg-canvas px-2 py-0.5 text-xs text-foreground-muted">+{doc.tags.length - 2}</span>}
                    </div>
                  </td>
                  <td className="truncate px-3 py-4 text-center align-middle text-xs text-foreground-muted" title={doc.ingestTime}>{doc.ingestTime}</td>
                  <td className="px-3 py-4 text-center align-middle">
                    <span className={`inline-flex max-w-full justify-center truncate whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${parseStatusMap[doc.parseStatus].className}`}>
                      {parseStatusMap[doc.parseStatus].label}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-3 py-4 text-center align-middle text-xs text-foreground-secondary">
                    {summaryReady ? (
                      <button onClick={() => onOpenSummary(doc)} className="rounded px-2 py-1 text-xs font-medium text-primary hover:bg-primary-light">
                        查看
                      </button>
                    ) : (
                      <span className="text-foreground-muted">未生成</span>
                    )}
                  </td>
                  <td className="px-3 py-4 align-middle">
                    <div className="flex flex-wrap items-center justify-center gap-0.5">
                      <button onClick={() => onOpen(doc)} className="rounded px-1 py-1 text-xs text-primary hover:bg-primary-light">原文</button>
                      <button onClick={() => onAsk(doc)} className="rounded px-1 py-1 text-xs text-primary hover:bg-primary-light">提问</button>
                      <button onClick={() => onEditPolicyStatus(doc)} title={`修改效力状态（当前：${getPolicyStatusDisplay(doc.policyStatus).label}）`} aria-label={`修改效力状态：${doc.fileName}`} className="rounded px-1 py-1 text-xs text-primary hover:bg-primary-light">效力</button>
                      {!summaryReady && (
                        <button onClick={() => onGenerateSummary(doc)} className="rounded px-1 py-1 text-xs text-primary hover:bg-primary-light">摘要</button>
                      )}
                      <button onClick={() => onDelete(doc)} className="rounded px-1 py-1 text-xs text-status-repealed hover:bg-red-50"><Trash2 size={12} /></button>
                      {doc.parseStatus === 'failed' && (
                        <button onClick={() => onReparse(doc)} className="inline-flex items-center gap-0.5 rounded px-1 py-1 text-xs text-primary hover:bg-primary-light"><RefreshCw size={12} /> 重试</button>
                      )}
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

