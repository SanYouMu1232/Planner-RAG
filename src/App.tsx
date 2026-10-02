import { useCallback, useEffect, useMemo, useState } from 'react'
import type { KnowledgeDocument, PolicyStatus, Project } from './types'
import * as api from './api/client'
import ProjectSelect from './pages/ProjectSelect'
import AppShell from './pages/AppShell'
import TopBar from './components/TopBar'
import CreateProjectModal from './components/CreateProjectModal'
import ApiConfigModal from './components/ApiConfigModal'
import RenameProjectModal from './components/RenameProjectModal'

type ViewState =
  | { page: 'project-select' }
  | { page: 'app-shell'; projectId: string }

export default function App() {
  // 首次进入必须是「无项目库」状态。PRD / 原型中的项目只作为演示案例，不作为真实初始数据。
  const [projects, setProjects] = useState<Project[]>([])
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([])
  const [view, setView] = useState<ViewState>({ page: 'project-select' })
  const [openProjectIds, setOpenProjectIds] = useState<string[]>([])
  const [showCreate, setShowCreate] = useState(false)
  const [showApiConfig, setShowApiConfig] = useState(false)
  const [renameProject, setRenameProject] = useState<Project | null>(null)
  const [apiConfigured, setApiConfigured] = useState(false)

  // Load projects and documents from API on mount
  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const [projList, docList, configList] = await Promise.all([
          api.listProjects(),
          api.listDocuments(),
          api.listProviderConfigs().catch(() => []),
        ])
        if (!cancelled) {
          setProjects(projList)
          setDocuments(docList)
          setApiConfigured(configList.length > 0)
        }
      } catch {
        // Backend not available — keep empty projects state; UI will show "no projects"
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  const handleCreateProject = useCallback(
    async (payload: { name: string; projectType: string; region: string; description: string }) => {
      try {
        const newProject = await api.createProject({
          name: payload.name,
          project_type: payload.projectType || '其他',
          region: payload.region || '未填写',
          description: payload.description || '个人创建的项目库，暂无项目专属资料。',
        })
        setProjects((prev) => [newProject, ...prev])
        setOpenProjectIds((prev) => [newProject.id, ...prev])
        setView({ page: 'app-shell', projectId: newProject.id })
      } catch (error) {
        alert(error instanceof Error ? error.message : '创建项目失败，请确认后端已启动。')
      }
    },
    [],
  )


  const handleRenameProject = useCallback(async (projectId: string, name: string) => {
    try {
      const updated = await api.updateProject(projectId, { name })
      setProjects((prev) => prev.map((project) => project.id === projectId ? updated : project))
      setRenameProject(null)
    } catch (error) {
      alert(error instanceof Error ? error.message : '项目库改名失败，请确认后端已启动。')
    }
  }, [])

  const handleEnterProject = useCallback((projectId: string) => {
    setOpenProjectIds((prev) => (prev.includes(projectId) ? prev : [projectId, ...prev]))
    setView({ page: 'app-shell', projectId })
  }, [])

  const handleSwitchProject = useCallback(() => {
    setView({ page: 'project-select' })
  }, [])

  const handleCloseProjectTab = useCallback((projectId: string) => {
    setOpenProjectIds((prev) => {
      const next = prev.filter((id) => id !== projectId)
      setView((current) => {
        if (current.page !== 'app-shell' || current.projectId !== projectId) return current
        const fallback = next[0]
        return fallback ? { page: 'app-shell', projectId: fallback } : { page: 'project-select' }
      })
      return next
    })
  }, [])

  const handleAddDocument = useCallback((doc: KnowledgeDocument) => {
    setDocuments((prev) => [doc, ...prev])
    if (doc.knowledgeBase === 'project' && doc.projectId) {
      setProjects((prev) =>
        prev.map((project) =>
          project.id === doc.projectId
            ? { ...project, docCount: project.docCount + 1, lastUsed: '刚刚' }
            : project,
        ),
      )
    }
  }, [])

  const handleDeleteDocument = useCallback((docId: string) => {
    const deleted = documents.find((doc) => doc.id === docId)
    setDocuments((prev) => prev.filter((doc) => doc.id !== docId))
    if (deleted?.knowledgeBase === 'project' && deleted.projectId) {
      setProjects((prev) =>
        prev.map((project) =>
          project.id === deleted.projectId
            ? { ...project, docCount: Math.max(0, project.docCount - 1) }
            : project,
        ),
      )
    }
    // Fire-and-forget API delete
    api.deleteDocument(docId).catch(() => {})
  }, [documents])

  const handleUpdateDocument = useCallback((docId: string, patch: Partial<KnowledgeDocument>) => {
    setDocuments((prev) => prev.map((doc) => (doc.id === docId ? { ...doc, ...patch } : doc)))
    // Fire-and-forget API update
    api.updateDocument(docId, patch).catch(() => {})
  }, [])

  const handleUpdatePolicyStatus = useCallback(async (docId: string, policyStatus: PolicyStatus) => {
    const updated = await api.updateDocument(docId, { policyStatus })
    setDocuments(prev => prev.map(doc => doc.id === docId ? { ...doc, policyStatus: updated.policyStatus } : doc))
  }, [])

  const currentProject = view.page === 'app-shell'
    ? projects.find((project) => project.id === view.projectId)
    : undefined

  const openProjects = useMemo(
    () => openProjectIds.map((id) => projects.find((project) => project.id === id)).filter(Boolean) as Project[],
    [openProjectIds, projects],
  )

  const content = view.page === 'app-shell' && currentProject ? (
    <AppShell
      project={currentProject}
      documents={documents}
      apiConfigured={apiConfigured}
      onRequireApi={() => setShowApiConfig(true)}
      onAddDocument={handleAddDocument}
      onDeleteDocument={handleDeleteDocument}
      onUpdateDocument={handleUpdateDocument}
      onUpdatePolicyStatus={handleUpdatePolicyStatus}
    />
  ) : (
    <ProjectSelect
      projects={projects}
      onEnterProject={handleEnterProject}
      onOpenCreate={() => setShowCreate(true)}
      onRenameProject={setRenameProject}
    />
  )

  return (
    <div className="h-screen flex flex-col bg-canvas">
      <TopBar
        activeProject={currentProject}
        openProjects={openProjects}
        onSelectProject={(projectId) => setView({ page: 'app-shell', projectId })}
        onCloseProject={handleCloseProjectTab}
        onSwitchProject={handleSwitchProject}
        onOpenApiConfig={() => setShowApiConfig(true)}
      />
      <div className="flex min-h-0 flex-1 overflow-hidden page-fade" key={`${view.page}-${currentProject?.id ?? 'select'}`}>
        {content}
      </div>
      <CreateProjectModal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        onCreate={(payload) => {
          handleCreateProject(payload)
          setShowCreate(false)
        }}
      />
      <ApiConfigModal
        open={showApiConfig}
        onClose={() => setShowApiConfig(false)}
        onSaved={() => setApiConfigured(true)}
      />
      <RenameProjectModal
        project={renameProject}
        onClose={() => setRenameProject(null)}
        onRename={handleRenameProject}
      />
    </div>
  )
}


