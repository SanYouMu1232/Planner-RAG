"""Ingestion job endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from .. import crud
from ..schemas import IngestionJobOut
from ..serializers import job_out
from ..services.ingestion import process_document

router = APIRouter(prefix="/ingestion-jobs", tags=["ingestion"])


@router.get("/{job_id}", response_model=IngestionJobOut)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    job = await crud.get_ingestion_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="入库任务不存在")
    return job_out(job)


@router.post("/{job_id}/retry", response_model=IngestionJobOut)
async def retry_job(job_id: str, db: AsyncSession = Depends(get_db)):
    job = await crud.get_ingestion_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="入库任务不存在")
    job.status = "running"
    job.progress = 0
    job.step = "retry"
    job.error_message = None
    await db.commit()
    await process_document(db, job.document_id, job.id, generate_summary=False)
    job = await crud.get_ingestion_job(db, job_id)
    return job_out(job)
