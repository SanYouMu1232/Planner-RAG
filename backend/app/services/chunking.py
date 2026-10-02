"""Structure-aware text chunking for planning documents.

Produces parent-child chunk structure:
- Parent chunks represent document sections/headings.
- Child chunks contain the actual text within each parent.
- Each child retains pageStart/pageEnd/headingPath/chunkType/sourceMethod/contentHash.

MVP strategy: keep headings / clause numbers / page numbers, then window long
sections by character count with overlap. This is deliberately deterministic so
citations can be checked by humans.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .text_extractor import PageContent

HEADING_RE = re.compile(
    r"^(第[一二三四五六七八九十百千万0-9]+[章节条款编]|"
    r"[一二三四五六七八九十]+[、．.]|"
    r"\d+(?:\.\d+)*[、.\s]|"
    r"[（(][一二三四五六七八九十0-9]+[）)])"
)
CLAUSE_RE = re.compile(r"^(第[一二三四五六七八九十百千万0-9]+条|\d+(?:\.\d+){1,3})")


@dataclass(slots=True)
class Chunk:
    chunk_index: int
    text: str
    section: str = ""
    heading_path: str = ""
    clause_number: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    page_number: int | None = None  # legacy single-page hint
    token_count: int = 0
    chunk_type: str = "child"  # "parent" or "child"
    source_method: str = "native_unknown"
    content_hash: str = ""
    parent_index: int | None = None  # index of parent chunk in the flat list; None for parent chunks
    table_json: str | None = None
    reading_order: int = 0
    bbox_json: str | None = None


@dataclass(slots=True)
class ChunkResult:
    chunks: list[Chunk]  # flat list, parents first, children follow


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _rough_tokens(text: str) -> int:
    # Chinese planning docs: char count / 1.7 is a usable cheap estimate.
    return max(1, int(len(text) / 1.7))


def _text_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]


def _split_pages(text: str) -> list[tuple[int | None, str]]:
    if "\f" not in text:
        return [(None, text)]
    return [(i + 1, page) for i, page in enumerate(text.split("\f"))]


def _paragraphs(text: str) -> list[str]:
    paragraphs: list[str] = []
    for block in re.split(r"\n\s*\n|\n", text):
        block = block.strip()
        if block:
            paragraphs.append(block)
    return paragraphs


def _split_boundary(text: str, start: int, hard_end: int, max_chars: int) -> int:
    """Pick a Chinese-friendly chunk boundary without dropping characters.

    Search result pages often contain very long policy paragraphs. Splitting at
    the hard character limit can cut fixed phrases such as “报党中央同意后” in
    half, which then looks like text is missing in the original preview. Prefer
    sentence and clause punctuation before falling back to the hard limit.
    """
    if hard_end >= len(text):
        return len(text)
    # Prefer sentence boundaries; accept a slightly earlier split to keep legal
    # clauses intact instead of chopping names or procedure phrases.
    for marks, floor in (("。！？；\n", 0.35), ("，、：", 0.55), (" )）]】", 0.65)):
        best = -1
        for mark in marks:
            best = max(best, text.rfind(mark, start, hard_end))
        if best >= start + int(max_chars * floor):
            return best + 1
    return hard_end

def _slice_long(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    start = 0
    safe_overlap = max(0, min(overlap_chars, max_chars // 2))
    while start < len(text):
        hard_end = min(len(text), start + max_chars)
        end = _split_boundary(text, start, hard_end, max_chars)
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        next_start = max(0, end - safe_overlap) if safe_overlap else end
        # Ensure progress even if overlap/whitespace creates an awkward boundary.
        if next_start <= start:
            next_start = end
        start = next_start
    return chunks


def chunk_text(
    text: str,
    max_chars: int = 900,
    overlap_chars: int = 150,
    source_method: str = "native_unknown",
    pages: list[PageContent] | None = None,
) -> ChunkResult:
    """Split text into parent-child chunk structure.

    - Parent chunks are heading/section containers.
    - Child chunks are the actual splittable text segments.
    - pageStart/pageEnd derived from page-content metadata when available.

    Recommended defaults for PRD V1.1: 700-1000 Chinese chars with 100-200 chars
    overlap. It is long enough for planning clauses and short enough for precise
    citations.
    """
    text = normalize_text(text)
    chunks: list[Chunk] = []
    chunk_idx = 0

    if not text:
        return ChunkResult(chunks=chunks)

    # Build page number lookup from structured pages if available
    page_ranges: dict[int, int | None] = {}  # paragraph_index -> page_number
    if pages:
        para_idx = 0
        for pg in pages:
            for _ in _paragraphs(pg.text):
                page_ranges[para_idx] = pg.page_number
                para_idx += 1

    current_section = "正文"
    heading_path = "正文"
    current_parent_idx: int | None = None

    for page_num, page_text in _split_pages(text):
        buffer: list[str] = []
        buffer_section = current_section
        buffer_heading_path = heading_path
        buffer_clause: str | None = None
        buffer_page_start: int | None = page_num

        def flush() -> None:
            nonlocal buffer, buffer_section, buffer_heading_path, buffer_clause, buffer_page_start, chunk_idx, current_parent_idx
            if not buffer:
                return
            joined = "\n".join(buffer).strip()
            for part in _slice_long(joined, max_chars=max_chars, overlap_chars=overlap_chars):
                chunks.append(
                    Chunk(
                        chunk_index=chunk_idx,
                        text=part,
                        section=buffer_section,
                        heading_path=buffer_heading_path,
                        clause_number=buffer_clause,
                        page_start=buffer_page_start,
                        page_end=buffer_page_start,  # refined below
                        page_number=buffer_page_start,
                        token_count=_rough_tokens(part),
                        chunk_type="child",
                        source_method=source_method,
                        content_hash=_text_hash(part),
                        parent_index=current_parent_idx,
                    )
                )
                chunk_idx += 1
            buffer = []
            buffer_clause = None

        for para in _paragraphs(page_text):
            heading = HEADING_RE.match(para)
            clause = CLAUSE_RE.match(para)

            # Heading: start a new parent section
            if heading and len(para) <= 80 and not clause:
                flush()
                current_section = para[:120]
                # Build heading path
                heading_parts = [p for p in heading_path.split(" > ") if p and p != "正文"]
                heading_parts.append(para[:120])
                heading_path = " > ".join(heading_parts) if heading_parts else para[:120]

                # Create parent chunk
                chunks.append(
                    Chunk(
                        chunk_index=chunk_idx,
                        text=para[:240],
                        section=para[:120],
                        heading_path=heading_path,
                        clause_number=None,
                        page_start=page_num,
                        page_end=page_num,
                        page_number=page_num,
                        token_count=_rough_tokens(para[:240]),
                        chunk_type="parent",
                        source_method=source_method,
                        content_hash=_text_hash(para[:240]),
                        parent_index=None,
                    )
                )
                current_parent_idx = chunk_idx
                chunk_idx += 1
                buffer_section = current_section
                buffer_heading_path = heading_path
                continue

            if clause:
                if sum(len(x) for x in buffer) > max_chars * 0.55:
                    flush()
                buffer_clause = clause.group(1)

            if sum(len(x) for x in buffer) + len(para) > max_chars:
                flush()
                buffer_section = current_section
                buffer_heading_path = heading_path
                if clause:
                    buffer_clause = clause.group(1)
            buffer.append(para)

        flush()

    # When no parent chunks were created (e.g. plain text without headings),
    # create at least one parent for the children.
    parent_count = sum(1 for c in chunks if c.chunk_type == "parent")
    if parent_count == 0 and len(chunks) > 0:
        # Insert a root parent at index 0
        root_parent = Chunk(
            chunk_index=0,
            text=text[:240],
            section="正文",
            heading_path="正文",
            page_start=chunks[0].page_start if chunks else None,
            page_end=chunks[-1].page_end if chunks else None,
            page_number=chunks[0].page_start if chunks else None,
            token_count=_rough_tokens(text[:240]),
            chunk_type="parent",
            source_method=source_method,
            content_hash=_text_hash(text[:240]),
            parent_index=None,
        )
        # Shift all existing chunk indices up by 1
        for c in chunks:
            c.chunk_index += 1
            if c.parent_index is not None:
                c.parent_index = 0  # all children now point to new parent
        chunks.insert(0, root_parent)
        chunk_idx = len(chunks)

    return ChunkResult(chunks=chunks)


# ---------------------------------------------------------------------------
# Legacy compatibility wrapper
# ---------------------------------------------------------------------------
def chunk_text_flat(
    text: str,
    max_chars: int = 900,
    overlap_chars: int = 150,
    source_method: str = "native_unknown",
    pages: list[PageContent] | None = None,
) -> list[Chunk]:
    """Return a flat list of child chunks (no parent/child split).

    Useful for callers that only need text segments without hierarchy.
    """
    result = chunk_text(
        text=text,
        max_chars=max_chars,
        overlap_chars=overlap_chars,
        source_method=source_method,
        pages=pages,
    )
    return [c for c in result.chunks if c.chunk_type == "child" or c.chunk_type == "parent"]


# ---------------------------------------------------------------------------
# Structured content blocks (paragraph/table) preserve reading order end-to-end.
# ---------------------------------------------------------------------------
def chunk_blocks(blocks, max_chars: int = 900, overlap_chars: int = 150, source_method: str = "native_unknown") -> ChunkResult:
    import json
    chunks: list[Chunk] = []
    current_section = "正文"
    current_heading_path = "正文"
    current_parent: int | None = None
    index = 0

    def add_parent(text: str, block, section: str):
        nonlocal index, current_parent
        chunks.append(Chunk(chunk_index=index, text=text[:240], section=section[:256], heading_path=current_heading_path[:512],
            page_start=getattr(block, "page_number", None), page_end=getattr(block, "page_number", None), page_number=getattr(block, "page_number", None),
            token_count=_rough_tokens(text[:240]), chunk_type="parent", source_method=source_method, content_hash=_text_hash(text[:240]),
            reading_order=getattr(block, "order", index), bbox_json=json.dumps(getattr(block, "bbox", None), ensure_ascii=False) if getattr(block, "bbox", None) else None))
        current_parent=index; index+=1

    for block in blocks:
        raw=(getattr(block,"text","") or "").strip()
        if not raw: continue
        kind=getattr(block,"block_type","paragraph")
        if kind == "heading":
            current_section=raw[:256]
            previous=[p for p in current_heading_path.split(" > ") if p and p!="正文"]
            # A short heading replaces deeper local context; a repeated major heading starts new path.
            if raw.startswith("第") or len(previous)>=3: previous=[]
            previous.append(raw[:180]); current_heading_path=" > ".join(previous)
            add_parent(raw,block,current_section)
            continue
        if current_parent is None:
            add_parent(current_section,block,current_section)
        bbox=getattr(block,"bbox",None)
        bbox_json=json.dumps(bbox,ensure_ascii=False) if bbox else None
        common=dict(section=current_section[:256], heading_path=current_heading_path[:512], page_start=getattr(block,"page_number",None),
                    page_end=getattr(block,"page_number",None), page_number=getattr(block,"page_number",None), source_method=source_method,
                    parent_index=current_parent, reading_order=getattr(block,"order",index), bbox_json=bbox_json)
        if kind == "table":
            matrix=getattr(block,"table",None) or []
            chunks.append(Chunk(chunk_index=index,text=raw,token_count=_rough_tokens(raw),chunk_type="table",content_hash=_text_hash(raw),
                table_json=json.dumps({"rows":matrix,"sheet_name":getattr(block,"sheet_name",None)},ensure_ascii=False),**common))
            index+=1; continue
        for piece in _slice_long(raw,max_chars,overlap_chars):
            chunks.append(Chunk(chunk_index=index,text=piece,token_count=_rough_tokens(piece),chunk_type="child",content_hash=_text_hash(piece),**common))
            index+=1
    return ChunkResult(chunks=chunks)
