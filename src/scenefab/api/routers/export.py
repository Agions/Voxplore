"""
Export Router
导出 API - 支持 MP4/MOV/GIF/剪映草稿格式
"""

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException

from scenefab.api.schemas.models import ExportRequest, ExportResponse
from scenefab.exceptions import ExportError
from scenefab.services.export.export_manager import (
    ExportConfig,
    ExportFormat,
    ExportManager,
)
from scenefab.utils.security import (
    ALLOWED_VIDEO_EXTENSIONS,
    PathValidator,
    SecurityError,
)

router = APIRouter()

# 导出任务存储（生产环境应使用 Redis）
_export_tasks: dict = {}


# 安全默认: API 模式下 output_path 只允许落在项目工作区下的 outputs/ 或用户主目录下的 scenefab 导出目录,
# 避免任意写 /etc /root /System32 等敏感位置. 用户可在 settings.allowed_base_dirs 扩展.
_DEFAULT_ALLOWED_BASE_DIRS = (
    os.path.join(os.getcwd(), "outputs"),
    os.path.expanduser("~/.scenefab/exports"),
    os.path.expanduser("~/Downloads"),
    os.path.expanduser("~/.cache/scenefab/exports"),
)


def _get_path_validator() -> PathValidator:
    """获取路径校验器: 优先使用 settings 中的 allowed_base_dirs, 否则使用安全默认."""
    try:
        from scenefab.settings import get_config

        configured = getattr(get_config(), "allowed_base_dirs", None)
        base_dirs = list(configured) if configured else list(_DEFAULT_ALLOWED_BASE_DIRS)
    except Exception:
        # 配置加载失败时回退到安全默认
        base_dirs = list(_DEFAULT_ALLOWED_BASE_DIRS)
    return PathValidator(allowed_base_dirs=base_dirs)


def _validate_output_path(output_path: str | None) -> None:
    """校验用户提供的 output_path, 不合法时抛 HTTPException."""
    if not output_path:
        return

    validator = _get_path_validator()

    # 1) 路径合法性 (含 DANGEROUS_PATH_PATTERNS 黑名单 + 允许的 base 目录)
    try:
        result = validator.validate(output_path)
    except SecurityError as e:
        raise HTTPException(status_code=400, detail=f"无效的路径: {e}") from e
    if not result.passed:
        raise HTTPException(status_code=400, detail=f"无效的路径: {result.message}")

    # 2) 扩展名白名单 (视频/字幕/草稿包)
    abs_path = Path(result.details["abs_path"]) if result.details else Path(output_path)
    ext_result = validator.validate_extension(
        str(abs_path), ALLOWED_VIDEO_EXTENSIONS
    )
    if not ext_result.passed:
        raise HTTPException(
            status_code=400,
            detail=ext_result.message,
        )

    # 3) 父目录存在性 (可写性由执行期决定, 这里只校验路径)
    output_dir = abs_path.parent
    if not output_dir.is_dir():
        raise HTTPException(
            status_code=400,
            detail=f"输出目录不存在或无效: {output_dir}",
        )


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

    # 验证输出路径 (走 PathValidator: DANGEROUS_PATH_PATTERNS + allowed_base_dirs)
    _validate_output_path(request.output_path)

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
    background_tasks.add_task(_run_export, task_id, request.project_id, config)

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
