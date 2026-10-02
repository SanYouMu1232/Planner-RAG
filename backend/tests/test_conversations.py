import io
import pytest


@pytest.mark.asyncio
async def test_create_conversation(client):
    # Need a project first
    resp = await client.post("/api/projects", json={"name": "对话测试项目"})
    pid = resp.json()["id"]

    resp = await client.post(f"/api/projects/{pid}/conversations", json={"title": "测试对话"})
    assert resp.status_code == 201
    conv = resp.json()
    assert conv["title"] == "测试对话"
    assert conv["turns"] == []


@pytest.mark.asyncio
async def test_list_conversations(client):
    resp = await client.post("/api/projects", json={"name": "列表测试"})
    pid = resp.json()["id"]

    await client.post(f"/api/projects/{pid}/conversations", json={"title": "C1"})
    await client.post(f"/api/projects/{pid}/conversations", json={"title": "C2"})

    resp = await client.get(f"/api/projects/{pid}/conversations")
    assert resp.status_code == 200
    convs = resp.json()
    assert len(convs) == 2


@pytest.mark.asyncio
async def test_get_and_delete_conversation(client):
    resp = await client.post("/api/projects", json={"name": "删对话测试"})
    pid = resp.json()["id"]

    resp = await client.post(f"/api/projects/{pid}/conversations", json={"title": "待删除"})
    cid = resp.json()["id"]

    resp = await client.get(f"/api/conversations/{cid}")
    assert resp.status_code == 200

    resp = await client.delete(f"/api/conversations/{cid}")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    resp = await client.get(f"/api/conversations/{cid}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_post_message_no_knowledge(client):
    """Ask a question with no documents — expect the 'no knowledge' message."""
    resp = await client.post("/api/projects", json={"name": "空知识库"})
    pid = resp.json()["id"]

    resp = await client.post(f"/api/projects/{pid}/conversations", json={"title": "问答测试"})
    cid = resp.json()["id"]

    resp = await client.post(f"/api/conversations/{cid}/messages", json={
        "question": "测试问题",
        "knowledge_source": "both",
    })
    assert resp.status_code == 201
    msg = resp.json()
    assert msg["status"] == "done"
    assert "当前知识库" in msg["answer"] or "可以正常交流" in msg["answer"]
    assert "拒绝" not in msg["answer"]
    assert msg["citations"] == []


@pytest.mark.asyncio
async def test_post_message_with_documents(client):
    """Ask a question with ready documents — expect answer with citations."""
    resp = await client.post("/api/projects", json={"name": "有资料项目"})
    pid = resp.json()["id"]

    # Upload a ready document
    content = io.BytesIO(b"fake")
    await client.post(
        "/api/documents/upload",
        files={"files": ("甲方任务书.pdf", content, "application/pdf")},
        data={"knowledgeBase": "project", "projectId": pid, "generate_summary": "true"},
    )

    resp = await client.post(f"/api/projects/{pid}/conversations", json={"title": "有资料问答"})
    cid = resp.json()["id"]

    resp = await client.post(f"/api/conversations/{cid}/messages", json={
        "question": "甲方有哪些要求？",
        "knowledge_source": "project",
    })
    assert resp.status_code == 201
    msg = resp.json()
    assert msg["status"] == "done"
    assert len(msg["answer"]) > 0
    assert "未找到明确依据" not in msg["answer"]
    assert len(msg["citations"]) > 0

    # Verify citations have required fields
    for cit in msg["citations"]:
        assert cit["number"] > 0
        assert len(cit["documentName"]) > 0
        assert "section" in cit
        assert "quote" in cit


@pytest.mark.asyncio
async def test_sse_streaming_endpoint(client):
    """SSE streaming endpoint emits expected events."""
    resp = await client.post("/api/projects", json={"name": "SSE测试项目"})
    pid = resp.json()["id"]

    # Upload a document so retrieval has something to find
    content = io.BytesIO(b"fake pdf content for sse test")
    await client.post(
        "/api/documents/upload",
        files={"files": ("sse_doc.pdf", content, "application/pdf")},
        data={"knowledgeBase": "project", "projectId": pid},
    )

    resp = await client.post(f"/api/projects/{pid}/conversations", json={"title": "SSE对话"})
    cid = resp.json()["id"]

    # Call the SSE streaming endpoint
    resp = await client.post(
        f"/api/projects/{pid}/conversations/{cid}/messages/stream",
        json={"question": "测试SSE流式问题", "knowledge_source": "both"},
        timeout=30,
    )
    assert resp.status_code == 200
    body = resp.text

    # Verify required SSE events are present
    assert "message.started" in body
    assert "retrieval.completed" in body
    assert "answer.delta" in body
    assert "citation" in body
    assert "message.completed" in body
    # Verify SSE format: "event:" and "data:" lines
    assert "event:" in body
    assert "data:" in body


@pytest.mark.asyncio
async def test_sse_streaming_no_knowledge(client):
    """SSE streaming with no documents should still emit events and complete."""
    resp = await client.post("/api/projects", json={"name": "空SSE项目"})
    pid = resp.json()["id"]

    resp = await client.post(f"/api/projects/{pid}/conversations", json={"title": "空SSE对话"})
    cid = resp.json()["id"]

    resp = await client.post(
        f"/api/projects/{pid}/conversations/{cid}/messages/stream",
        json={"question": "空知识库的SSE问题", "knowledge_source": "both"},
        timeout=30,
    )
    assert resp.status_code == 200
    body = resp.text
    assert "message.started" in body
    assert "message.completed" in body


@pytest.mark.asyncio
async def test_retrieval_isolation_project_a_not_see_project_b(client):
    """Project A should not see Project B documents, and vice versa."""
    # Create two projects
    resp = await client.post("/api/projects", json={"name": "项目A"})
    pid_a = resp.json()["id"]
    resp = await client.post("/api/projects", json={"name": "项目B"})
    pid_b = resp.json()["id"]

    # Upload document to project A only
    content_a = io.BytesIO("项目A专属文档内容".encode("utf-8"))
    resp = await client.post(
        "/api/documents/upload",
        files={"files": ("a_doc.txt", content_a, "text/plain")},
        data={"knowledgeBase": "project", "projectId": pid_a},
    )
    doc_a = resp.json()[0]

    # Upload document to project B only
    content_b = io.BytesIO("项目B专属文档内容".encode("utf-8"))
    resp = await client.post(
        "/api/documents/upload",
        files={"files": ("b_doc.txt", content_b, "text/plain")},
        data={"knowledgeBase": "project", "projectId": pid_b},
    )
    doc_b = resp.json()[0]

    # Verify each project only sees its own documents
    resp = await client.get(f"/api/documents?project_id={pid_a}")
    docs_a = resp.json()
    assert all(d["projectId"] == pid_a or d["knowledgeBase"] == "general" for d in docs_a)
    assert any(d["id"] == doc_a["id"] for d in docs_a)

    resp = await client.get(f"/api/documents?project_id={pid_b}")
    docs_b = resp.json()
    assert all(d["projectId"] == pid_b or d["knowledgeBase"] == "general" for d in docs_b)
    assert any(d["id"] == doc_b["id"] for d in docs_b)


@pytest.mark.asyncio
async def test_retrieval_isolation_general_knowledge_base(client):
    """General knowledge base documents are visible across projects."""
    # Upload to general knowledge base
    content = io.BytesIO("通用知识库文档内容".encode("utf-8"))
    resp = await client.post(
        "/api/documents/upload",
        files={"files": ("general_doc.txt", content, "text/plain")},
        data={"knowledgeBase": "general"},
    )
    doc = resp.json()[0]
    assert doc["knowledgeBase"] == "general"

    # Create a project and verify it can see general docs when querying both
    resp = await client.post("/api/projects", json={"name": "通用测试"})
    pid = resp.json()["id"]

    resp = await client.get(f"/api/documents?project_id={pid}")
    project_docs = resp.json()
    # General docs should not appear in project-scoped listing
    assert not any(d["id"] == doc["id"] for d in project_docs)

    # But general docs appear in general listing
    resp = await client.get("/api/documents?knowledge_base=general")
    general_docs = resp.json()
    assert any(d["id"] == doc["id"] for d in general_docs)
