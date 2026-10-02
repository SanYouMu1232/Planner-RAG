"""Pydantic schemas. API JSON uses frontend-friendly camelCase aliases."""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


def to_camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(p[:1].upper() + p[1:] for p in parts[1:])


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        use_enum_values=True,
    )


class KnowledgeBaseType(str, Enum):
    project = "project"
    general = "general"


class PolicyStatus(str, Enum):
    active = "active"
    repealed = "repealed"
    draft = "draft"
    unknown = "unknown"


class FileType(str, Enum):
    pdf = "pdf"
    word = "word"
    image = "image"
    scan = "scan"
    web = "web"
    txt = "txt"
    ppt = "ppt"
    excel = "excel"
    other = "other"


class ParseStatus(str, Enum):
    uploading = "uploading"
    parsing = "parsing"
    summarizing = "summarizing"
    vectorizing = "vectorizing"
    ready = "ready"
    failed = "failed"


class OcrStatus(str, Enum):
    not_required = "not-required"
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class SummaryStatus(str, Enum):
    generated = "generated"
    not_generated = "not-generated"
    failed = "failed"


class KnowledgeSource(str, Enum):
    project = "project"
    general = "general"
    both = "both"


class ProjectType(str, Enum):
    master = "总体规划"
    detail = "详细规划"
    special = "专项规划"
    urban_design = "城市设计"
    renewal = "城市更新"
    other = "其他"


class HealthResponse(CamelModel):
    ok: bool = True
    message: str = "规划智库后端运行中"


class ErrorResponse(CamelModel):
    ok: bool = False
    message: str
    code: str = "ERROR"


class ProjectCreate(CamelModel):
    name: str
    project_type: ProjectType = ProjectType.other
    region: str = ""
    description: str = ""


class ProjectUpdate(CamelModel):
    name: str | None = None
    project_type: ProjectType | None = None
    region: str | None = None
    description: str | None = None


class ProjectOut(CamelModel):
    id: str
    name: str
    project_type: str = "其他"
    region: str = ""
    description: str = ""
    doc_count: int = 0
    last_used: str = ""
    last_qa_time: str = ""
    created_at: str = ""
    updated_at: str = ""


class DocumentOut(CamelModel):
    id: str
    file_name: str
    file_type: str = "other"
    category: str = "其他"
    tags: list[str] = Field(default_factory=list)
    source: str = ""
    source_url: str = ""
    publish_date: str = ""
    policy_status: str = "unknown"
    ingest_time: str = ""
    parse_status: str = "uploading"
    ocr_status: str = "not-required"
    is_usable: bool = False
    summary_status: str = "not-generated"
    knowledge_base: str = "project"
    project_id: str | None = None
    summary: str = ""
    chunk_count: int = 0
    table_count: int = 0
    parser_name: str = ""


class DocumentUpdate(CamelModel):
    file_name: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    policy_status: PolicyStatus | None = None
    publish_date: str | None = None
    source: str | None = None
    summary: str | None = None


class ChunkOut(CamelModel):
    id: str
    parent_id: str | None = None
    chunk_index: int = 0
    chunk_type: str = "child"
    section: str = ""
    heading_path: str = ""
    clause_number: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    page_number: int | None = None
    text: str = ""
    token_count: int = 0
    source_method: str = "native_unknown"
    content_hash: str = ""
    table_json: str | None = None
    reading_order: int = 0
    bbox_json: str | None = None


class IngestionJobOut(CamelModel):
    id: str
    document_id: str
    status: str
    progress: int = 0
    step: str = "pending"
    error_message: str | None = None
    created_at: str = ""
    updated_at: str = ""


class SearchRequest(CamelModel):
    keyword: str
    target: str = "不限"
    region: str = ""
    time_range: str = ""


class CandidateOut(CamelModel):
    id: str
    title: str
    source: str = ""
    publish_date: str = ""
    summary: str = ""
    url: str = ""
    credibility: str = ""
    reason: str = ""
    category: str = ""


class CandidateIngestRequest(CamelModel):
    knowledge_base: KnowledgeBaseType = KnowledgeBaseType.project
    project_id: str | None = None
    generate_summary: bool = False


class ConversationCreate(CamelModel):
    title: str = "新对话"


class ChatTurnOut(CamelModel):
    id: str
    question: str
    answer: str = ""
    status: str
    citations: list["CitationOut"] = Field(default_factory=list)
    created_at: str = ""


class ConversationOut(CamelModel):
    id: str
    title: str
    turns: list[ChatTurnOut] = Field(default_factory=list)
    updated_at: str = ""


class MessageCreate(CamelModel):
    question: str
    knowledge_source: KnowledgeSource = KnowledgeSource.both


class CitationOut(CamelModel):
    id: str
    number: int
    document_id: str | None = None
    chunk_id: str | None = None
    document_name: str = ""
    knowledge_base: str = "project"
    section: str = ""
    quote: str = ""
    policy_status: str = "unknown"


class MessageOut(CamelModel):
    id: str
    question: str
    answer: str = ""
    status: str = "answering"
    citations: list[CitationOut] = Field(default_factory=list)
    created_at: str = ""


class DraftGenerateRequest(CamelModel):
    prompt: str
    knowledge_source: KnowledgeSource = KnowledgeSource.both


class DraftOut(CamelModel):
    id: str
    content: str = ""
    citations: list[CitationOut] = Field(default_factory=list)


class ProviderConfigOut(CamelModel):
    id: str
    provider: str = "DeepSeek"
    api_key_masked: str = ""
    base_url: str = ""
    model_name: str = ""
    search_provider: str = ""
    search_api_key_masked: str = ""
    search_base_url: str = ""
    baidu_api_key_masked: str = ""
    baidu_secret_key_masked: str = ""
    ocr_risk_confirmed: bool = False
    ocr_provider: str = ""


class ProviderConfigSave(CamelModel):
    provider: str = "DeepSeek"
    api_key: str = ""
    base_url: str = ""
    model_name: str = ""
    search_provider: str = ""
    search_api_key: str = ""
    search_base_url: str = ""
    baidu_api_key: str = ""
    baidu_secret_key: str = ""
    ocr_risk_confirmed: bool = False
    ocr_provider: str = "文档解析（PaddleOCR-VL）"


class ProviderConfigTest(CamelModel):
    provider: str = "DeepSeek"
    api_key: str = ""
    base_url: str = ""
    model_name: str = ""
    search_provider: str = ""
    search_api_key: str = ""
    search_base_url: str = ""


class ProviderConfigTestResponse(CamelModel):
    ok: bool
    message: str
    search_tested: bool = False


class SearchConfigTest(CamelModel):
    search_provider: str
    search_api_key: str = ""
    search_base_url: str = ""


class OCRConfigTest(CamelModel):
    baidu_api_key: str
    baidu_secret_key: str
    risk_confirmed: bool


class UploadInitRequest(CamelModel):
    file_name: str
    total_bytes: int = Field(gt=0)


class UploadCompleteRequest(CamelModel):
    knowledge_base: KnowledgeBaseType = KnowledgeBaseType.project
    project_id: str | None = None
    generate_summary: bool = False
    category: str = ""
    tags: str = "甲方资料,待核验"
    use_cloud_ocr: bool = False


class UploadSessionOut(CamelModel):
    id: str
    file_name: str
    total_bytes: int
    received_bytes: int
    status: str


class EmbeddingConfigOut(CamelModel):
    model_id: str = "stub-embedding-v1"
    dimension: int = 768
    version: str = "1.0.0"
    provider: str = "stub"


# ---------------------------------------------------------------------------
# SSE streaming event schemas
# ---------------------------------------------------------------------------
class SSEBase(CamelModel):
    type: str
    data: dict = Field(default_factory=dict)


class SSEError(CamelModel):
    code: str = "STREAM_ERROR"
    message: str = ""
