"""
Projects Router
项目管理 API
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

from scenefab.api.schemas.models import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
)

router = APIRouter()

# 文件持久化路径（简易方案，非完整数据库）
_DB_PATH = Path.home() / ".scenefab" / "api_projects.json"

_projects_db: dict[str, ProjectResponse] = {}


def _load_projects() -> None:
    """启动时从文件加载项目；文件缺失或损坏时以空数据库启动"""
    if not _DB_PATH.exists():
        return
    try:
        data = json.loads(_DB_PATH.read_text(encoding="utf-8"))
        for project_id, item in data.items():
            _projects_db[project_id] = ProjectResponse.model_validate(item)
    except (OSError, ValueError):
        _projects_db.clear()


def _save_projects() -> None:
    """将当前项目数据写入文件"""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {
        project_id: project.model_dump() for project_id, project in _projects_db.items()
    }
    _DB_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


# 模块导入时加载已有项目（等价于启动加载）
_load_projects()


@router.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(request: ProjectCreate):
    """创建新项目"""
    project_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    project = ProjectResponse(
        id=project_id,
        name=request.name,
        description=request.description,
        created_at=now,
        updated_at=now,
        status="active",
    )

    _projects_db[project_id] = project
    _save_projects()
    return project


@router.get("/projects", response_model=ProjectListResponse)
async def list_projects():
    """列出所有项目"""
    projects = list(_projects_db.values())
    return ProjectListResponse(projects=projects, total=len(projects))


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
    _save_projects()
