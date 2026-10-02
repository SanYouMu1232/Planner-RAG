"""Document ingestion: structured parse → reading-order chunks → embedding.

Cloud OCR is only activated when the user selected it at upload time and has
explicitly saved a risk-confirmed Baidu Cloud configuration.
"""
from __future__ import annotations
import asyncio, json, logging
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from .. import crud, models
from ..adapters.llm import LLMProvider
from .chunking import ChunkResult, chunk_blocks, chunk_text
from .embedding import get_embedding_provider
from .text_extractor import extract_text
from .document_files import resolve_document_file
from .baidu_ocr import BaiduPaddleOCRVL, BaiduOCRError
logger=logging.getLogger(__name__)

def _fallback_text(doc:models.Document,warning:str)->str:
    return f"《{doc.file_name}》暂未提取到正文。{warning or '文件可能为空或格式不受支持。'}\n请检查文件，或在明确确认云传输风险后选择百度云端 OCR。"

async def _set_job(db:AsyncSession,job:models.IngestionJob,status:str,progress:int,step:str,error:str|None=None)->None:
    job.status=status; job.progress=progress; job.step=step; job.error_message=error; await db.commit()

async def _resolve_extraction(db:AsyncSession,doc:models.Document):
    if not doc.storage_path: return None
    path = resolve_document_file(doc.storage_path)
    if path is None:
        raise FileNotFoundError("原始文件不存在，请重新上传后重试。")
    # A user explicitly chose cloud OCR. Native Office/PDF parsing is skipped so page layout/order comes from Baidu.
    if doc.ocr_status in {"pending","processing"}:
        cfg=await crud.get_latest_provider_runtime_config(db)
        if not cfg.get("ocr_risk_confirmed") or not cfg.get("baidu_api_key") or not cfg.get("baidu_secret_key"):
            raise BaiduOCRError("该文件已选择云端 OCR，但尚未配置并确认百度云 OCR 的资料上传风险。")
        doc.ocr_status="processing"; await db.commit()
        return await BaiduPaddleOCRVL(cfg["baidu_api_key"],cfg["baidu_secret_key"]).parse(str(path))
    return extract_text(str(path),doc.file_type)

async def process_document(db:AsyncSession,document_id:str,job_id:str|None=None,generate_summary:bool=False)->models.Document:
    doc=await db.get(models.Document,document_id)
    if doc is None: raise ValueError("document not found")
    job=await db.get(models.IngestionJob,job_id) if job_id else None
    if job is None:
        job=models.IngestionJob(document_id=document_id,status="running",progress=5,step="parsing"); db.add(job); await db.commit(); await db.refresh(job)
    try:
        doc.parse_status="parsing"; await _set_job(db,job,"running",15,"parsing")
        extracted=await _resolve_extraction(db,doc)
        text=extracted.text if extracted else ""; warning=extracted.warning if extracted else "文件路径不存在"; source_method=extracted.source_method if extracted else "native_unknown"
        if extracted and extracted.requires_cloud_ocr and not text:
            warning=warning or "该文件需要云端 OCR；未选择百度云端解析。"
        if not text: text=_fallback_text(doc,warning)
        doc.parser_name=extracted.parser_name if extracted else ""
        await db.commit()

        await _set_job(db,job,"running",45,"chunking")
        await db.execute(delete(models.DocumentChunk).where(models.DocumentChunk.document_id==doc.id))
        result:ChunkResult=chunk_blocks(extracted.blocks,source_method=source_method) if extracted and extracted.blocks else chunk_text(text,max_chars=900,overlap_chars=150,source_method=source_method,pages=extracted.pages if extracted else None)
        if not result.chunks: result=chunk_text(_fallback_text(doc,warning),source_method=source_method)
        id_map:dict[int,str]={}
        for c in result.chunks:
            obj=models.DocumentChunk(document_id=doc.id,parent_id=id_map.get(c.parent_index) if c.parent_index is not None else None,
              chunk_index=c.chunk_index,chunk_type=c.chunk_type,section=c.section,heading_path=c.heading_path,clause_number=c.clause_number,page_start=c.page_start,page_end=c.page_end,page_number=c.page_number,text=c.text,token_count=c.token_count,source_method=c.source_method,content_hash=c.content_hash,table_json=c.table_json,reading_order=c.reading_order,bbox_json=c.bbox_json)
            db.add(obj); await db.flush(); id_map[c.chunk_index]=obj.id
        await db.commit()

        if generate_summary:
            doc.parse_status="summarizing"; await _set_job(db,job,"running",70,"summarizing")
            doc.summary=await LLMProvider.summarize(text[:16000],file_name=doc.file_name,provider_config=await crud.get_latest_provider_runtime_config(db)); doc.summary_status="generated"
        else:
            doc.summary=doc.summary or ("已完成结构化解析、表格抽取与阅读顺序保留，可用于问答与引用。" if not warning else f"已入库。提示：{warning}")
            doc.summary_status=doc.summary_status or "not-generated"

        doc.parse_status="vectorizing"; await _set_job(db,job,"running",85,"vectorizing")
        provider=get_embedding_provider(); all_chunks=list((await db.execute(select(models.DocumentChunk).where(models.DocumentChunk.document_id==doc.id))).scalars().all())
        if all_chunks:
            vectors=await provider.embed([c.text for c in all_chunks])
            for c,v in zip(all_chunks,vectors): c.embedding_json=json.dumps({"model_id":provider.config.model_id,"dimension":provider.config.dimension,"version":provider.config.version,"vector":v},ensure_ascii=False)
        await db.commit()
        doc.parse_status="ready"; doc.ocr_status="completed" if extracted and extracted.used_ocr else ("not-required" if not (extracted and extracted.requires_cloud_ocr) else "pending"); doc.is_usable=1
        await _set_job(db,job,"completed",100,"ready"); await db.commit(); await db.refresh(doc); return doc
    except Exception as exc:
        doc.parse_status="failed"; doc.is_usable=0; doc.ocr_status="failed" if doc.ocr_status in {"pending","processing"} else doc.ocr_status; doc.summary_status="failed" if generate_summary else doc.summary_status
        await _set_job(db,job,"failed",max(job.progress,10),job.step or "failed",str(exc)); await db.commit(); await db.refresh(doc); return doc

async def run_ingestion_background(document_id:str,generate_summary:bool=False,job_id:str|None=None)->None:
    from ..database import async_session
    async with async_session() as db:
        try: await process_document(db,document_id,job_id,generate_summary)
        except Exception as exc: logger.exception("Background ingestion failed %s: %s",document_id,exc)

def schedule_ingestion(document_id:str,generate_summary:bool=False,job_id:str|None=None)->None:
    asyncio.ensure_future(run_ingestion_background(document_id,generate_summary,job_id))
