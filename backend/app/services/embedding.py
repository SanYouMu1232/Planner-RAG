"""Embedding provider abstraction.

Defines a fixed interface, a deterministic stub for dev/test, and a factory
that enforces production-safety: stub embeddings are never silently used in
production mode. Model id, dimension, version, and index metadata are recorded
so that future model swaps require re-vectorization.
"""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class EmbeddingConfig:
    """Immutable metadata for a concrete embedding provider instance.

    Changing model_id, dimension, or version across runs means existing vectors
    are incompatible and must be re-generated.
    """

    model_id: str
    dimension: int
    version: str
    provider_name: str
    index_metadata: dict[str, Any] = field(default_factory=dict)


class EmbeddingProvider(ABC):
    """Fixed interface for all embedding backends."""

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Produce a list of float vectors (one per input text)."""
        ...

    @property
    @abstractmethod
    def config(self) -> EmbeddingConfig:
        """Return immutable metadata for this provider instance."""
        ...


# ---------------------------------------------------------------------------
# Deterministic stub for dev / test
# ---------------------------------------------------------------------------

class StubEmbeddingProvider(EmbeddingProvider):
    """Deterministic SHA-256-based embeddings.

    Always produces the same vector for the same text.  Dimension is
    configurable (default 768).  **Must never be used in production mode**
    without an explicit opt-in via ALLOW_STUB_EMBEDDING.
    """

    def __init__(
        self,
        dimension: int = 768,
        model_id: str = "stub-embedding-v1",
        version: str = "1.0.0",
    ) -> None:
        self._config = EmbeddingConfig(
            model_id=model_id,
            dimension=dimension,
            version=version,
            provider_name="stub",
            index_metadata={
                "backend": "deterministic-sha256",
                "normalized": False,
                "description": "Dev/test stub — do not use in production",
            },
        )

    @property
    def config(self) -> EmbeddingConfig:
        return self._config

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [_stub_vector(t, self._config.dimension) for t in texts]


def _stub_vector(text: str, dim: int) -> list[float]:
    """Deterministic float vector from SHA-256 of text."""
    h = hashlib.sha256((text or "").encode("utf-8")).digest()
    # Expand hash bytes into `dim` floats in [-1, 1).
    vec: list[float] = []
    for i in range(dim):
        # Cycle through hash bytes with offset
        b = h[i % len(h)] + h[(i * 7 + 13) % len(h)]
        vec.append(round((b / 255.0) * 2.0 - 1.0, 6))
    return vec


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_embedding_provider: EmbeddingProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    """Return the configured embedding provider (singleton)."""
    global _embedding_provider
    if _embedding_provider is not None:
        return _embedding_provider

    from ..config import (
        ALLOW_STUB_EMBEDDING,
        EMBEDDING_DIMENSION,
        EMBEDDING_MODEL_ID,
        EMBEDDING_PROVIDER,
        EMBEDDING_VERSION,
    )

    provider_name = EMBEDDING_PROVIDER

    if provider_name == "stub":
        if not ALLOW_STUB_EMBEDDING:
            raise RuntimeError(
                "Stub embedding provider is not allowed in production mode. "
                "Set ALLOW_STUB_EMBEDDING=1 only for development/testing, "
                "or configure a real embedding provider via EMBEDDING_PROVIDER."
            )
        _embedding_provider = StubEmbeddingProvider(
            dimension=EMBEDDING_DIMENSION,
            model_id=EMBEDDING_MODEL_ID,
            version=EMBEDDING_VERSION,
        )
    else:
        raise ValueError(
            f"Unknown embedding provider: {provider_name!r}. "
            "Supported providers: stub (dev/test only)."
        )

    return _embedding_provider


def reset_embedding_provider() -> None:
    """Reset singleton (useful in tests)."""
    global _embedding_provider
    _embedding_provider = None
