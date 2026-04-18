"""
Projects Router
项目管理 API
"""

from fastapi import APIRouter, HTTPException
from typing import List

from app.api.schemas.models import (
    ProjectCreate, ProjectResponse, ProjectListResponse
)

router = APIRouter()


# 模拟数据（实际应连接数据库）
_projects_db: dict = {}


@router.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(request: ProjectCreate):
    """创建新项目"""
    import uuid
    from datetime import datetime

    project_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    project = ProjectResponse(
        id=project_id,
        name=request.name,
        description=request.description,
        created_at=now,
        updated_at=now,
        status="active"
    )

    _projects_db[project_id] = project
    return project


@router.get("/projects", response_model=ProjectListResponse)
async def list_projects():
    """列出所有项目"""
    projects = list(_projects_db.values())
    return ProjectListResponse(
        projects=projects,
        total=len(projects)
    )


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """获取项目详情"""
    if project_id not in _projects_db:
        raise HTTPException(status_code=404, detail="Project not found")
    return _projects_db[project_id]


@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(project_id: str):
    """删除项目"""
    if project_id not in _projects_db:
        raise HTTPException(status_code=404, detail="Project not found")
    del _projects_db[project_id]
