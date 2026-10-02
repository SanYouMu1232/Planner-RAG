"""Deterministic local retrieval used before real vector DB integration."""

from __future__ import annotations

import re
from dataclasses import dataclass
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models


@dataclass(slots=True)
class RetrievedChunk:
    score: float
    doc: models.Document
    chunk: models.DocumentChunk


def _keywords(question: str) -> list[str]:
    words = re.findall(r"[\u4e00-\u9fa5]{2,}|[A-Za-z0-9]{2,}", question.lower())
    stop = {"这个", "是否", "哪些", "什么", "如何", "规划", "项目", "请问", "需要"}
    out: list[str] = []
    for w in words:
        if w in stop:
            continue
        out.append(w)
        # Chinese has no spaces; add short n-grams so MVP retrieval still works without a tokenizer.
        if re.fullmatch(r"[\u4e00-\u9fa5]+", w) and len(w) > 4:
            for n in (4, 3, 2):
                for i in range(0, min(len(w) - n + 1, 8)):
                    gram = w[i:i+n]
                    if gram not in stop:
                        out.append(gram)
    dedup = list(dict.fromkeys(out))
    return dedup[:18]


def _score(text: str, keywords: list[str]) -> float:
    if not keywords:
        return 0.0
    lower = text.lower()
    score = 0.0
    for kw in keywords:
        count = lower.count(kw)
        if count:
            score += 1.0 + min(count, 4) * 0.2
    return score


async def retrieve_chunks(
    db: AsyncSession,
    project_id: str,
    question: str,
    knowledge_source: str = "both",
    limit: int = 6,
) -> list[RetrievedChunk]:
    q = select(models.Document, models.DocumentChunk).join(models.DocumentChunk).where(models.Document.parse_status == "ready", models.Document.is_usable == True, models.DocumentChunk.chunk_type != "parent")

    if knowledge_source == "project":
        q = q.where(models.Document.knowledge_base == "project", models.Document.project_id == project_id)
    elif knowledge_source == "general":
        q = q.where(models.Document.knowledge_base == "general")
    else:
        q = q.where(
            or_(
                models.Document.knowledge_base == "general",
                (models.Document.knowledge_base == "project") & (models.Document.project_id == project_id),
            )
        )

    rows = (await db.execute(q)).all()
    keywords = _keywords(question)
    table_intent = any(term in question for term in ("表格", "指标", "数据", "统计", "附表", "比例", "面积", "人口"))
    scored = []
    for doc, chunk in rows:
        value = _score(f"{doc.file_name}\n{chunk.section}\n{chunk.text}", keywords)
        if value <= 0:
            continue
        if chunk.chunk_type == "table":
            value += 0.35
            if table_intent:
                value += 0.45
        scored.append(RetrievedChunk(value, doc, chunk))
    scored.sort(key=lambda x: (x.score, -x.chunk.chunk_index), reverse=True)
    return [x for x in scored[:limit] if x.score > 0]
