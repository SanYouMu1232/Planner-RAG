"""Project CRUD endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from .. import crud
from ..schemas import ProjectCreate, ProjectOut, ProjectUpdate
from ..serializers import project_out

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
async def list_projects(db: AsyncSession = Depends(get_db)):
    return [project_out(p) for p in await crud.list_projects(db)]


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(body: ProjectCreate, db: AsyncSession = Depends(get_db)):
    p = await crud.create_project(db, body.model_dump())
    return project_out(p)


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    p = await crud.get_project(db, project_id)
    if p is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project_out(p)


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(project_id: str, body: ProjectUpdate, db: AsyncSession = Depends(get_db)):
    p = await crud.update_project(db, project_id, body.model_dump(exclude_none=True))
    if p is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project_out(p)


@router.delete("/{project_id}", response_model=dict)
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    deleted = await crud.delete_project(db, project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"ok": True}
