"""SQLAlchemy async engine, session factory, and lightweight SQLite upgrades."""
from __future__ import annotations
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from .config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncSession:  # type: ignore[misc]
    async with async_session() as session:
        yield session

async def _ensure_sqlite_columns(conn, table_name: str, columns: dict[str, str]) -> None:
    if not DATABASE_URL.startswith("sqlite"):
        return
    result = await conn.execute(text(f"PRAGMA table_info({table_name})"))
    existing = {row[1] for row in result.fetchall()}
    for column_name, ddl in columns.items():
        if column_name not in existing:
            await conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}"))

async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _ensure_sqlite_columns(conn, "documents", {
            "file_size": "INTEGER DEFAULT 0", "checksum": "VARCHAR(64) DEFAULT ''",
            "source_url": "VARCHAR(1024) DEFAULT ''", "parser_name": "VARCHAR(128) DEFAULT ''",
        })
        await _ensure_sqlite_columns(conn, "document_chunks", {
            "parent_id": "VARCHAR(32)", "chunk_type": "VARCHAR(32) DEFAULT 'child'",
            "heading_path": "VARCHAR(512) DEFAULT ''", "clause_number": "VARCHAR(64)",
            "page_start": "INTEGER", "page_end": "INTEGER", "source_method": "VARCHAR(32) DEFAULT 'native_unknown'",
            "content_hash": "VARCHAR(64) DEFAULT ''", "embedding_json": "TEXT",
            "table_json": "TEXT", "reading_order": "INTEGER DEFAULT 0", "bbox_json": "TEXT",
        })
        await _ensure_sqlite_columns(conn, "provider_configs", {
            "baidu_api_key_encrypted": "VARCHAR(2048) DEFAULT ''",
            "baidu_secret_key_encrypted": "VARCHAR(2048) DEFAULT ''",
            "ocr_risk_confirmed": "INTEGER DEFAULT 0",
            "ocr_provider": "VARCHAR(128) DEFAULT ''",
        })
