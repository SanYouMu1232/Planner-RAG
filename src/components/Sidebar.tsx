import { useState } from 'react'
import { ChevronDown, LayoutDashboard, Library, MessageSquare, Plus } from 'lucide-react'
import type { ConversationSession } from '../types'

export type NavPage = 'workbench' | 'knowledge-base'

interface Props {
  activePage: NavPage
  onNavigate: (page: NavPage) => void
  sessions: ConversationSession[]
  activeSessionId: string | null
  onSelectSession: (sessionId: string) => void
  onStartNewConversation: () => void
}

export default function Sidebar({
  activePage,
  onNavigate,
  sessions,
  activeSessionId,
  onSelectSession,
  onStartNewConversation,
}: Props) {
  const workbenchActive = activePage === 'workbench'
  const knowledgeActive = activePage === 'knowledge-base'
  const [workbenchExpanded, setWorkbenchExpanded] = useState(true)

  const handleWorkbenchClick = () => {
    if (!workbenchActive) {
      onNavigate('workbench')
      setWorkbenchExpanded(true)
      return
    }
    setWorkbenchExpanded((prev) => !prev)
  }

  return (
    <aside className="sidebar flex flex-col shrink-0 select-none">
      <nav className="flex-1 overflow-y-auto py-4">
        <div>
          <button
            onClick={handleWorkbenchClick}
            className={`sidebar-item w-full ${workbenchActive ? 'sidebar-item-active' : ''}`}
          >
            <LayoutDashboard size={18} />
            <span className="flex-1 text-left">工作台</span>
            <ChevronDown size={15} className={`transition-transform ${workbenchExpanded && workbenchActive ? 'rotate-0' : '-rotate-90'}`} />
          </button>

          {workbenchActive && workbenchExpanded && (
            <div className="mx-3 mt-2 rounded-xl border border-edge bg-white/70 p-2 shadow-sm">
              <button
                type="button"
                onClick={onStartNewConversation}
                className="mb-2 flex h-9 w-full items-center gap-2 rounded-lg px-3 text-left text-xs font-medium text-primary transition hover:bg-primary-light"
              >
                <Plus size={14} />
                新建对话
              </button>

              <div className="max-h-[300px] space-y-1 overflow-y-auto pr-1 chat-history-menu">
                {sessions.length === 0 ? (
                  <div className="rounded-lg px-3 py-3 text-xs leading-5 text-foreground-muted">
                    暂无对话记录。发送问题后，会自动保存到这里。
                  </div>
                ) : (
                  sessions.map((session) => {
                    const active = session.id === activeSessionId
                    const lastQuestion = session.turns[session.turns.length - 1]?.question ?? session.title
                    return (
                      <button
                        key={session.id}
                        type="button"
                        onClick={() => onSelectSession(session.id)}
                        className={`w-full rounded-lg px-3 py-2 text-left transition ${
                          active ? 'bg-primary-light text-primary' : 'text-foreground-secondary hover:bg-canvas hover:text-foreground'
                        }`}
                        title={lastQuestion}
                      >
                        <div className="flex items-center gap-2">
                          <MessageSquare size={13} className="shrink-0" />
                          <span className="min-w-0 flex-1 truncate text-xs font-medium">{session.title}</span>
                        </div>
                        <div className="mt-1 truncate pl-5 text-[11px] text-foreground-muted">
                          {session.turns.length} 轮对话 · {session.updatedAt}
                        </div>
                      </button>
                    )
                  })
                )}
              </div>
            </div>
          )}
        </div>

        <button
          onClick={() => onNavigate('knowledge-base')}
          className={`sidebar-item mt-2 w-full ${knowledgeActive ? 'sidebar-item-active' : ''}`}
        >
          <Library size={18} />
          <span>知识库</span>
        </button>
      </nav>
    </aside>
  )
}
