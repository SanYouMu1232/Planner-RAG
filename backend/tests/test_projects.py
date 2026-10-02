import pytest


@pytest.mark.asyncio
async def test_create_project(client):
    resp = await client.post("/api/projects", json={
        "name": "测试项目",
        "projectType": "总体规划",
        "region": "测试市",
        "description": "测试描述",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "测试项目"
    assert data["projectType"] == "总体规划"
    assert data["docCount"] == 0
    assert len(data["id"]) > 0


@pytest.mark.asyncio
async def test_list_projects_empty(client):
    resp = await client.get("/api/projects")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_list_projects_after_create(client):
    await client.post("/api/projects", json={"name": "P1"})
    await client.post("/api/projects", json={"name": "P2"})
    resp = await client.get("/api/projects")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_project(client):
    resp = await client.post("/api/projects", json={"name": "获取测试"})
    pid = resp.json()["id"]
    resp = await client.get(f"/api/projects/{pid}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "获取测试"


@pytest.mark.asyncio
async def test_get_project_404(client):
    resp = await client.get("/api/projects/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_project(client):
    resp = await client.post("/api/projects", json={"name": "更新前"})
    pid = resp.json()["id"]
    resp = await client.patch(f"/api/projects/{pid}", json={"name": "已更新"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "已更新"


@pytest.mark.asyncio
async def test_delete_project(client):
    resp = await client.post("/api/projects", json={"name": "删除测试"})
    pid = resp.json()["id"]
    resp = await client.delete(f"/api/projects/{pid}")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    resp = await client.get(f"/api/projects/{pid}")
    assert resp.status_code == 404
