import pytest


@pytest.mark.asyncio
async def test_list_configs_empty(client):
    resp = await client.get("/api/provider-configs")
    assert resp.status_code == 200
    configs = resp.json()
    assert isinstance(configs, list)


@pytest.mark.asyncio
async def test_save_and_list_config(client):
    resp = await client.post("/api/provider-configs", json={
        "provider": "DeepSeek",
        "api_key": "sk-test-key-12345678",
        "base_url": "https://api.deepseek.com",
        "model_name": "deepseek-chat",
        "search_provider": "博查 AI Search",
        "search_api_key": "search-key-abc",
    })
    assert resp.status_code == 201
    config = resp.json()
    assert config["provider"] == "DeepSeek"
    assert "sk-test" not in config["apiKeyMasked"]
    assert config["apiKeyMasked"] != ""
    assert "search-key" not in config["searchApiKeyMasked"]

    resp = await client.get("/api/provider-configs")
    assert resp.status_code == 200
    configs = resp.json()
    assert len(configs) == 1
    assert "sk-test" not in configs[0]["apiKeyMasked"]


@pytest.mark.asyncio
async def test_test_config_no_key(client):
    resp = await client.post("/api/provider-configs/test", json={
        "provider": "DeepSeek",
        "api_key": "",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert "API Key" in data["message"]


@pytest.mark.asyncio
async def test_masked_key_never_exposes_full_key(client):
    long_key = "sk-this-is-a-very-long-secret-key-that-should-be-masked"
    resp = await client.post("/api/provider-configs", json={
        "provider": "OpenAI",
        "api_key": long_key,
    })
    assert resp.status_code == 201
    config = resp.json()
    masked = config["apiKeyMasked"]
    assert long_key not in masked
    assert "****" in masked
