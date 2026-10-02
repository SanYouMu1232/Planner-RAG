import { useCallback, useEffect, useState } from 'react'
import Sidebar, { type NavPage } from '../components/Sidebar'
import Workbench from './Workbench'
import KnowledgeBase from './KnowledgeBase'
import * as api from '../api/client'
import type { ChatTurn, Citation, ConversationSession, KnowledgeDocument, PolicyStatus, Project } from '../types'

interface Props {
  project: Project
  documents: KnowledgeDocument[]
  apiConfigured: boolean
  onRequireApi: () => void
  onAddDocument: (doc: KnowledgeDocument) => void
  onDeleteDocument: (docId: string) => void
  onUpdateDocument: (docId: string, patch: Partial<KnowledgeDocument>) => void
  onUpdatePolicyStatus: (docId: string, status: PolicyStatus) => Promise<void>
}

export default function AppShell({
  project,
  documents,
  apiConfigured,
  onRequireApi,
  onAddDocument,
  onDeleteDocument,
  onUpdateDocument,
  onUpdatePolicyStatus,
}: Props) {
  const [activePage, setActivePage] = useState<NavPage>('workbench')
  const [draftQuestion, setDraftQuestion] = useState('')
  const [conversationSessions, setConversationSessions] = useState<ConversationSession[]>([])
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null)

  const activeConversation = conversationSessions.find((session) => session.id === activeConversationId) ?? null

  // Load conversations when project changes
  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const convs = await api.listConversations(project.id)
        if (!cancelled) {
          setConversationSessions(convs)
          setActiveConversationId(convs[0]?.id ?? null)
        }
      } catch {
        // Backend not available — keep local state
      }
    }
    load()
    return () => { cancelled = true }
  }, [project.id])

  const handleAskFromDocument = (doc: KnowledgeDocument) => {
    setDraftQuestion(`请基于《${doc.fileName}》回答：`)
    setActivePage('workbench')
  }

  const handleStartNewConversation = useCallback(() => {
    setActivePage('workbench')
    setActiveConversationId(null)
  }, [])

  const handleSelectConversation = useCallback((sessionId: string) => {
    setActivePage('workbench')
    setActiveConversationId(sessionId)
  }, [])

  const handleSubmitQuestion = useCallback(
    async (question: string) => {
      const now = Date.now()
      const turn: ChatTurn = {
        id: `turn-${now}`,
        question,
        status: 'answering',
      }

      let sessionId = activeConversationId
      const existingSession = sessionId
        ? conversationSessions.find((session) => session.id === sessionId)
        : null

      if (!existingSession) {
        // Create new conversation via API
        try {
          const conv = await api.createConversation(project.id, question.length > 18 ? `${question.slice(0, 18)}…` : question)
          sessionId = conv.id
          const newSession: ConversationSession = {
            id: conv.id,
            title: conv.title,
            turns: [turn],
            updatedAt: '刚刚',
          }
          setConversationSessions((prev) => [newSession, ...prev])
          setActiveConversationId(conv.id)
          return { sessionId: conv.id, turnId: turn.id }
        } catch (error) {
          throw new Error(error instanceof Error ? error.message : '创建后端会话失败，请确认后端已启动。')
        }
      }

      const targetSessionId = sessionId as string
      setConversationSessions((prev) =>
        prev.map((session) =>
          session.id === targetSessionId
            ? {
                ...session,
                turns: [...session.turns, turn],
                title: session.title || (question.length > 18 ? `${question.slice(0, 18)}…` : question),
                updatedAt: '刚刚',
              }
            : session,
        ),
      )

      return { sessionId: targetSessionId, turnId: turn.id }
    },
    [activeConversationId, conversationSessions, project.id],
  )

  const handleUpdateTurnProgress = useCallback((sessionId: string, turnId: string, result: { answer: string; citations: Citation[] }) => {
    setConversationSessions((prev) => prev.map((session) => session.id === sessionId ? {
      ...session,
      turns: session.turns.map((turn) => turn.id === turnId ? { ...turn, answer: result.answer, citations: result.citations, status: 'answering' } : turn),
    } : session))
  }, [])

  const handleMarkTurnDone = useCallback((sessionId: string, turnId: string) => {
    setConversationSessions((prev) =>
      prev.map((session) =>
        session.id === sessionId
          ? {
              ...session,
              turns: session.turns.map((turn) =>
                turn.id === turnId && turn.status !== 'failed' ? { ...turn, status: 'done' } : turn,
              ),
              updatedAt: '刚刚',
            }
          : session,
      ),
    )
  }, [])

  const handleStoreTurnResult = useCallback((sessionId: string, turnId: string, result: { answer: string; citations: Citation[]; failed?: boolean }) => {
    setConversationSessions((prev) =>
      prev.map((session) =>
        session.id === sessionId
          ? {
              ...session,
              turns: session.turns.map((turn) =>
                turn.id === turnId
                  ? { ...turn, answer: result.answer, citations: result.citations, status: result.failed ? 'failed' : 'done' }
                  : turn,
              ),
              updatedAt: '刚刚',
            }
          : session,
      ),
    )
  }, [])

  const handleResetConversation = useCallback(() => {
    if (!activeConversationId) return
    setConversationSessions((prev) => prev.filter((session) => session.id !== activeConversationId))
    // Fire-and-forget API delete
    api.deleteConversation(activeConversationId).catch(() => {})
    setActiveConversationId(null)
  }, [activeConversationId])

  return (
    <div className="flex h-full min-h-0 flex-1 overflow-hidden">
      <Sidebar
        activePage={activePage}
        onNavigate={setActivePage}
        sessions={conversationSessions}
        activeSessionId={activeConversationId}
        onSelectSession={handleSelectConversation}
        onStartNewConversation={handleStartNewConversation}
      />

      {activePage === 'workbench' && (
        <Workbench
          project={project}
          documents={documents}
          draftQuestion={draftQuestion}
          apiConfigured={apiConfigured}
          activeConversation={activeConversation}
          onSubmitQuestion={handleSubmitQuestion}
          onMarkTurnDone={handleMarkTurnDone}
          onStoreTurnResult={handleStoreTurnResult}
          onUpdateTurnProgress={handleUpdateTurnProgress}
          onResetConversation={handleResetConversation}
          onOpenKnowledgeBase={() => setActivePage('knowledge-base')}
          onRequireApi={onRequireApi}
          onDraftQuestionConsumed={() => setDraftQuestion('')}
          onAddDocument={onAddDocument}
        />
      )}
      {activePage === 'knowledge-base' && (
        <KnowledgeBase
          project={project}
          documents={documents}
          onAddDocument={onAddDocument}
          onDeleteDocument={onDeleteDocument}
          onUpdateDocument={onUpdateDocument}
          onUpdatePolicyStatus={onUpdatePolicyStatus}
          onAskFromDocument={handleAskFromDocument}
        />
      )}
    </div>
  )
}
