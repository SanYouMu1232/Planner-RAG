/** 知识库类型 */
export type KnowledgeBaseType = 'project' | 'general'
export type PolicyStatus = 'active' | 'repealed' | 'draft' | 'unknown'
/** Word/PDF/PPT/Excel/网页等统一资料类型。 */
export type FileType = 'pdf' | 'word' | 'ppt' | 'excel' | 'image' | 'scan' | 'web' | 'txt' | 'md' | 'other'
export type ParseStatus = 'uploading' | 'parsing' | 'summarizing' | 'vectorizing' | 'ready' | 'failed'
export type SummaryStatus = 'generated' | 'not-generated' | 'failed'
export type KnowledgeSource = 'project' | 'general' | 'both'

export interface Project {
  id: string
  name: string
  projectType: string
  region: string
  description: string
  docCount: number
  lastUsed: string
  lastQaTime: string
  createdAt: string
  updatedAt: string
}

export interface KnowledgeDocument {
  id: string
  fileName: string
  fileType: FileType
  category: string
  tags: string[]
  source: string
  sourceUrl?: string
  publishDate: string
  policyStatus: PolicyStatus
  ingestTime: string
  parseStatus: ParseStatus
  /** not-required | pending | processing | completed | required | failed */
  ocrStatus?: string
  isUsable?: boolean
  summaryStatus: SummaryStatus
  knowledgeBase: KnowledgeBaseType
  projectId?: string
  summary: string
  chunkCount?: number
  tableCount?: number
  parserName?: string
}

export interface CandidateDocument {
  id: string
  title: string
  source: string
  publishDate: string
  summary: string
  url: string
  credibility: string
  reason: string
  category: string
}

export interface Citation {
  id: string
  number: number
  documentId?: string
  chunkId?: string
  documentName: string
  knowledgeBase: KnowledgeBaseType
  section: string
  quote: string
  policyStatus: PolicyStatus
}

export interface ChatTurn {
  id: string
  question: string
  status: 'answering' | 'done' | 'failed'
  answer?: string
  citations?: Citation[]
  createdAt?: string
}

export interface ConversationSession {
  id: string
  title: string
  turns: ChatTurn[]
  updatedAt: string
}
