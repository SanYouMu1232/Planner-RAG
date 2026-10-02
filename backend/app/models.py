"""SQLAlchemy ORM models for 规划智库 backend."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _utcnow() -> datetime:
    return datetime.utcnow()


def _uuid() -> str:
    return uuid.uuid4().hex[:12]


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(128), default="默认用户")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    projects: Mapped[list["Project"]] = relationship(back_populates="owner", lazy="selectin")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="owner", lazy="selectin")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(256))
    project_type: Mapped[str] = mapped_column(String(64), default="其他")
    region: Mapped[str] = mapped_column(String(128), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    owner: Mapped["User | None"] = relationship(back_populates="projects")
    documents: Mapped[list["Document"]] = relationship(
        back_populates="project", lazy="selectin", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="project", lazy="selectin", cascade="all, delete-orphan"
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    project_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("projects.id"), nullable=True)
    file_name: Mapped[str] = mapped_column(String(512))
    file_type: Mapped[str] = mapped_column(String(32), default="other")
    category: Mapped[str] = mapped_column(String(64), default="其他")
    tags: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(256), default="用户上传")
    source_url: Mapped[str] = mapped_column(String(1024), default="")
    publish_date: Mapped[str] = mapped_column(String(32), default="")
    policy_status: Mapped[str] = mapped_column(String(32), default="unknown")
    knowledge_base: Mapped[str] = mapped_column(String(32), default="project")
    parse_status: Mapped[str] = mapped_column(String(32), default="uploading")
    ocr_status: Mapped[str] = mapped_column(String(32), default="not-required")
    is_usable: Mapped[int] = mapped_column(Integer, default=0)  # SQLite bool as int: 0=False, 1=True
    summary_status: Mapped[str] = mapped_column(String(32), default="not-generated")
    summary: Mapped[str] = mapped_column(Text, default="")
    storage_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    checksum: Mapped[str] = mapped_column(String(64), default="")
    parser_name: Mapped[str] = mapped_column(String(128), default="")
    ingest_time: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    project: Mapped["Project | None"] = relationship(back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", lazy="selectin", cascade="all, delete-orphan"
    )
    jobs: Mapped[list["IngestionJob"]] = relationship(
        back_populates="document", lazy="selectin", cascade="all, delete-orphan"
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(String(32), ForeignKey("documents.id"))
    parent_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("document_chunks.id"), nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    chunk_type: Mapped[str] = mapped_column(String(32), default="child")  # "parent" or "child"
    section: Mapped[str] = mapped_column(String(256), default="")
    heading_path: Mapped[str] = mapped_column(String(512), default="")  # hierarchical heading path
    clause_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    page_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)  # legacy, kept for compatibility
    text: Mapped[str] = mapped_column(Text, default="")
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    source_method: Mapped[str] = mapped_column(String(32), default="native_unknown")  # e.g. native_pdf, native_docx, native_txt
    content_hash: Mapped[str] = mapped_column(String(64), default="")  # SHA256 of chunk text
    embedding_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    table_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    reading_order: Mapped[int] = mapped_column(Integer, default=0)
    bbox_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    document: Mapped["Document"] = relationship(back_populates="chunks")
    parent: Mapped["DocumentChunk | None"] = relationship("DocumentChunk", remote_side=[id], back_populates="children")
    children: Mapped[list["DocumentChunk"]] = relationship("DocumentChunk", back_populates="parent", lazy="selectin")
    citations: Mapped[list["Citation"]] = relationship(back_populates="chunk", lazy="selectin")


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(String(32), ForeignKey("documents.id"))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    step: Mapped[str] = mapped_column(String(32), default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    document: Mapped["Document"] = relationship(back_populates="jobs")


class SearchCandidate(Base):
    __tablename__ = "search_candidates"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(512))
    source: Mapped[str] = mapped_column(String(256), default="")
    publish_date: Mapped[str] = mapped_column(String(32), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    url: Mapped[str] = mapped_column(String(1024), default="")
    credibility: Mapped[str] = mapped_column(String(64), default="")
    reason: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(64), default="其他")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(String(32), ForeignKey("projects.id"))
    user_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(512), default="新对话")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    project: Mapped["Project"] = relationship(back_populates="conversations")
    owner: Mapped["User | None"] = relationship(back_populates="conversations")
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="conversation", lazy="selectin", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(String(32), ForeignKey("conversations.id"))
    question: Mapped[str] = mapped_column(Text, default="")
    answer: Mapped[str] = mapped_column(Text, default="")
    knowledge_source: Mapped[str] = mapped_column(String(32), default="both")
    status: Mapped[str] = mapped_column(String(32), default="answering")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    citations: Mapped[list["Citation"]] = relationship(
        back_populates="message", lazy="selectin", cascade="all, delete-orphan"
    )


class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    message_id: Mapped[str] = mapped_column(String(32), ForeignKey("chat_messages.id"))
    document_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("documents.id"), nullable=True)
    chunk_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("document_chunks.id"), nullable=True)
    number: Mapped[int] = mapped_column(Integer, default=1)
    document_name: Mapped[str] = mapped_column(String(512), default="")
    knowledge_base: Mapped[str] = mapped_column(String(32), default="project")
    section: Mapped[str] = mapped_column(String(256), default="")
    quote: Mapped[str] = mapped_column(Text, default="")
    policy_status: Mapped[str] = mapped_column(String(32), default="unknown")

    message: Mapped["ChatMessage"] = relationship(back_populates="citations")
    document: Mapped["Document | None"] = relationship()
    chunk: Mapped["DocumentChunk | None"] = relationship(back_populates="citations")


class UploadSession(Base):
    __tablename__ = "upload_sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    file_name: Mapped[str] = mapped_column(String(512))
    temp_path: Mapped[str] = mapped_column(String(1024))
    total_bytes: Mapped[int] = mapped_column(Integer, default=0)
    received_bytes: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="created")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)


class ProviderConfig(Base):
    __tablename__ = "provider_configs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    provider: Mapped[str] = mapped_column(String(64), default="DeepSeek")
    api_key_encrypted: Mapped[str] = mapped_column(String(2048), default="")
    base_url: Mapped[str] = mapped_column(String(512), default="")
    model_name: Mapped[str] = mapped_column(String(128), default="")
    search_provider: Mapped[str] = mapped_column(String(64), default="")
    search_api_key_encrypted: Mapped[str] = mapped_column(String(2048), default="")
    search_base_url: Mapped[str] = mapped_column(String(512), default="")
    baidu_api_key_encrypted: Mapped[str] = mapped_column(String(2048), default="")
    baidu_secret_key_encrypted: Mapped[str] = mapped_column(String(2048), default="")
    ocr_risk_confirmed: Mapped[int] = mapped_column(Integer, default=0)
    ocr_provider: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)
