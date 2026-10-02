import io
import pytest


@pytest.mark.asyncio
async def test_get_ingestion_job(client):
    # Upload creates an ingestion job automatically
    content = io.BytesIO(b"fake")
    resp = await client.post(
        "/api/documents/upload",
        files={"files": ("job_test.pdf", content, "application/pdf")},
    )
    doc_id = resp.json()[0]["id"]

    # Find the job via document
    from app.database import async_session
    from sqlalchemy import select
    from app.models import IngestionJob

    async with async_session() as session:
        result = await session.execute(
            select(IngestionJob).where(IngestionJob.document_id == doc_id)
        )
        job = result.scalar_one_or_none()

    assert job is not None

    resp = await client.get(f"/api/ingestion-jobs/{job.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["documentId"] == doc_id


@pytest.mark.asyncio
async def test_retry_ingestion_job(client):
    content = io.BytesIO(b"fake")
    resp = await client.post(
        "/api/documents/upload",
        files={"files": ("retry_test.pdf", content, "application/pdf")},
    )
    doc_id = resp.json()[0]["id"]

    from app.database import async_session
    from sqlalchemy import select
    from app.models import IngestionJob

    async with async_session() as session:
        result = await session.execute(
            select(IngestionJob).where(IngestionJob.document_id == doc_id)
        )
        job = result.scalar_one_or_none()

    resp = await client.post(f"/api/ingestion-jobs/{job.id}/retry")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["progress"] == 100


@pytest.mark.asyncio
async def test_ingestion_job_404(client):
    resp = await client.get("/api/ingestion-jobs/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_upload_creates_ingestion_job(client):
    """Upload returns a document with an associated ingestion job that can be polled."""
    content = io.BytesIO(b"test content for job polling")
    resp = await client.post(
        "/api/documents/upload",
        files={"files": ("poll_test.txt", content, "text/plain")},
    )
    assert resp.status_code == 201
    docs = resp.json()
    assert len(docs) == 1
    doc = docs[0]

    # Find the job via the document ingestion-job endpoint
    resp = await client.get(f"/api/documents/{doc['id']}/ingestion-job")
    assert resp.status_code == 200
    job = resp.json()
    assert job["documentId"] == doc["id"]
    # In sync/test mode, job should be completed
    assert job["status"] == "completed"
    assert job["progress"] == 100
    assert job["step"] == "ready"
    assert "createdAt" in job
    assert "updatedAt" in job


@pytest.mark.asyncio
async def test_ingestion_job_rich_progress(client):
    """Ingestion job reports rich stage/progress fields compatible with clients."""
    content = io.BytesIO(b"rich progress test content for ingestion pipeline")
    resp = await client.post(
        "/api/documents/upload",
        files={"files": ("rich.pdf", content, "application/pdf")},
    )
    assert resp.status_code == 201
    doc = resp.json()[0]

    resp = await client.get(f"/api/documents/{doc['id']}/ingestion-job")
    assert resp.status_code == 200
    job = resp.json()
    assert "status" in job
    assert "progress" in job
    assert "step" in job
    assert "errorMessage" in job
    assert "updatedAt" in job

@pytest.mark.asyncio
async def test_ingestion_fails_when_stub_embedding_disallowed(client, monkeypatch):
    """Production-like config must fail visibly instead of marking docs ready with stub embeddings."""
    import app.config as cfg
    from app.services.embedding import reset_embedding_provider

    monkeypatch.setattr(cfg, "ALLOW_STUB_EMBEDDING", False)
    monkeypatch.setattr(cfg, "EMBEDDING_PROVIDER", "stub")
    reset_embedding_provider()

    content = io.BytesIO("真实文本内容，用于验证生产模式禁止 stub embedding".encode("utf-8"))
    resp = await client.post(
        "/api/documents/upload",
        files={"files": ("prod_stub_block.txt", content, "text/plain")},
    )
    assert resp.status_code == 201
    doc = resp.json()[0]
    assert doc["parseStatus"] == "failed"
    assert doc["isUsable"] is False

    job_resp = await client.get(f"/api/documents/{doc['id']}/ingestion-job")
    assert job_resp.status_code == 200
    job = job_resp.json()
    assert job["status"] == "failed"
    assert "Stub embedding provider is not allowed" in job["errorMessage"]

    reset_embedding_provider()
    monkeypatch.setattr(cfg, "ALLOW_STUB_EMBEDDING", True)
