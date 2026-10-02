"""Shared pytest fixtures for async FastAPI + SQLite testing."""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Ensure backend/ is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["ALLOW_STUB_EMBEDDING"] = "1"
os.environ["INGESTION_MODE"] = "sync"
_test_storage = tempfile.TemporaryDirectory(prefix="planner-tests-")
os.environ["UPLOAD_DIR"] = str(Path(_test_storage.name) / "uploads")
os.environ["UPLOAD_TEMP_DIR"] = str(Path(_test_storage.name) / "tmp")

from app.database import Base, async_session, engine, get_db
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def isolated_storage():
    yield _test_storage.name
    _test_storage.cleanup()


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create tables before each test, drop after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    """Async HTTP client for test requests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session():
    async with async_session() as session:
        yield session
