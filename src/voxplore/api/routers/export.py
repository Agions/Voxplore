"""
Export Router
导出 API - 支持 MP4/MOV/GIF/剪映草稿格式
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, BackgroundTasks

from voxplore.api.schemas.models import ExportRequest, ExportResponse
from voxplore.services.export.export_manager import (
    ExportManager,
    ExportFormat,
    ExportConfig,
)
from voxplore.core.exceptions import ExportError

router = APIRouter()

# 导出任务存储（生产环境应使用 Redis）
_export_tasks: dict = {}


def _build_export_config(req: ExportRequest) -> ExportConfig:
    """从 API 请求构建 ExportConfig"""
    return ExportConfig(
        format=req.format,
        quality=req.quality,
        resolution=req.resolution,
        fps=req.fps,
        codec=req.codec,
        output_path=req.output_path,
    )


async def _run_export(task_id: str, project_id: str, config: ExportConfig):
    """后台执行导出任务"""
    task = _export_tasks.get(task_id)
    if not task:
        return

    try:
        task["status"] = "processing"
        task["progress"] = 0.0
        task["current_step"] = "初始化导出器..."

        # 获取项目数据（这里应从 ProjectManager 加载）
        # 目前用 project_id 做占位
        project_data = {
            "project_id": project_id,
            "segments": [],
        }

        manager = ExportManager()
        manager.export(project_data, config)

        task["status"] = "completed"
        task["progress"] = 100.0
        task["current_step"] = "导出完成"
        task["download_url"] = config.output_path

    except ExportError as e:
        task["status"] = "failed"
        task["error"] = f"导出失败: {e.message}"
    except Exception as e:
        task["status"] = "failed"
        task["error"] = f"导出失败: {str(e)}"


@router.post("/export", status_code=202)
async def create_export_task(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
):
    """创建导出任务（异步后台执行）"""
    task_id = str(uuid.uuid4())

    # 验证输出路径
    output_path = request.output_path
    if output_path:
        output_dir = str(Path(output_path).parent)
        if not Path(output_dir).is_dir():
            raise HTTPException(
                status_code=400,
                detail=f"输出目录不存在或无效: {output_dir}",
            )

    config = _build_export_config(request)

    _export_tasks[task_id] = {
        "task_id": task_id,
        "project_id": request.project_id,
        "status": "pending",
        "progress": 0.0,
        "current_step": "等待处理...",
        "download_url": None,
        "error": None,
        "config": config,
    }

    # 后台执行导出
    background_tasks.add_task(
        _run_export, task_id, request.project_id, config
    )

    return ExportResponse(
        task_id=task_id,
        status="pending",
        progress=0.0,
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
        download_url=task.get("download_url"),
    )


@router.get("/export/{task_id}/download")
async def download_export(task_id: str):
    """下载导出的文件"""
    if task_id not in _export_tasks:
        raise HTTPException(status_code=404, detail="Export task not found")

    task = _export_tasks[task_id]
    if task["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"导出未完成，当前状态: {task['status']}",
        )

    download_url = task.get("download_url")
    if not download_url:
        raise HTTPException(status_code=404, detail="导出文件路径不存在")

    return {
        "download_url": download_url,
        "filename": Path(download_url).name,
    }


@router.get("/export/formats")
async def list_export_formats():
    """获取支持的导出格式列表"""
    return {
        "formats": [
            {
                "value": fmt.value,
                "label": _format_label(fmt),
                "description": _format_desc(fmt),
            }
            for fmt in ExportFormat
        ]
    }


def _format_label(fmt: ExportFormat) -> str:
    return {
        ExportFormat.MP4: "MP4 视频",
        ExportFormat.MOV: "MOV 视频",
        ExportFormat.GIF: "GIF 动图",
        ExportFormat.JIANYING: "剪映草稿",
    }[fmt]


def _format_desc(fmt: ExportFormat) -> str:
    return {
        ExportFormat.MP4: "H.264 编码，适合直接分享",
        ExportFormat.MOV: "高质量视频格式",
        ExportFormat.GIF: "无损动图，适合简短循环内容",
        ExportFormat.JIANYING: "导出为剪映可编辑的草稿工程",
    }[fmt]
