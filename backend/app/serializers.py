"""Small response builders used by routers."""

from __future__ import annotations

from datetime import datetime
from . import models
from .schemas import (
    CandidateOut,
    CitationOut,
    ChunkOut,
    ConversationOut,
    ChatTurnOut,
    DocumentOut,
    IngestionJobOut,
    ProjectOut,
)


def dt_str(dt: datetime | None) -> str:
    return dt.isoformat() if dt else datetime.utcnow().isoformat()


def date_str(dt: datetime | None) -> str:
    return dt.strftime("%Y-%m-%d") if dt else datetime.utcnow().strftime("%Y-%m-%d")


def project_out(p: models.Project) -> ProjectOut:
    last_qa = "暂无"
    if p.conversations:
        latest = max((c.updated_at for c in p.conversations if c.updated_at), default=None)
        if latest:
            last_qa = latest.isoformat()
    return ProjectOut(
        id=p.id,
        name=p.name,
        project_type=p.project_type,
        region=p.region,
        description=p.description,
        doc_count=len(p.documents or []),
        last_used=dt_str(p.updated_at),
        last_qa_time=last_qa,
        created_at=dt_str(p.created_at),
        updated_at=dt_str(p.updated_at),
    )


def document_out(doc: models.Document) -> DocumentOut:
    return DocumentOut(
        id=doc.id,
        file_name=doc.file_name,
        file_type=doc.file_type,
        category=doc.category,
        tags=[t.strip() for t in (doc.tags or "").split(",") if t.strip()],
        source=doc.source,
        source_url=doc.source_url,
        publish_date=doc.publish_date,
        policy_status=doc.policy_status,
        ingest_time=date_str(doc.ingest_time),
        parse_status=doc.parse_status,
        ocr_status=doc.ocr_status,
        is_usable=bool(doc.is_usable),
        summary_status=doc.summary_status,
        knowledge_base=doc.knowledge_base,
        project_id=doc.project_id,
        summary=doc.summary,
        chunk_count=len(doc.chunks or []),
        table_count=sum(1 for c in (doc.chunks or []) if c.chunk_type == "table"),
        parser_name=doc.parser_name or "",
    )


def chunk_out(c: models.DocumentChunk) -> ChunkOut:
    return ChunkOut(
        id=c.id,
        parent_id=c.parent_id,
        chunk_index=c.chunk_index,
        chunk_type=c.chunk_type,
        section=c.section,
        heading_path=c.heading_path,
        clause_number=c.clause_number,
        page_start=c.page_start,
        page_end=c.page_end,
        page_number=c.page_number,
        text=c.text,
        token_count=c.token_count,
        source_method=c.source_method,
        content_hash=c.content_hash,
        table_json=c.table_json,
        reading_order=c.reading_order or 0,
        bbox_json=c.bbox_json,
    )


def job_out(job: models.IngestionJob) -> IngestionJobOut:
    return IngestionJobOut(
        id=job.id,
        document_id=job.document_id,
        status=job.status,
        progress=job.progress,
        step=job.step,
        error_message=job.error_message,
        created_at=dt_str(job.created_at),
        updated_at=dt_str(job.updated_at),
    )


def candidate_out(c: models.SearchCandidate) -> CandidateOut:
    return CandidateOut(
        id=c.id,
        title=c.title,
        source=c.source,
        publish_date=c.publish_date,
        summary=c.summary,
        url=c.url,
        credibility=c.credibility,
        reason=c.reason,
        category=c.category,
    )


def citation_out(c: models.Citation) -> CitationOut:
    return CitationOut(
        id=c.id,
        number=c.number,
        document_id=c.document_id,
        chunk_id=c.chunk_id,
        document_name=c.document_name,
        knowledge_base=c.knowledge_base,
        section=c.section,
        quote=c.quote,
        policy_status=c.policy_status,
    )


def conversation_out(c: models.Conversation) -> ConversationOut:
    turns = [
        ChatTurnOut(
            id=m.id,
            question=m.question,
            answer=m.answer or "",
            status=m.status,
            citations=[citation_out(citation) for citation in (m.citations or [])],
            created_at=dt_str(m.created_at),
        )
        for m in (c.messages or [])
    ]
    turns.sort(key=lambda t: t.created_at or t.id)
    return ConversationOut(id=c.id, title=c.title, turns=turns, updated_at=dt_str(c.updated_at))
