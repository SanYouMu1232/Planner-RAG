"""Database CRUD helpers."""

from __future__ import annotations

import base64
import os
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from . import models


def _now() -> str:
    return datetime.utcnow().isoformat()


def _dt_str(dt: datetime | None) -> str:
    return dt.isoformat() if dt else _now()


async def get_or_create_default_user(db: AsyncSession) -> models.User:
    result = await db.execute(select(models.User).limit(1))
    user = result.scalar_one_or_none()
    if user is None:
        user = models.User(name="默认用户")
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


async def list_projects(db: AsyncSession) -> list[models.Project]:
    result = await db.execute(
        select(models.Project).options(selectinload(models.Project.documents), selectinload(models.Project.conversations)).order_by(models.Project.updated_at.desc())
    )
    return list(result.scalars().all())


async def get_project(db: AsyncSession, project_id: str) -> models.Project | None:
    result = await db.execute(
        select(models.Project)
        .where(models.Project.id == project_id)
        .options(selectinload(models.Project.documents), selectinload(models.Project.conversations))
    )
    return result.scalar_one_or_none()


async def create_project(db: AsyncSession, data: dict) -> models.Project:
    user = await get_or_create_default_user(db)
    project = models.Project(user_id=user.id, **data)
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def update_project(db: AsyncSession, project_id: str, data: dict) -> models.Project | None:
    project = await get_project(db, project_id)
    if project is None:
        return None
    for key, value in data.items():
        if value is not None:
            setattr(project, key, value)
    await db.commit()
    await db.refresh(project)
    return project


async def delete_project(db: AsyncSession, project_id: str) -> bool:
    project = await get_project(db, project_id)
    if project is None:
        return False
    await db.delete(project)
    await db.commit()
    return True


async def list_documents(
    db: AsyncSession,
    knowledge_base: str | None = None,
    project_id: str | None = None,
    keyword: str | None = None,
    category: str | None = None,
    tag: str | None = None,
    status: str | None = None,
) -> list[models.Document]:
    q = select(models.Document).options(selectinload(models.Document.chunks))
    if knowledge_base:
        q = q.where(models.Document.knowledge_base == knowledge_base)
    if project_id:
        q = q.where(models.Document.project_id == project_id)
    if category:
        q = q.where(models.Document.category == category)
    if status:
        q = q.where(models.Document.parse_status == status)
    q = q.order_by(models.Document.ingest_time.desc())
    docs = list((await db.execute(q)).scalars().all())

    if keyword:
        kw = keyword.lower()
        docs = [d for d in docs if kw in d.file_name.lower() or kw in d.category.lower() or kw in (d.tags or "").lower()]
    if tag:
        docs = [d for d in docs if tag in (d.tags or "")]
    return docs


async def get_document(db: AsyncSession, doc_id: str) -> models.Document | None:
    result = await db.execute(
        select(models.Document).where(models.Document.id == doc_id).options(selectinload(models.Document.chunks), selectinload(models.Document.jobs))
    )
    return result.scalar_one_or_none()


async def create_document(db: AsyncSession, data: dict) -> models.Document:
    doc = models.Document(**data)
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def update_document(db: AsyncSession, doc_id: str, data: dict) -> models.Document | None:
    doc = await get_document(db, doc_id)
    if doc is None:
        return None
    for key, value in data.items():
        if value is not None:
            setattr(doc, key, value)
    await db.commit()
    await db.refresh(doc)
    return doc


async def delete_document(db: AsyncSession, doc_id: str) -> bool:
    doc = await get_document(db, doc_id)
    if doc is None:
        return False
    storage_path = doc.storage_path
    await db.delete(doc)
    await db.commit()
    if storage_path and os.path.exists(storage_path):
        try:
            os.remove(storage_path)
        except OSError:
            pass
    return True


async def list_chunks(db: AsyncSession, doc_id: str) -> list[models.DocumentChunk]:
    result = await db.execute(
        select(models.DocumentChunk).where(models.DocumentChunk.document_id == doc_id).order_by(models.DocumentChunk.chunk_index.asc())
    )
    return list(result.scalars().all())


async def get_ingestion_job(db: AsyncSession, job_id: str) -> models.IngestionJob | None:
    return await db.get(models.IngestionJob, job_id)


async def get_latest_document_job(db: AsyncSession, document_id: str) -> models.IngestionJob | None:
    result = await db.execute(
        select(models.IngestionJob).where(models.IngestionJob.document_id == document_id).order_by(models.IngestionJob.created_at.desc()).limit(1)
    )
    return result.scalar_one_or_none()


async def create_ingestion_job(db: AsyncSession, document_id: str, status: str = "pending", progress: int = 0, step: str = "pending") -> models.IngestionJob:
    job = models.IngestionJob(document_id=document_id, status=status, progress=progress, step=step)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def list_search_candidates(db: AsyncSession) -> list[models.SearchCandidate]:
    result = await db.execute(select(models.SearchCandidate).order_by(models.SearchCandidate.created_at.desc()))
    return list(result.scalars().all())


async def get_search_candidate(db: AsyncSession, candidate_id: str) -> models.SearchCandidate | None:
    return await db.get(models.SearchCandidate, candidate_id)


async def create_search_candidates(db: AsyncSession, candidates: list[dict]) -> list[models.SearchCandidate]:
    objs = [models.SearchCandidate(**{k: v for k, v in c.items() if k in models.SearchCandidate.__table__.columns.keys()}) for c in candidates]
    db.add_all(objs)
    await db.commit()
    for obj in objs:
        await db.refresh(obj)
    return objs


async def list_conversations(db: AsyncSession, project_id: str) -> list[models.Conversation]:
    result = await db.execute(
        select(models.Conversation)
        .where(models.Conversation.project_id == project_id)
        .options(selectinload(models.Conversation.messages).selectinload(models.ChatMessage.citations))
        .order_by(models.Conversation.updated_at.desc())
    )
    return list(result.scalars().all())


async def get_conversation(db: AsyncSession, conv_id: str) -> models.Conversation | None:
    result = await db.execute(
        select(models.Conversation).where(models.Conversation.id == conv_id).options(selectinload(models.Conversation.messages).selectinload(models.ChatMessage.citations))
    )
    return result.scalar_one_or_none()


async def create_conversation(db: AsyncSession, project_id: str, title: str = "新对话") -> models.Conversation:
    user = await get_or_create_default_user(db)
    conv = models.Conversation(project_id=project_id, user_id=user.id, title=title)
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


async def delete_conversation(db: AsyncSession, conv_id: str) -> bool:
    conv = await get_conversation(db, conv_id)
    if conv is None:
        return False
    await db.delete(conv)
    await db.commit()
    return True


async def create_message(db: AsyncSession, conv_id: str, question: str, knowledge_source: str = "both") -> models.ChatMessage:
    msg = models.ChatMessage(conversation_id=conv_id, question=question, knowledge_source=knowledge_source, status="answering")
    db.add(msg)
    # Touch conversation so project cards can show recent activity.
    conv = await get_conversation(db, conv_id)
    if conv:
        conv.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(msg)
    return msg


async def update_message_answer(db: AsyncSession, msg_id: str, answer: str, status: str = "done") -> models.ChatMessage | None:
    msg = await db.get(models.ChatMessage, msg_id)
    if msg is None:
        return None
    msg.answer = answer
    msg.status = status
    await db.commit()
    await db.refresh(msg)
    return msg


async def create_citations(db: AsyncSession, message_id: str, citations_data: list[dict]) -> list[models.Citation]:
    objs = [models.Citation(message_id=message_id, **c) for c in citations_data]
    db.add_all(objs)
    await db.commit()
    for obj in objs:
        await db.refresh(obj)
    return objs


def _mask_key(key: str) -> str:
    if not key:
        return ""
    return "****" if len(key) <= 8 else key[:4] + "****" + key[-4:]


def _secret_bytes() -> bytes:
    from .config import PROVIDER_CONFIG_SECRET
    return (PROVIDER_CONFIG_SECRET or "planner-dev-secret-change-me").encode("utf-8")


def _xor_bytes(raw: bytes, secret: bytes) -> bytes:
    return bytes(value ^ secret[index % len(secret)] for index, value in enumerate(raw))


def _encrypt_key(key: str) -> str:
    if not key:
        return ""
    encrypted = _xor_bytes(key.encode("utf-8"), _secret_bytes())
    return "xor:v1:" + base64.urlsafe_b64encode(encrypted).decode("ascii")


def _decrypt_key(encrypted: str) -> str:
    if not encrypted:
        return ""
    try:
        if encrypted.startswith("xor:v1:"):
            raw = base64.urlsafe_b64decode(encrypted.removeprefix("xor:v1:").encode("ascii"))
            return _xor_bytes(raw, _secret_bytes()).decode("utf-8")
        return base64.b64decode(encrypted.encode()).decode()
    except Exception:
        return ""


def _config_out(c: models.ProviderConfig) -> dict:
    return {
        "id": c.id,
        "provider": c.provider,
        "api_key_masked": _mask_key(_decrypt_key(c.api_key_encrypted)),
        "base_url": c.base_url,
        "model_name": c.model_name,
        "search_provider": c.search_provider,
        "search_api_key_masked": _mask_key(_decrypt_key(c.search_api_key_encrypted)),
        "search_base_url": c.search_base_url,
        "baidu_api_key_masked": _mask_key(_decrypt_key(c.baidu_api_key_encrypted)),
        "baidu_secret_key_masked": _mask_key(_decrypt_key(c.baidu_secret_key_encrypted)),
        "ocr_risk_confirmed": bool(c.ocr_risk_confirmed),
        "ocr_provider": c.ocr_provider,
    }


async def list_provider_configs(db: AsyncSession) -> list[dict]:
    result = await db.execute(select(models.ProviderConfig).order_by(models.ProviderConfig.updated_at.desc()))
    return [_config_out(c) for c in result.scalars().all()]


async def save_provider_config(db: AsyncSession, data: dict) -> dict:
    # Cloud OCR credentials are never persisted unless the user has explicitly acknowledged cloud transfer risk.
    has_ocr_credentials = bool(data.get("baidu_api_key") or data.get("baidu_secret_key"))
    if has_ocr_credentials and not data.get("ocr_risk_confirmed"):
        raise ValueError("保存百度云 OCR 前必须确认：文件会发送至百度智能云进行云端解析。")
    config = models.ProviderConfig(
        provider=data.get("provider", "DeepSeek"),
        api_key_encrypted=_encrypt_key(data.get("api_key", "")),
        base_url=data.get("base_url", ""),
        model_name=data.get("model_name", ""),
        search_provider=data.get("search_provider", ""),
        search_api_key_encrypted=_encrypt_key(data.get("search_api_key", "")),
        search_base_url=data.get("search_base_url", ""),
        baidu_api_key_encrypted=_encrypt_key(data.get("baidu_api_key", "")),
        baidu_secret_key_encrypted=_encrypt_key(data.get("baidu_secret_key", "")),
        ocr_risk_confirmed=1 if data.get("ocr_risk_confirmed") else 0,
        ocr_provider=data.get("ocr_provider", "文档解析（PaddleOCR-VL）") if has_ocr_credentials else "",
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return _config_out(config)


async def get_latest_provider_config(db: AsyncSession) -> models.ProviderConfig | None:
    result = await db.execute(select(models.ProviderConfig).order_by(models.ProviderConfig.updated_at.desc()).limit(1))
    return result.scalar_one_or_none()


def provider_config_runtime(c: models.ProviderConfig | None) -> dict:
    if c is None:
        return {}
    return {
        "provider": c.provider,
        "api_key": _decrypt_key(c.api_key_encrypted),
        "base_url": c.base_url,
        "model_name": c.model_name,
        "search_provider": c.search_provider,
        "search_api_key": _decrypt_key(c.search_api_key_encrypted),
        "search_base_url": c.search_base_url,
        "baidu_api_key": _decrypt_key(c.baidu_api_key_encrypted),
        "baidu_secret_key": _decrypt_key(c.baidu_secret_key_encrypted),
        "ocr_risk_confirmed": bool(c.ocr_risk_confirmed),
        "ocr_provider": c.ocr_provider,
    }


async def get_latest_provider_runtime_config(db: AsyncSession) -> dict:
    config = await get_latest_provider_config(db)
    return provider_config_runtime(config)


async def create_upload_session(db: AsyncSession, file_name: str, temp_path: str, total_bytes: int) -> models.UploadSession:
    item = models.UploadSession(file_name=file_name, temp_path=temp_path, total_bytes=total_bytes, status="created")
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def get_upload_session(db: AsyncSession, upload_id: str) -> models.UploadSession | None:
    return await db.get(models.UploadSession, upload_id)


async def update_upload_session(db: AsyncSession, upload_id: str, **values) -> models.UploadSession | None:
    item = await db.get(models.UploadSession, upload_id)
    if item is None:
        return None
    for key, value in values.items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


async def list_recent_messages(db: AsyncSession, conv_id: str, limit: int = 10) -> list[models.ChatMessage]:
    result = await db.execute(
        select(models.ChatMessage).where(models.ChatMessage.conversation_id == conv_id)
        .order_by(models.ChatMessage.created_at.desc()).limit(limit)
    )
    return list(reversed(list(result.scalars().all())))
