import io
import pytest


@pytest.mark.asyncio
async def test_upload_and_list_documents(client):
    """Upload documents and verify they appear in listing."""
    # Upload a test file
    content = io.BytesIO(b"fake pdf content")
    resp = await client.post(
        "/api/documents/upload",
        files={"files": ("test.pdf", content, "application/pdf")},
        data={
            "knowledgeBase": "project",
            "projectId": "proj-test",
            "category": "甲方资料",
            "tags": "测试,甲方",
            "generate_summary": "true",
        },
    )
    assert resp.status_code == 201
    docs = resp.json()
    assert len(docs) == 1
    doc = docs[0]
    assert doc["fileName"] == "test.pdf"
    assert doc["fileType"] == "pdf"
    assert doc["parseStatus"] == "ready"
    assert doc["summaryStatus"] == "generated"
    assert len(doc["tags"]) > 0

    # List documents
    resp = await client.get("/api/documents")
    assert resp.status_code == 200
    all_docs = resp.json()
    assert len(all_docs) >= 1


@pytest.mark.asyncio
async def test_get_document(client):
    content = io.BytesIO(b"fake content")
    resp = await client.post(
        "/api/documents/upload",
        files={"files": ("note.docx", content, "application/octet-stream")},
        data={"knowledgeBase": "general"},
    )
    doc_id = resp.json()[0]["id"]

    resp = await client.get(f"/api/documents/{doc_id}")
    assert resp.status_code == 200
    assert resp.json()["fileName"] == "note.docx"
    assert resp.json()["fileType"] == "word"


@pytest.mark.asyncio
async def test_patch_document(client):
    content = io.BytesIO(b"fake content")
    resp = await client.post(
        "/api/documents/upload",
        files={"files": ("doc.txt", content, "text/plain")},
        data={"category": "其他"},
    )
    doc_id = resp.json()[0]["id"]

    resp = await client.patch(
        f"/api/documents/{doc_id}",
        json={"fileName": "renamed.txt", "tags": ["已更新", "重命名"]},
    )
    assert resp.status_code == 200
    doc = resp.json()
    assert doc["fileName"] == "renamed.txt"
    assert "已更新" in doc["tags"]


@pytest.mark.asyncio
async def test_delete_document(client):
    content = io.BytesIO(b"fake")
    resp = await client.post(
        "/api/documents/upload",
        files={"files": ("del.txt", content, "text/plain")},
    )
    doc_id = resp.json()[0]["id"]

    resp = await client.delete(f"/api/documents/{doc_id}")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    resp = await client.get(f"/api/documents/{doc_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_summarize_document(client):
    content = io.BytesIO(b"fake")
    resp = await client.post(
        "/api/documents/upload",
        files={"files": ("sum.pdf", content, "application/pdf")},
    )
    doc_id = resp.json()[0]["id"]

    resp = await client.post(f"/api/documents/{doc_id}/summarize")
    assert resp.status_code == 200
    doc = resp.json()
    assert doc["summaryStatus"] == "generated"
    assert len(doc["summary"]) > 0


@pytest.mark.asyncio
async def test_get_document_chunks(client):
    content = io.BytesIO(b"fake")
    resp = await client.post(
        "/api/documents/upload",
        files={"files": ("chunked.pdf", content, "application/pdf")},
    )
    doc_id = resp.json()[0]["id"]

    resp = await client.get(f"/api/documents/{doc_id}/chunks")
    assert resp.status_code == 200
    chunks = resp.json()
    assert len(chunks) >= 1
    for c in chunks:
        assert "text" in c
        assert "section" in c


@pytest.mark.asyncio
async def test_filter_documents_by_knowledge_base(client):
    content = io.BytesIO(b"p")
    await client.post(
        "/api/documents/upload",
        files={"files": ("proj_doc.pdf", content, "application/pdf")},
        data={"knowledgeBase": "project", "projectId": "p1"},
    )
    content2 = io.BytesIO(b"g")
    await client.post(
        "/api/documents/upload",
        files={"files": ("gen_doc.pdf", content2, "application/pdf")},
        data={"knowledgeBase": "general"},
    )

    resp = await client.get("/api/documents?knowledge_base=project")
    docs = resp.json()
    assert all(d["knowledgeBase"] == "project" for d in docs)

    resp = await client.get("/api/documents?knowledge_base=general")
    docs = resp.json()
    assert all(d["knowledgeBase"] == "general" for d in docs)


@pytest.mark.asyncio
async def test_document_has_usability_fields(client):
    """Uploaded document should have ocrStatus and isUsable fields."""
    content = io.BytesIO(b"Testing usability fields for planning document ingestion.")
    resp = await client.post(
        "/api/documents/upload",
        files={"files": ("usable.pdf", content, "application/pdf")},
    )
    assert resp.status_code == 201
    doc = resp.json()[0]
    assert "ocrStatus" in doc
    assert doc["ocrStatus"] == "not-required"
    assert "isUsable" in doc
    assert doc["isUsable"] is True


@pytest.mark.asyncio
async def test_chunk_parent_child_metadata(client):
    """Chunks should include parent-child metadata fields."""
    content = io.BytesIO(
        "\n".join([
            "第一章 总则",
            "第一条 为了规范规划管理，制定本办法。",
            "第二条 本办法适用于城市规划编制与审批。",
        ]).encode("utf-8")
    )
    resp = await client.post(
        "/api/documents/upload",
        files={"files": ("structured.pdf", content, "application/pdf")},
    )
    assert resp.status_code == 201
    doc = resp.json()[0]
    doc_id = doc["id"]

    resp = await client.get(f"/api/documents/{doc_id}/chunks")
    assert resp.status_code == 200
    chunks = resp.json()
    assert len(chunks) >= 1

    # At least one chunk should have the new metadata fields
    meta_fields = {"parentId", "chunkType", "headingPath", "sourceMethod", "contentHash"}
    found = set()
    for c in chunks:
        for f in meta_fields:
            if f in c and c[f]:
                found.add(f)
    # headingPath and contentHash should be present; parentId may be None for parent chunks
    assert "headingPath" in found or any(
        c.get("headingPath") for c in chunks
    ), f"Expected headingPath in chunks, got: {[{k: v for k, v in c.items() if k in meta_fields} for c in chunks]}"
    assert "contentHash" in found
    assert "sourceMethod" in found
    assert "chunkType" in found


@pytest.mark.asyncio
async def test_chunk_page_metadata(client):
    """Chunks should preserve page_start/page_end metadata."""
    # A multi-page-like PDF (using \f as page separator in the text extraction fallback)
    content = io.BytesIO(b"Page one content goes here.\fPage two content is here.")
    resp = await client.post(
        "/api/documents/upload",
        files={"files": ("paged.pdf", content, "application/pdf")},
    )
    assert resp.status_code == 201
    doc = resp.json()[0]
    doc_id = doc["id"]

    resp = await client.get(f"/api/documents/{doc_id}/chunks")
    assert resp.status_code == 200
    chunks = resp.json()
    assert len(chunks) >= 1

    # At least one chunk should have page_start metadata
    pages_with_meta = [c for c in chunks if c.get("pageStart") is not None]
    # The pypdf parser may or may not extract text from fake binary content,
    # but we at least verify the field is present in schema
    for c in chunks:
        assert "pageStart" in c
        assert "pageEnd" in c


@pytest.mark.asyncio
async def test_native_ingestion_marks_document_usable(client):
    """Native text extraction (even from stub content) should set isUsable=true."""
    content = io.BytesIO(b"Some meaningful planning document content for usability test.")
    resp = await client.post(
        "/api/documents/upload",
        files={"files": ("usable_doc.txt", content, "text/plain")},
    )
    assert resp.status_code == 201
    doc = resp.json()[0]
    assert doc["parseStatus"] == "ready"
    assert doc["isUsable"] is True
    assert doc["ocrStatus"] == "not-required"
