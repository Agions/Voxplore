"""
Pipeline Router
流水线 API - 核心的视频解说生成接口
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
import uuid
import asyncio

from app.api.schemas.models import (
    NarrationRequest, PipelineStatus, InterleaveModeAPI
)
from app.services.video.pipeline_integrator import PipelineIntegrator

router = APIRouter()

# 任务存储（生产环境应使用 Redis）
_tasks: dict = {}

# 全局 PipelineIntegrator 实例
_integrator: Optional[PipelineIntegrator] = None


def _get_integrator() -> PipelineIntegrator:
    global _integrator
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
    task_id = str(uuid.uuid4())

    _tasks[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "progress": 0.0,
        "current_step": "等待处理",
        "estimated_remaining": None,
        "result_url": None,
        "error": None,
        "request": request.model_dump(),
    }

    asyncio.create_task(_process_narration(task_id))

    return {"task_id": task_id, "status": "pending"}


@router.get("/pipeline/{task_id}/status", response_model=PipelineStatus)
async def get_task_status(task_id: str):
    """获取任务状态"""
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = _tasks[task_id]
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
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    _tasks[task_id]["status"] = "cancelled"
    return {"task_id": task_id, "status": "cancelled"}


# ──────────────────────────────────────────────────────────
# 内部处理
# ──────────────────────────────────────────────────────────

async def _process_narration(task_id: str):
    """
    调用 PipelineIntegrator 真实处理流程
    
    步骤：analyze → script → voice → caption → interleave → export
    """
    task = _tasks.get(task_id)
    if not task:
        return

    try:
        req = task["request"]
        integrator = _get_integrator()

        # ── 步骤 1: 创建项目 ──
        _update(task, "pending", 5.0, "正在创建项目...")

        from app.services.video.monologue_maker import MonologueProject, MonologueStyle
        project = integrator.create_project(
            source_video=req["source_video"],
            context=req.get("context", ""),
            emotion=req.get("emotion", "惆怅"),
            name=req.get("name"),
        )

        # ── 步骤 2: 分析场景 ──
        _update(task, "analyzing", 15.0, "正在分析视频场景...")

        # ── 步骤 3: 生成文案 ──
        _update(task, "script", 35.0, "正在生成解说脚本...")
        if req.get("custom_script"):
            integrator.generate_script(project, custom_script=req["custom_script"])
        else:
            integrator.generate_script(project)

        # ── 步骤 4: 生成配音 ──
        _update(task, "voice", 60.0, "正在合成配音...")
        integrator.generate_voice(project)

        # ── 步骤 5: 生成字幕 ──
        _update(task, "caption", 75.0, "正在生成字幕...")
        integrator.generate_captions(project, style=req.get("caption_style", "cinematic"))

        # ── 步骤 6: 视角映射 + 穿插 ──
        if req.get("include_interleave", True):
            _update(task, "interleaving", 85.0, "正在处理视频穿插...")

            perspective_shots = integrator.run_perspective_mapping(project)
            timeline = integrator.run_video_interleave(project, perspective_shots)
            integrator.apply_interleave_to_project(project, timeline)

        # ── 步骤 7: 导出 ──
        _update(task, "exporting", 95.0, "正在生成最终视频...")
        draft_path = integrator.export_to_jianying(
            project,
            req.get("output_dir", "./output/jianying_drafts")
        )

        _update(
            task, "completed", 100.0, "处理完成",
            result_url=f"/api/v1/export/{task_id}/download"
        )

    except Exception as e:
        _update(task, "error", 0.0, f"处理失败: {str(e)}", error=str(e))


def _update(task: dict, status: str, progress: float, current_step: str,
            result_url=None, error=None):
    task["status"] = status
    task["progress"] = progress
    task["current_step"] = current_step
    if result_url is not None:
        task["result_url"] = result_url
    if error is not None:
        task["error"] = error
