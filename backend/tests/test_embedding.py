"""Tests for embedding service: provider abstraction, stub safety, determinism."""

import os
import pytest


@pytest.mark.asyncio
async def test_stub_embedding_deterministic():
    """Stub provider produces the same vector for the same text."""
    from app.services.embedding import StubEmbeddingProvider, reset_embedding_provider

    reset_embedding_provider()
    provider = StubEmbeddingProvider(dimension=64)

    v1 = await provider.embed(["相同的文本"])
    v2 = await provider.embed(["相同的文本"])
    assert v1 == v2

    # Different texts produce different vectors
    v3 = await provider.embed(["不同的文本内容"])
    assert v1 != v3


@pytest.mark.asyncio
async def test_embedding_config_metadata():
    """Embedding provider exposes model_id, dimension, version, index_metadata."""
    from app.services.embedding import StubEmbeddingProvider, reset_embedding_provider

    reset_embedding_provider()
    provider = StubEmbeddingProvider(dimension=512, model_id="test-model-v2", version="2.0.0")

    config = provider.config
    assert config.model_id == "test-model-v2"
    assert config.dimension == 512
    assert config.version == "2.0.0"
    assert config.provider_name == "stub"
    assert "backend" in config.index_metadata
    assert config.index_metadata["backend"] == "deterministic-sha256"


@pytest.mark.asyncio
async def test_stub_embedding_blocked_in_production(monkeypatch):
    """Stub embedding provider should raise RuntimeError when ALLOW_STUB_EMBEDDING is off."""
    # Simulate production mode — must patch both env and already-loaded config
    monkeypatch.setenv("ALLOW_STUB_EMBEDDING", "0")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "stub")

    import app.config as cfg
    monkeypatch.setattr(cfg, "ALLOW_STUB_EMBEDDING", False)

    from app.services.embedding import reset_embedding_provider, get_embedding_provider

    reset_embedding_provider()

    with pytest.raises(RuntimeError, match="not allowed in production"):
        get_embedding_provider()

    # Cleanup
    reset_embedding_provider()
    monkeypatch.setattr(cfg, "ALLOW_STUB_EMBEDDING", True)


@pytest.mark.asyncio
async def test_get_embedding_provider_singleton():
    """get_embedding_provider returns the same instance (singleton)."""
    from app.services.embedding import reset_embedding_provider, get_embedding_provider

    reset_embedding_provider()
    p1 = get_embedding_provider()
    p2 = get_embedding_provider()
    assert p1 is p2
    reset_embedding_provider()


@pytest.mark.asyncio
async def test_unknown_embedding_provider_raises(monkeypatch):
    """Unknown embedding provider name should raise ValueError."""
    monkeypatch.setenv("ALLOW_STUB_EMBEDDING", "1")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "nonexistent_provider")

    import app.config as cfg
    monkeypatch.setattr(cfg, "EMBEDDING_PROVIDER", "nonexistent_provider")
    monkeypatch.setattr(cfg, "ALLOW_STUB_EMBEDDING", True)

    from app.services.embedding import reset_embedding_provider, get_embedding_provider

    reset_embedding_provider()

    with pytest.raises(ValueError, match="Unknown embedding provider"):
        get_embedding_provider()

    # Restore
    monkeypatch.setattr(cfg, "EMBEDDING_PROVIDER", "stub")
    reset_embedding_provider()
