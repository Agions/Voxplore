"""
Pipeline Router
流水线 API - 核心的视频解说生成接口
"""

import asyncio
import logging
import os
import threading
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException

from scenefab.api.schemas.models import NarrationRequest, PipelineStatus
from scenefab.core.task_store import get_task_store
from scenefab.services.video.pipeline_integrator import PipelineIntegrator
from scenefab.utils.security import SecurityError

logger = logging.getLogger(__name__)

router = APIRouter()

# v2.1: 替换 v1.x 的私货 `_tasks: dict = {}` 为共享 TaskStore
# 支持 InMemory / SQLite / Redis（通过 set_task_store() 注入）
_task_store = get_task_store()

# 全局 PipelineIntegrator 实例
_integrator: PipelineIntegrator | None = None
_integrator_lock = threading.Lock()

# 安全默认: output_dir 只允许落在项目工作区下的 outputs/ 或用户主目录下的 scenefab 导出目录,
# 避免任意写 /etc /root /System32 等敏感位置. 用户可在 settings.allowed_base_dirs 扩展.
# 复用 api/routers/export.py 的安全语义（共享同一 PathValidator 实例）.

from .export import _get_path_validator  # noqa: F401  复用 export.py 的安全路径校验器


def _validate_output_dir(output_dir: str | None) -> str | None:
    """校验用户提供的 output_dir, 不合法时抛 HTTPException.

    与 api/routers/export.py:_validate_output_path 同型, 但用于目录而非文件.
    用户未提供 (None) 时返回 None (调用方用默认).
    """
    if not output_dir:
        return output_dir

    validator = _get_path_validator()

    # 1) 路径合法性 (含 DANGEROUS_PATH_PATTERNS 黑名单 + 允许的 base 目录)
    try:
        result = validator.validate(output_dir)
    except SecurityError as e:
        raise HTTPException(status_code=400, detail=f"无效的路径: {e}") from e
    if not result.passed:
        raise HTTPException(status_code=400, detail=f"无效的路径: {result.message}")

    return output_dir


def _get_integrator() -> PipelineIntegrator:
    global _integrator
    if _integrator is None:
        with _integrator_lock:
            if _integrator is None:
                _integrator = PipelineIntegrator()
    return _integrator


# ──────────────────────────────────────────────────────────
# 端点
# ──────────────────────────────────────────────────────────


@router.post("/pipeline/narrate", status_code=202)
async def create_narration_task(request: NarrationRequest):
    """
    创建视频解说任务

    上传视频文件，AI 生成第一人称解说

    返回 task_id 用于查询进度
    """
    # 早期校验 (避免进入处理流程后才拒绝)
    # NarrationRequest 当前不包含 output_dir 字段, 但 _process_narration
    # 内部用 req.get("output_dir", default), 所以 source_video 也走
    # PipelineIntegrator._validate_source_video (URL prefix or os.path.exists).
    # 防御性校验 source_video 防止空字符串/None.
    if not request.video_url or not request.video_url.strip():
        raise HTTPException(status_code=400, detail="video_url 不能为空")

    task_id = str(uuid.uuid4())

    _task_store.save(
        task_id,
        {
            "task_id": task_id,
            "status": "pending",
            "progress": 0.0,
            "current_step": "等待处理",
            "estimated_remaining": None,
            "result_url": None,
            "error": None,
            "request": request.model_dump(),
        },
    )

    asyncio.create_task(_process_narration(task_id))

    return {"task_id": task_id, "status": "pending"}


@router.get("/pipeline/{task_id}/status", response_model=PipelineStatus)
async def get_task_status(task_id: str):
    """获取任务状态"""
    task = _task_store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return PipelineStatus(
        task_id=task["task_id"],
        status=task["status"],
        progress=task["progress"],
        current_step=task["current_step"],
        estimated_remaining=task["estimated_remaining"],
        result_url=task.get("result_url"),
        error=task.get("error"),
    )


@router.get("/pipeline/{task_id}/cancel", status_code=202)
async def cancel_task(task_id: str):
    """取消任务"""
    task = _task_store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    _task_store.update(task_id, status="cancelled")
    return {"task_id": task_id, "status": "cancelled"}


# ──────────────────────────────────────────────────────────
# 内部处理
# ──────────────────────────────────────────────────────────


async def _process_narration(task_id: str):
    """
    调用 PipelineIntegrator 真实处理流程

    步骤：analyze → script → voice → caption → interleave → export
    """
    task = _task_store.get(task_id)
    if not task:
        return

    try:
        req = task["request"]
        integrator = _get_integrator()

        # ── 步骤 1: 创建项目 ──
        _update(task_id, "pending", 5.0, "正在创建项目...")

        project = integrator.create_project(
            source_video=req["video_url"],
            context=req.get("context", ""),
            emotion=req.get("emotion", "healing"),
            name=req.get("name"),
        )

        # ── 步骤 2: 分析场景 ──
        _update(task_id, "analyzing", 15.0, "正在分析视频场景...")

        # ── 步骤 3: 生成文案 ──
        _update(task_id, "script", 35.0, "正在生成解说脚本...")
        if req.get("custom_script"):
            integrator.generate_script(project, custom_script=req["custom_script"])
        else:
            integrator.generate_script(project)

        # ── 步骤 4: 生成配音 ──
        _update(task_id, "voice", 60.0, "正在合成配音...")
        integrator.generate_voice(project)

        # ── 步骤 5: 生成字幕 ──
        _update(task_id, "caption", 75.0, "正在生成字幕...")
        caption_style = req.get("caption_style", "cinematic")
        integrator.generate_captions(project, style=caption_style)

        # ── 步骤 6: 视角映射 + 穿插 ──
        if req.get("include_interleave", True):
            _update(task_id, "interleaving", 85.0, "正在处理视频穿插...")

            perspective_shots = integrator.run_perspective_mapping(project)
            timeline = integrator.run_video_interleave(project, perspective_shots)
            integrator.apply_interleave_to_project(project, timeline)

        # ── 步骤 7: 导出 ──
        _update(task_id, "exporting", 95.0, "正在生成最终视频...")
        # output_dir 早期校验: 即使 schema 不包含, 防御性验证 default 路径
        # 落入安全 base dir (output/jianying_drafts 在 cwd 下的 outputs 子目录)
        output_dir = req.get("output_dir", "./output/jianying_drafts")
        if output_dir:
            try:
                _validate_output_dir(output_dir)
            except HTTPException:
                # 校验失败时降级到安全默认
                logger.warning(
                    f"output_dir 校验失败 ({output_dir}), 降级到安全默认"
                )
                output_dir = os.path.join(os.getcwd(), "outputs", "jianying_drafts")

        _ = integrator.export_to_jianying(project, output_dir)

        _update(
            task_id,
            "completed",
            100.0,
            "处理完成",
            result_url=f"/api/v1/export/{task_id}/download",
        )

    except Exception as e:
        _update(task_id, "error", 0.0, f"处理失败: {str(e)}", error=str(e))


def _update(
    task_id: str,
    status: str,
    progress: float,
    current_step: str,
    result_url=None,
    error=None,
):
    """更新任务状态（v2.1 - 通过 TaskStore 持久化）"""
    updates: dict[str, Any] = {
        "status": status,
        "progress": progress,
        "current_step": current_step,
    }
    if result_url is not None:
        updates["result_url"] = result_url
    if error is not None:
        updates["error"] = error
    _task_store.update(task_id, **updates)
