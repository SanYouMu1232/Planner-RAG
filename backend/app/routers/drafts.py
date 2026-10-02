"""Lightweight planning draft generation."""

import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from .. import crud
from ..schemas import DraftGenerateRequest, DraftOut
from ..services.retrieval import retrieve_chunks

router = APIRouter(tags=["drafts"])


@router.post("/projects/{project_id}/drafts/generate", response_model=DraftOut)
async def generate_draft(project_id: str, body: DraftGenerateRequest, db: AsyncSession = Depends(get_db)):
    project = await crud.get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    retrieved = await retrieve_chunks(db, project_id, body.prompt, str(body.knowledge_source), limit=5)
    refs = "\n".join([f"- {r.doc.file_name}｜{r.chunk.section}：{r.chunk.text[:80]}" for r in retrieved]) or "- 当前知识库未找到明确依据，以下内容仅作结构草案。"
    content = (
        "# 规划说明草案\n\n"
        "## 一、规划依据\n"
        f"本章节围绕“{body.prompt}”展开，优先采用通用知识库与当前项目知识库中可核查资料。\n\n"
        "## 二、依据摘录\n"
        f"{refs}\n\n"
        "## 三、规划师提示\n"
        "生成文本需结合原文条款、政策状态和项目实际条件复核后使用。"
    )
    return DraftOut(id=f"draft-{uuid.uuid4().hex[:12]}", content=content, citations=[])


@router.post("/drafts/{draft_id}/export", response_model=dict)
async def export_draft(draft_id: str):
    return {"ok": True, "format": "md", "content": f"# Draft {draft_id}\n\n请在前端传入编辑后的正文后再扩展真实导出。\n"}
