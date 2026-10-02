/** Typed client for the FastAPI backend.  The upload and chat paths are streaming/cancellable. */
import type { Project, KnowledgeDocument, CandidateDocument, Citation, ConversationSession, ChatTurn, KnowledgeBaseType, KnowledgeSource } from '../types'

import { readEventStream } from './sse'

const BASE = (import.meta.env?.VITE_API_BASE_URL ?? '/api').replace(/\/$/, '')

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  if (init?.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const resp = await fetch(`${BASE}${url}`, { ...init, headers })
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}))
    throw new Error((body as any).detail || (body as any).message || `HTTP ${resp.status}`)
  }
  return resp.json() as Promise<T>
}

export async function getHealth(): Promise<{ ok: boolean; message: string }> { return request('/health') }

function projectFromApi(data: any): Project {
  return { id:data.id, name:data.name, projectType:data.project_type || data.projectType || '其他', region:data.region || '', description:data.description || '', docCount:data.doc_count ?? data.docCount ?? 0, lastUsed:data.last_used || data.lastUsed || '刚刚', lastQaTime:data.last_qa_time || data.lastQaTime || '暂无', createdAt:data.created_at || data.createdAt || '', updatedAt:data.updated_at || data.updatedAt || '' }
}
export async function listProjects(): Promise<Project[]> { return (await request<any[]>('/projects')).map(projectFromApi) }
export async function createProject(payload:{name:string;project_type?:string;region?:string;description?:string}): Promise<Project> { return projectFromApi(await request<any>('/projects',{method:'POST',body:JSON.stringify(payload)})) }
export async function getProject(id:string): Promise<Project> { return projectFromApi(await request<any>(`/projects/${id}`)) }
export async function updateProject(id:string,patch:Partial<Pick<Project,'name'|'description'>&{project_type?:string;region?:string}>): Promise<Project> { return projectFromApi(await request<any>(`/projects/${id}`,{method:'PATCH',body:JSON.stringify(patch)})) }
export async function deleteProject(id:string): Promise<{ok:boolean}> { return request(`/projects/${id}`,{method:'DELETE'}) }

export interface DocumentFilters { knowledgeBase?:KnowledgeBaseType; projectId?:string; keyword?:string; category?:string; tag?:string; status?:string }
function documentFromApi(data:any): KnowledgeDocument {
  return { id:data.id, fileName:data.file_name || data.fileName || '', fileType:data.file_type || data.fileType || 'other', category:data.category || '其他', tags:Array.isArray(data.tags)?data.tags:(data.tags || '').split(',').filter(Boolean), source:data.source || '', sourceUrl:data.source_url || data.sourceUrl || undefined, publishDate:data.publish_date || data.publishDate || '', policyStatus:data.policy_status || data.policyStatus || 'unknown', ingestTime:data.ingest_time || data.ingestTime || '', parseStatus:data.parse_status || data.parseStatus || 'uploading', ocrStatus:data.ocr_status || data.ocrStatus, isUsable:data.is_usable ?? data.isUsable, summaryStatus:data.summary_status || data.summaryStatus || 'not-generated', knowledgeBase:data.knowledge_base || data.knowledgeBase || 'project', projectId:data.project_id || data.projectId || undefined, summary:data.summary || '', chunkCount:data.chunk_count ?? data.chunkCount, tableCount:data.table_count ?? data.tableCount, parserName:data.parser_name || data.parserName || '' }
}
export async function listDocuments(filters?:DocumentFilters): Promise<KnowledgeDocument[]> { const p=new URLSearchParams(); if(filters?.knowledgeBase)p.set('knowledge_base',filters.knowledgeBase);if(filters?.projectId)p.set('project_id',filters.projectId);if(filters?.keyword)p.set('keyword',filters.keyword);if(filters?.category)p.set('category',filters.category);if(filters?.tag)p.set('tag',filters.tag);if(filters?.status)p.set('status',filters.status); return (await request<any[]>(`/documents${p.toString()?`?${p}`:''}`)).map(documentFromApi) }
/** Legacy simple upload route retained for integrations; UI uses resumable upload below. */
export async function uploadDocuments(formData:FormData):Promise<KnowledgeDocument[]>{ const r=await fetch(`${BASE}/documents/upload`,{method:'POST',body:formData});if(!r.ok){const b=await r.json().catch(()=>({}));throw new Error((b as any).detail || `HTTP ${r.status}`)}return (await r.json() as any[]).map(documentFromApi) }
export async function getDocument(id:string):Promise<KnowledgeDocument>{return documentFromApi(await request<any>(`/documents/${id}`))}
export async function updateDocument(id:string,patch:Partial<KnowledgeDocument>):Promise<KnowledgeDocument>{return documentFromApi(await request<any>(`/documents/${id}`,{method:'PATCH',body:JSON.stringify({file_name:patch.fileName,category:patch.category,tags:patch.tags,policy_status:patch.policyStatus,summary:patch.summary})}))}
export async function deleteDocument(id:string):Promise<{ok:boolean}>{return request(`/documents/${id}`,{method:'DELETE'})}
export async function summarizeDocument(id:string):Promise<KnowledgeDocument>{return documentFromApi(await request<any>(`/documents/${id}/summarize`,{method:'POST'}))}

export interface DocumentChunk { id:string;parentId?:string|null;chunkIndex:number;chunkType:string;section:string;headingPath:string;clauseNumber?:string|null;pageStart?:number|null;pageEnd?:number|null;pageNumber?:number|null;text:string;tokenCount:number;sourceMethod:string;contentHash:string;tableJson?:string|null;readingOrder:number;bboxJson?:string|null }
export async function getDocumentChunks(id:string,signal?:AbortSignal):Promise<DocumentChunk[]>{return (await request<any[]>(`/documents/${encodeURIComponent(id)}/chunks`,{signal})).map(c=>({id:c.id,parentId:c.parent_id ?? c.parentId ?? null,chunkIndex:c.chunk_index ?? c.chunkIndex ?? 0,chunkType:c.chunk_type ?? c.chunkType ?? 'child',section:c.section || '',headingPath:c.heading_path ?? c.headingPath ?? '',clauseNumber:c.clause_number ?? c.clauseNumber ?? null,pageStart:c.page_start ?? c.pageStart ?? null,pageEnd:c.page_end ?? c.pageEnd ?? null,pageNumber:c.page_number ?? c.pageNumber ?? null,text:c.text || '',tokenCount:c.token_count ?? c.tokenCount ?? 0,sourceMethod:c.source_method ?? c.sourceMethod ?? '',contentHash:c.content_hash ?? c.contentHash ?? '',tableJson:c.table_json ?? c.tableJson ?? null,readingOrder:c.reading_order ?? c.readingOrder ?? 0,bboxJson:c.bbox_json ?? c.bboxJson ?? null}))}

export function getDocumentFileUrl(doc: KnowledgeDocument, page?: number | null): string {
  if (doc.fileType === 'web' && doc.sourceUrl && /^https?:\/\//i.test(doc.sourceUrl)) return doc.sourceUrl
  const url = `${BASE}/documents/${encodeURIComponent(doc.id)}/file`
  return doc.fileType === 'pdf' && page && page > 0 ? `${url}#page=${Math.floor(page)}` : url
}

export interface UploadSession { id:string;fileName:string;totalBytes:number;receivedBytes:number;status:string }
export async function initUpload(file:File):Promise<UploadSession>{const d=await request<any>('/documents/uploads/init',{method:'POST',body:JSON.stringify({file_name:file.name,total_bytes:file.size})});return {id:d.id,fileName:d.file_name ?? d.fileName,totalBytes:d.total_bytes ?? d.totalBytes,receivedBytes:d.received_bytes ?? d.receivedBytes,status:d.status}}
export async function uploadFileResumable(file:File, metadata:{knowledgeBase:KnowledgeBaseType;projectId?:string;category:string;tags:string;generateSummary:boolean;useCloudOcr:boolean}, onProgress:(received:number,total:number)=>void, signal?:AbortSignal):Promise<KnowledgeDocument>{
  const upload=await initUpload(file); const chunkSize=2*1024*1024
  try { for(let offset=0;offset<file.size;offset+=chunkSize){ const bytes=file.slice(offset,Math.min(file.size,offset+chunkSize)); const r=await fetch(`${BASE}/documents/uploads/${upload.id}/chunk?offset=${offset}`,{method:'PUT',headers:{'Content-Type':'application/octet-stream'},body:bytes,signal});if(!r.ok){const b=await r.json().catch(()=>({}));throw new Error((b as any).detail || `上传分片失败 HTTP ${r.status}`)}const d=await r.json();onProgress(d.received_bytes ?? d.receivedBytes,file.size) }
    const d=await request<any>(`/documents/uploads/${upload.id}/complete`,{method:'POST',body:JSON.stringify({knowledge_base:metadata.knowledgeBase,project_id:metadata.projectId,category:metadata.category,tags:metadata.tags,generate_summary:metadata.generateSummary,use_cloud_ocr:metadata.useCloudOcr})});return documentFromApi(d)
  } catch (e) { if(signal?.aborted) await cancelUpload(upload.id).catch(()=>{}); throw e }
}
export async function cancelUpload(uploadId:string):Promise<{ok:boolean}>{return request(`/documents/uploads/${uploadId}/cancel`,{method:'POST'})}

export interface IngestionJob{id:string;documentId:string;status:string;progress:number;step:string;errorMessage:string|null}
function ingestionJobFromApi(d:any):IngestionJob{return{id:d.id,documentId:d.document_id||d.documentId,status:d.status,progress:d.progress??0,step:d.step||'pending',errorMessage:d.error_message??d.errorMessage??null}}
export async function getIngestionJob(id:string):Promise<IngestionJob>{return ingestionJobFromApi(await request<any>(`/ingestion-jobs/${id}`))}
export async function getDocumentIngestionJob(id:string):Promise<IngestionJob>{return ingestionJobFromApi(await request<any>(`/documents/${id}/ingestion-job`))}
export async function retryIngestionJob(id:string):Promise<any>{return request(`/ingestion-jobs/${id}/retry`,{method:'POST'})}

export async function searchCandidates(params:{keyword:string;target?:string;region?:string;time_range?:string}):Promise<CandidateDocument[]>{return (await request<any[]>('/search',{method:'POST',body:JSON.stringify(params)})).map(c=>({id:c.id,title:c.title,source:c.source||'',publishDate:c.publish_date||c.publishDate||'',summary:c.summary||'',url:c.url||'',credibility:c.credibility||'',reason:c.reason||'',category:c.category||''}))}
export async function ingestCandidate(id:string,payload:{knowledge_base:KnowledgeBaseType;project_id?:string;generate_summary?:boolean}):Promise<KnowledgeDocument>{return documentFromApi(await request<any>(`/search/candidates/${id}/ingest`,{method:'POST',body:JSON.stringify(payload)}))}

function citationFromApi(c:any):Citation{return{id:c.id || `${c.number}-${c.documentName||c.document_name}`,number:c.number,documentId:c.document_id||c.documentId,chunkId:c.chunk_id||c.chunkId,documentName:c.document_name||c.documentName||'',knowledgeBase:(c.knowledge_base||c.knowledgeBase||'project') as KnowledgeBaseType,section:c.section||'',quote:c.quote||'',policyStatus:(c.policy_status||c.policyStatus||'unknown') as any}}
function convFromApi(data:any):ConversationSession { const turns:ChatTurn[]=(data.turns||[]).map((t:any)=>({id:t.id,question:t.question,answer:t.answer||'',citations:(t.citations||[]).map(citationFromApi),status:t.status as ChatTurn['status'],createdAt:t.created_at||t.createdAt||''}));return{id:data.id,title:data.title||'新对话',turns,updatedAt:data.updated_at||data.updatedAt||''} }
export async function listConversations(projectId:string):Promise<ConversationSession[]>{return (await request<any[]>(`/projects/${projectId}/conversations`)).map(convFromApi)}
export async function createConversation(projectId:string,title?:string):Promise<ConversationSession>{return convFromApi(await request<any>(`/projects/${projectId}/conversations`,{method:'POST',body:JSON.stringify({title:title||'新对话'})}))}
export async function getConversation(id:string):Promise<ConversationSession>{return convFromApi(await request<any>(`/conversations/${id}`))}
export async function deleteConversation(id:string):Promise<{ok:boolean}>{return request(`/conversations/${id}`,{method:'DELETE'})}
export interface MessageResponse{id:string;question:string;answer:string;status:string;citations:Citation[];created_at:string}
export async function postMessage(id:string,payload:{question:string;knowledge_source?:KnowledgeSource}):Promise<MessageResponse>{const d=await request<any>(`/conversations/${id}/messages`,{method:'POST',body:JSON.stringify(payload)});return{id:d.id,question:d.question,answer:d.answer||'',status:d.status,citations:(d.citations||[]).map(citationFromApi),created_at:d.created_at||''}}

export type StreamEvent = {type:'started';messageId:string}|{type:'retrieval';chunkCount:number;tableCount:number}|{type:'delta';content:string}|{type:'citation';citation:Citation}|{type:'completed'}|{type:'error';message:string}
export async function streamMessage(projectId:string,conversationId:string,payload:{question:string;knowledge_source?:KnowledgeSource},onEvent:(event:StreamEvent)=>void):Promise<void>{
 const resp=await fetch(`${BASE}/projects/${projectId}/conversations/${conversationId}/messages/stream`,{method:'POST',headers:{'Content-Type':'application/json','Accept':'text/event-stream'},body:JSON.stringify(payload)});if(!resp.ok){const b=await resp.json().catch(()=>({}));throw new Error((b as any).detail || `HTTP ${resp.status}`)}if(!resp.body)throw new Error('浏览器不支持流式响应')
 let terminal = false
 await readEventStream(resp.body, (type, data) => {
   const d = JSON.parse(data)
   if (type === 'message.started') onEvent({type:'started',messageId:d.messageId||d.message_id})
   else if (type === 'retrieval.completed') onEvent({type:'retrieval',chunkCount:d.chunkCount??d.chunk_count??0,tableCount:d.tableCount??d.table_count??0})
   else if (type === 'answer.delta') onEvent({type:'delta',content:d.content||''})
   else if (type === 'citation') onEvent({type:'citation',citation:citationFromApi(d)})
   else if (type === 'message.completed') { terminal = true; onEvent({type:'completed'}) }
   else if (type === 'error') { terminal = true; onEvent({type:'error',message:d.message||'生成失败'}) }
   return terminal
 })
 if (!terminal) throw new Error('连接已中断，回答可能不完整，请重试。')
}

export async function generateDraft(projectId:string,payload:{prompt:string;knowledge_source?:string}):Promise<{id:string;content:string;citations:Citation[]}>{const d=await request<any>(`/projects/${projectId}/drafts/generate`,{method:'POST',body:JSON.stringify(payload)});return{id:d.id,content:d.content,citations:(d.citations||[]).map(citationFromApi)}}
export async function exportDraft(id:string):Promise<{ok:boolean;format:string;content:string}>{return request(`/drafts/${id}/export`,{method:'POST'})}

export interface ProviderConfigOut{id:string;provider:string;api_key_masked:string;base_url:string;model_name?:string;search_provider:string;search_api_key_masked:string;search_base_url?:string;baidu_api_key_masked?:string;baidu_secret_key_masked?:string;ocr_provider?:string;ocr_risk_confirmed?:boolean}
export async function listProviderConfigs():Promise<ProviderConfigOut[]>{return request('/provider-configs')}
export interface ProviderConfigSavePayload {provider:string;api_key?:string;base_url?:string;model_name?:string;search_provider?:string;search_api_key?:string;search_base_url?:string;baidu_api_key?:string;baidu_secret_key?:string;ocr_provider?:string;ocr_risk_confirmed?:boolean}
export async function saveProviderConfig(payload:ProviderConfigSavePayload):Promise<ProviderConfigOut>{return request('/provider-configs',{method:'POST',body:JSON.stringify(payload)})}
export async function testProviderConfig(payload:{provider:string;api_key:string;base_url?:string;model_name?:string}):Promise<{ok:boolean;message:string}>{return request('/provider-configs/test',{method:'POST',body:JSON.stringify(payload)})}
export async function testSearchConfig(payload:{search_provider:string;search_api_key?:string;search_base_url?:string}):Promise<{ok:boolean;message:string}>{return request('/provider-configs/test-search',{method:'POST',body:JSON.stringify(payload)})}
export async function testBaiduOcrConfig(payload:{baidu_api_key:string;baidu_secret_key:string;risk_confirmed:boolean}):Promise<{ok:boolean;message:string}>{return request('/provider-configs/test-baidu-ocr',{method:'POST',body:JSON.stringify(payload)})}
