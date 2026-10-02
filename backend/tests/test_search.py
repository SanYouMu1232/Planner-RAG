import pytest


@pytest.mark.asyncio
async def test_search_returns_empty_without_real_provider(client):
    resp = await client.post("/api/search", json={
        "keyword": "城市规划",
        "target": "不限",
        "region": "",
        "time_range": "",
    })
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_ingest_candidate_404(client):
    resp = await client.post("/api/search/candidates/nonexistent/ingest", json={
        "knowledgeBase": "project",
    })
    assert resp.status_code == 404
