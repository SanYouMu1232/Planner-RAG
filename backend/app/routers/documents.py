"""Document CRUD plus resumable/cancellable uploads."""
from __future__ import annotations
import os,re,shutil,uuid
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from mimetypes import guess_type
from sqlalchemy.ext.asyncio import AsyncSession
from ..config import INGESTION_MODE, MAX_UPLOAD_MB, UPLOAD_DIR, UPLOAD_TEMP_DIR, UPLOAD_CHUNK_SIZE
from ..database import get_db
from .. import crud
from ..schemas import DocumentOut,DocumentUpdate,ChunkOut,IngestionJobOut,UploadInitRequest,UploadCompleteRequest,UploadSessionOut
from ..serializers import document_out,chunk_out,job_out
from ..services.ingestion import process_document,run_ingestion_background
from ..services.text_extractor import file_checksum
from ..services.document_files import resolve_document_file
router=APIRouter(prefix="/documents",tags=["documents"])

def _today(): return datetime.utcnow().strftime("%Y-%m-%d")
def _sanitize_filename(filename:str)->str:
    name=Path(filename or "upload").name; name=re.sub(r"[\\/:*?\"<>|]+","_",name).strip() or "upload"; return name[:180]
def _infer_file_type(filename:str)->str:
    lower=filename.lower()
    if lower.endswith(".pdf"): return "pdf"
    if lower.endswith((".docx",".doc")): return "word"
    if lower.endswith((".pptx",".ppt")): return "ppt"
    if lower.endswith((".xlsx",".xls")): return "excel"
    if lower.endswith((".png",".jpg",".jpeg",".webp",".bmp",".tif",".tiff",".ofd")): return "image"
    if lower.endswith((".txt",".md",".csv")): return "txt"
    return "other"
def _infer_category(filename:str)->str:
    if "会议" in filename:return "会议纪要"
    if "评审" in filename:return "评审意见"
    if "导则" in filename or "标准" in filename:return "技术标准"
    if "政策" in filename or "办法" in filename:return "政策法规"
    if "规划" in filename:return "上位规划"
    return "甲方资料"
def _validate_file_name(name:str):
    if Path(name).suffix.lower() not in {".pdf",".doc",".docx",".ppt",".pptx",".xls",".xlsx",".txt",".md",".csv",".png",".jpg",".jpeg",".webp",".bmp",".tif",".tiff",".ofd"}:
        raise HTTPException(415,"当前支持 Word、PDF、PPT、Excel、文本、图片和扫描件。")
async def _save_upload(file:UploadFile)->tuple[str,int,str]:
    _validate_file_name(file.filename or "")
    Path(UPLOAD_DIR).mkdir(parents=True,exist_ok=True); original=_sanitize_filename(file.filename or "upload"); dest=Path(UPLOAD_DIR)/f"{uuid.uuid4().hex[:12]}_{original}"; size=0;limit=MAX_UPLOAD_MB*1024*1024
    try:
        with open(dest,"wb") as f:
            while chunk:=await file.read(1024*1024):
                size+=len(chunk)
                if size>limit: raise HTTPException(413,f"单文件不能超过 {MAX_UPLOAD_MB}MB")
                f.write(chunk)
    except Exception:
        dest.unlink(missing_ok=True); raise
    return str(dest),size,file_checksum(dest)
async def _create_and_start(db:AsyncSession,storage_path:str,file_name:str,knowledge_base:str,project_id:str|None,generate_summary:bool,category:str,tags:str,use_cloud_ocr:bool,background_tasks:BackgroundTasks|None=None):
    doc=await crud.create_document(db,{"file_name":_sanitize_filename(file_name),"file_type":_infer_file_type(file_name),"category":category or _infer_category(file_name),"tags":tags,"source":"用户上传","publish_date":_today(),"policy_status":"unknown","knowledge_base":knowledge_base,"project_id":project_id if knowledge_base=="project" else None,"parse_status":"uploading","ocr_status":"pending" if use_cloud_ocr else "not-required","summary_status":"not-generated","summary":"","storage_path":storage_path,"file_size":Path(storage_path).stat().st_size,"checksum":file_checksum(storage_path)})
    job=await crud.create_ingestion_job(db,doc.id,status="running",progress=5,step="uploading")
    if INGESTION_MODE=="sync": doc=await process_document(db,doc.id,job.id,generate_summary)
    elif background_tasks is not None: background_tasks.add_task(run_ingestion_background,doc.id,generate_summary,job.id)
    return doc

@router.get("",response_model=list[DocumentOut])
async def list_documents(knowledge_base:str|None=None,project_id:str|None=None,keyword:str|None=None,category:str|None=None,tag:str|None=None,status:str|None=None,db:AsyncSession=Depends(get_db)):
    return [document_out(x) for x in await crud.list_documents(db,knowledge_base,project_id,keyword,category,tag,status)]

@router.post("/upload",response_model=list[DocumentOut],status_code=201)
async def upload_documents(files:list[UploadFile]=File(...),background_tasks:BackgroundTasks=None,knowledge_base:str=Form(""),project_id:str=Form(""),generate_summary:bool=Form(False),knowledgeBase:str|None=Form(None),projectId:str|None=Form(None),generateSummary:bool|None=Form(None),category:str=Form(""),tags:str=Form("甲方资料,待核验"),use_cloud_ocr:bool=Form(False),useCloudOcr:bool|None=Form(None),db:AsyncSession=Depends(get_db)):
    knowledge_base=knowledgeBase or knowledge_base or "general"; project_id=projectId or project_id; generate_summary=generateSummary if generateSummary is not None else generate_summary; use_cloud_ocr=useCloudOcr if useCloudOcr is not None else use_cloud_ocr
    if knowledge_base not in {"project","general"}: raise HTTPException(422,"知识库类型必须是 project 或 general")
    if knowledge_base=="project" and not project_id: raise HTTPException(422,"项目知识库必须选择项目")
    result=[]
    for file in files:
        path,_,_=await _save_upload(file)
        result.append(document_out(await _create_and_start(db,path,file.filename or "未知文件",knowledge_base,project_id or None,generate_summary,category,tags,use_cloud_ocr,background_tasks)))
    return result

@router.post("/uploads/init",response_model=UploadSessionOut,status_code=201)
async def upload_init(body:UploadInitRequest,db:AsyncSession=Depends(get_db)):
    _validate_file_name(body.file_name)
    if body.total_bytes>MAX_UPLOAD_MB*1024*1024: raise HTTPException(413,f"单文件不能超过 {MAX_UPLOAD_MB}MB")
    Path(UPLOAD_TEMP_DIR).mkdir(parents=True,exist_ok=True); temp=Path(UPLOAD_TEMP_DIR)/f"{uuid.uuid4().hex}.part"; item=await crud.create_upload_session(db,_sanitize_filename(body.file_name),str(temp),body.total_bytes)
    return UploadSessionOut(id=item.id,file_name=item.file_name,total_bytes=item.total_bytes,received_bytes=item.received_bytes,status=item.status)

@router.put("/uploads/{upload_id}/chunk",response_model=UploadSessionOut)
async def upload_chunk(upload_id:str,request:Request,offset:int,db:AsyncSession=Depends(get_db)):
    item=await crud.get_upload_session(db,upload_id)
    if item is None: raise HTTPException(404,"上传会话不存在或已过期")
    if item.status=="cancelled": raise HTTPException(409,"上传已取消")
    if offset!=item.received_bytes: raise HTTPException(409,f"分片偏移错误，服务端已接收 {item.received_bytes} 字节")
    data=await request.body()
    if not data: raise HTTPException(422,"上传分片为空")
    if item.received_bytes+len(data)>item.total_bytes: raise HTTPException(413,"分片超过声明文件大小")
    path=Path(item.temp_path); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("ab") as f:f.write(data)
    item=await crud.update_upload_session(db,upload_id,received_bytes=item.received_bytes+len(data),status="uploading")
    return UploadSessionOut(id=item.id,file_name=item.file_name,total_bytes=item.total_bytes,received_bytes=item.received_bytes,status=item.status)

@router.post("/uploads/{upload_id}/cancel",response_model=dict)
async def upload_cancel(upload_id:str,db:AsyncSession=Depends(get_db)):
    item=await crud.get_upload_session(db,upload_id)
    if item is None:return {"ok":True,"alreadyGone":True}
    Path(item.temp_path).unlink(missing_ok=True); await crud.update_upload_session(db,upload_id,status="cancelled"); return {"ok":True}

@router.post("/uploads/{upload_id}/complete",response_model=DocumentOut,status_code=201)
async def upload_complete(upload_id:str,body:UploadCompleteRequest,background_tasks:BackgroundTasks=None,db:AsyncSession=Depends(get_db)):
    item=await crud.get_upload_session(db,upload_id)
    if item is None: raise HTTPException(404,"上传会话不存在")
    if item.status=="cancelled": raise HTTPException(409,"上传已取消")
    if item.received_bytes!=item.total_bytes: raise HTTPException(409,"文件尚未上传完整")
    if body.knowledge_base=="project" and not body.project_id: raise HTTPException(422,"项目知识库必须选择项目")
    temp=Path(item.temp_path)
    if not temp.exists(): raise HTTPException(409,"上传临时文件不存在")
    Path(UPLOAD_DIR).mkdir(parents=True,exist_ok=True); dest=Path(UPLOAD_DIR)/f"{uuid.uuid4().hex[:12]}_{item.file_name}"; shutil.move(str(temp),dest); await crud.update_upload_session(db,upload_id,status="completed")
    doc=await _create_and_start(db,str(dest),item.file_name,str(body.knowledge_base),body.project_id,body.generate_summary,body.category,body.tags,body.use_cloud_ocr,background_tasks)
    return document_out(doc)

@router.get("/{doc_id}",response_model=DocumentOut)
async def get_document(doc_id:str,db:AsyncSession=Depends(get_db)):
    doc=await crud.get_document(db,doc_id)
    if doc is None:raise HTTPException(404,"资料不存在")
    return document_out(doc)
@router.patch("/{doc_id}",response_model=DocumentOut)
async def update_document(doc_id:str,body:DocumentUpdate,db:AsyncSession=Depends(get_db)):
    data=body.model_dump(exclude_none=True)
    if isinstance(data.get("tags"),list):data["tags"]=",".join(data["tags"])
    doc=await crud.update_document(db,doc_id,data)
    if doc is None:raise HTTPException(404,"资料不存在")
    return document_out(doc)
@router.delete("/{doc_id}",response_model=dict)
async def delete_document(doc_id:str,db:AsyncSession=Depends(get_db)):
    if not await crud.delete_document(db,doc_id):raise HTTPException(404,"资料不存在")
    return {"ok":True}
@router.post("/{doc_id}/summarize",response_model=DocumentOut)
async def summarize_document(doc_id:str,db:AsyncSession=Depends(get_db)):
    doc=await crud.get_document(db,doc_id)
    if doc is None:raise HTTPException(404,"资料不存在")
    job=await crud.create_ingestion_job(db,doc.id,status="running",progress=0,step="retry")
    doc=await process_document(db,doc.id,job.id,generate_summary=True)
    return document_out(doc)
@router.get("/{doc_id}/chunks",response_model=list[ChunkOut])
async def get_document_chunks(doc_id:str,db:AsyncSession=Depends(get_db)):
    if not await crud.get_document(db,doc_id):raise HTTPException(404,"资料不存在")
    return [chunk_out(c) for c in await crud.list_chunks(db,doc_id)]

@router.get("/{doc_id}/file")
async def get_document_file(doc_id: str, db: AsyncSession = Depends(get_db)):
    doc = await crud.get_document(db, doc_id)
    if doc is None:
        raise HTTPException(404, "资料不存在")
    path = resolve_document_file(doc.storage_path)
    if path is None:
        raise HTTPException(404, "原始文件不存在，请重新上传；已解析正文仍可在原文预览中查看。")
    inline = path.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    return FileResponse(
        path, filename=doc.file_name,
        media_type=guess_type(path.name)[0] or "application/octet-stream",
        content_disposition_type="inline" if inline else "attachment",
        headers={"X-Content-Type-Options": "nosniff"},
    )

@router.get("/{doc_id}/ingestion-job",response_model=IngestionJobOut)
async def get_document_ingestion_job(doc_id:str,db:AsyncSession=Depends(get_db)):
    job=await crud.get_latest_document_job(db,doc_id)
    if job is None:raise HTTPException(404,"入库任务不存在")
    return job_out(job)
