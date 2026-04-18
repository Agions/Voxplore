"""
Export Router
导出 API
"""

from fastapi import APIRouter, HTTPException
import uuid

from app.api.schemas.models import ExportRequest, ExportResponse

router = APIRouter()

_export_tasks: dict = {}


@router.post("/export", status_code=202)
async def create_export_task(request: ExportRequest):
    """创建导出任务"""
    task_id = str(uuid.uuid4())

    _export_tasks[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "progress": 0.0,
        "download_url": None
    }

    # 实际应提交到导出服务
    return ExportResponse(
        task_id=task_id,
        status="pending",
        progress=0.0
    )


@router.get("/export/{task_id}/status", response_model=ExportResponse)
async def get_export_status(task_id: str):
    """获取导出状态"""
    if task_id not in _export_tasks:
        raise HTTPException(status_code=404, detail="Export task not found")

    task = _export_tasks[task_id]
    return ExportResponse(
        task_id=task["task_id"],
        status=task["status"],
        progress=task["progress"],
        download_url=task.get("download_url")
    )


@router.get("/export/{task_id}/download")
async def download_export(task_id: str):
    """下载导出的文件"""
    if task_id not in _export_tasks:
        raise HTTPException(status_code=404, detail="Export task not found")

    task = _export_tasks[task_id]
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="Export not ready")

    return {"download_url": task.get("download_url")}
