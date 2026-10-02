"""Conversation endpoints: dual-library retrieval, persisted memory, real SSE stream."""
from __future__ import annotations
import json
from fastapi import APIRouter,Depends,HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_db
from .. import crud
from ..adapters.llm import LLMProvider,_citation_data
from ..schemas import ConversationCreate,ConversationOut,MessageCreate,MessageOut
from ..serializers import citation_out,conversation_out,dt_str
from ..services.retrieval import retrieve_chunks
router=APIRouter(tags=["conversations"])

@router.get("/projects/{project_id}/conversations",response_model=list[ConversationOut])
async def list_conversations(project_id:str,db:AsyncSession=Depends(get_db)):return [conversation_out(c) for c in await crud.list_conversations(db,project_id)]
@router.post("/projects/{project_id}/conversations",response_model=ConversationOut,status_code=201)
async def create_conversation(project_id:str,body:ConversationCreate,db:AsyncSession=Depends(get_db)):
    if not await crud.get_project(db,project_id):raise HTTPException(404,"项目不存在")
    return conversation_out(await crud.create_conversation(db,project_id,body.title or "新对话"))
@router.get("/conversations/{conv_id}",response_model=ConversationOut)
async def get_conversation(conv_id:str,db:AsyncSession=Depends(get_db)):
    c=await crud.get_conversation(db,conv_id)
    if not c:raise HTTPException(404,"会话不存在")
    return conversation_out(c)
@router.delete("/conversations/{conv_id}",response_model=dict)
async def delete_conversation(conv_id:str,db:AsyncSession=Depends(get_db)):
    if not await crud.delete_conversation(db,conv_id):raise HTTPException(404,"会话不存在")
    return {"ok":True}

def _chunks(rows):
    return [{"document_id":r.doc.id,"chunk_id":r.chunk.id,"file_name":r.doc.file_name,"knowledge_base":r.doc.knowledge_base,"section":r.chunk.section,"text":r.chunk.text,"policy_status":r.doc.policy_status,"chunk_type":r.chunk.chunk_type,"page_start":r.chunk.page_start} for r in rows]
def _event(kind:str,data:dict|None=None)->str:return f"event: {kind}\ndata: {json.dumps(data or {},ensure_ascii=False)}\n\n"

@router.post("/conversations/{conv_id}/messages",response_model=MessageOut,status_code=201)
async def post_message(conv_id:str,body:MessageCreate,db:AsyncSession=Depends(get_db)):
    conv=await crud.get_conversation(db,conv_id)
    if not conv:raise HTTPException(404,"会话不存在")
    history=[{"question":m.question,"answer":m.answer} for m in await crud.list_recent_messages(db,conv_id,10)]
    msg=await crud.create_message(db,conv_id,body.question,str(body.knowledge_source))
    chunks=_chunks(await retrieve_chunks(db,conv.project_id,body.question,str(body.knowledge_source),limit=10))
    answer,citation_data=await LLMProvider.chat(body.question,str(body.knowledge_source),chunks,await crud.get_latest_provider_runtime_config(db),history)
    citations=await crud.create_citations(db,msg.id,citation_data); msg=await crud.update_message_answer(db,msg.id,answer,"done")
    return MessageOut(id=msg.id,question=msg.question,answer=msg.answer,status=msg.status,citations=[citation_out(c) for c in citations],created_at=dt_str(msg.created_at))

@router.post("/projects/{project_id}/conversations/{conversation_id}/messages/stream")
async def post_message_stream(project_id:str,conversation_id:str,body:MessageCreate,db:AsyncSession=Depends(get_db)):
    conv=await crud.get_conversation(db,conversation_id)
    if not conv or conv.project_id!=project_id:raise HTTPException(404,"会话不存在")
    async def stream():
        msg=None
        answer=""
        try:
            history=[{"question":m.question,"answer":m.answer} for m in await crud.list_recent_messages(db,conversation_id,10)]
            msg=await crud.create_message(db,conversation_id,body.question,str(body.knowledge_source));yield _event("message.started",{"messageId":msg.id,"question":msg.question})
            chunks=_chunks(await retrieve_chunks(db,conv.project_id,body.question,str(body.knowledge_source),limit=12));yield _event("retrieval.completed",{"messageId":msg.id,"chunkCount":len(chunks),"tableCount":sum(1 for c in chunks if c["chunk_type"]=="table")})
            answer=""
            async for delta in LLMProvider.stream_chat(body.question,str(body.knowledge_source),chunks,await crud.get_latest_provider_runtime_config(db),history):
                answer+=delta;yield _event("answer.delta",{"messageId":msg.id,"content":delta})
            citations=await crud.create_citations(db,msg.id,_citation_data(chunks));await crud.update_message_answer(db,msg.id,answer,"done")
            for c in citations:yield _event("citation",{"messageId":msg.id,"number":c.number,"documentId":c.document_id,"chunkId":c.chunk_id,"documentName":c.document_name,"knowledgeBase":c.knowledge_base,"section":c.section,"quote":c.quote,"policyStatus":c.policy_status})
            yield _event("message.completed",{"messageId":msg.id,"status":"done"})
        except Exception as exc:
            if msg:await crud.update_message_answer(db,msg.id,f"{answer}\n\n生成失败：{exc}".strip(),"failed")
            yield _event("error",{"code":"STREAM_ERROR","message":str(exc)})
    return StreamingResponse(stream(),media_type="text/event-stream",headers={"Cache-Control":"no-cache","Connection":"keep-alive","X-Accel-Buffering":"no"})
