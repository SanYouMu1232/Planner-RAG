"""Search and explicit webpage-content ingestion."""
from __future__ import annotations
import json, uuid
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db
from .. import crud,models
from ..adapters.search import SearchProvider,SearchProviderError
from ..schemas import CandidateIngestRequest,CandidateOut,DocumentOut,SearchRequest
from ..serializers import candidate_out,document_out
from ..services.chunking import chunk_blocks
from ..services.embedding import get_embedding_provider
from ..services.web_content import fetch_webpage,WebContentError
from ..config import UPLOAD_DIR
router=APIRouter(prefix="/search",tags=["search"])
def _now():return datetime.utcnow().strftime("%Y-%m-%d")

@router.post("",response_model=list[CandidateOut])
async def search(body:SearchRequest,db:AsyncSession=Depends(get_db)):
    try:
        cfg=await crud.get_latest_provider_runtime_config(db)
        if not cfg.get("search_provider") or cfg.get("search_provider") in {"", "暂不配置"}:
            return []
        results=await SearchProvider.search(body.keyword,body.target,body.region,body.time_range,cfg)
        return [candidate_out(x) for x in await crud.create_search_candidates(db,results)]
    except SearchProviderError as exc: raise HTTPException(409,str(exc))

@router.post("/candidates/{candidate_id}/ingest",response_model=DocumentOut)
async def ingest_candidate(candidate_id:str,body:CandidateIngestRequest,db:AsyncSession=Depends(get_db)):
    candidate=await crud.get_search_candidate(db,candidate_id)
    if candidate is None:raise HTTPException(404,"候选资料不存在")
    if str(body.knowledge_base)=="project" and not body.project_id:raise HTTPException(422,"加入项目知识库时必须提供 projectId")
    if not candidate.url:raise HTTPException(422,"候选结果没有可抓取的网页链接")
    try:title,extracted=await fetch_webpage(candidate.url)
    except WebContentError as exc:raise HTTPException(502,f"网页内容解析失败：{exc}")
    Path(UPLOAD_DIR).mkdir(parents=True,exist_ok=True); path=Path(UPLOAD_DIR)/f"web_{uuid.uuid4().hex[:12]}.txt"; path.write_text(extracted.text,encoding="utf-8")
    doc=await crud.create_document(db,{"file_name":candidate.title or title,"file_type":"web","category":candidate.category or "公开资料","tags":",".join(x for x in [candidate.credibility,candidate.category] if x),"source":candidate.source,"source_url":candidate.url,"publish_date":candidate.publish_date or _now(),"policy_status":"active" if candidate.credibility in {"政府官网","国家标准"} else "unknown","knowledge_base":str(body.knowledge_base),"project_id":body.project_id,"parse_status":"vectorizing","ocr_status":"not-required","is_usable":0,"summary_status":"generated" if body.generate_summary else "not-generated","summary":candidate.summary if body.generate_summary else "已抓取网页正文与表格，待检索使用。","storage_path":str(path),"file_size":path.stat().st_size,"checksum":"","parser_name":extracted.parser_name})
    result=chunk_blocks(extracted.blocks,source_method=extracted.source_method); id_map={}
    for c in result.chunks:
        obj=models.DocumentChunk(document_id=doc.id,parent_id=id_map.get(c.parent_index) if c.parent_index is not None else None,chunk_index=c.chunk_index,chunk_type=c.chunk_type,section=c.section,heading_path=c.heading_path,clause_number=c.clause_number,page_start=c.page_start,page_end=c.page_end,page_number=c.page_number,text=c.text,token_count=c.token_count,source_method=c.source_method,content_hash=c.content_hash,table_json=c.table_json,reading_order=c.reading_order,bbox_json=c.bbox_json); db.add(obj);await db.flush();id_map[c.chunk_index]=obj.id
    provider=get_embedding_provider(); chunks=list((await db.execute(select(models.DocumentChunk).where(models.DocumentChunk.document_id==doc.id))).scalars().all()); vectors=await provider.embed([c.text for c in chunks])
    for c,v in zip(chunks,vectors):c.embedding_json=json.dumps({"model_id":provider.config.model_id,"dimension":provider.config.dimension,"version":provider.config.version,"vector":v},ensure_ascii=False)
    doc.parse_status="ready";doc.is_usable=1;db.add(models.IngestionJob(document_id=doc.id,status="completed",progress=100,step="ready"));await db.commit();await db.refresh(doc);return document_out(doc)
