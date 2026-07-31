#!/usr/bin/env python3
"""
v2.2 解说生成默认 Step — INGEST / ACCEPT / REJECT

每个 Step 函数签名: (ctx: NarrationContext) -> StepResult

本模块仅保留没有专属实现模块的 Step:
- ingest_step: 源视频校验 + 创建工作目录
- accept_step / reject_step: 评估循环的中转控制节点, 无业务逻辑

其余状态的 Step 由真实实现模块注册:
- understanding_steps: UNDERSTAND / STORYGRAPH / DRAFT
- evaluation_steps:    EVALUATE / HOOK_REWRITE
- assembly_steps:      TTS_LENGTH_ADJUST / TTS / ASSEMBLE

v2.2 决策: 见 docs/adr/007-narration-state-machine.md
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

from .context import NarrationContext
from .state_machine import NarrationState, StepResult

if TYPE_CHECKING:
    from .state_machine import NarrationStateMachine


# ============================================
# 主路径入口
# ============================================


def ingest_step(ctx: NarrationContext) -> StepResult:
    """① INGEST: 校验源视频 + 创建工作目录

    - 校验 ctx.source_video 存在
    - 创建 ctx.output_dir (含 trace_id 子目录)
    """
    start = time.time()

    # 校验源视频存在
    if not ctx.source_video or not Path(ctx.source_video).exists():
        return StepResult(
            success=False,
            state=NarrationState.INGEST,
            error=f"源视频不存在: {ctx.source_video}",
        )

    # 创建工作目录
    try:
        ctx.output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:  # noqa: BLE001
        return StepResult(
            success=False,
            state=NarrationState.INGEST,
            error=f"创建输出目录失败: {e}",
        )

    duration_ms = (time.time() - start) * 1000
    return StepResult(
        success=True,
        state=NarrationState.INGEST,
        duration_ms=duration_ms,
        message=f"ingest 完成 (video={ctx.source_video.name}, dir={ctx.output_dir})",
    )


# ============================================
# 评估循环控制节点
# ============================================


def accept_step(ctx: NarrationContext) -> StepResult:
    """⑦ ACCEPT: 控制流标记, 评估通过后自动跳转 HOOK_REWRITE

    ACCEPT/REJECT 是状态机评估循环的"中转节点", 无业务逻辑。
    默认实现: 直接 succeed, 主循环根据 ctx.eval_score 选择 ACCEPT/REJECT。
    """
    return StepResult(
        success=True,
        state=NarrationState.ACCEPT,
        message=f"accept (score={ctx.eval_score} >= threshold)",
    )


def reject_step(ctx: NarrationContext) -> StepResult:
    """⑧ REJECT: 控制流标记, 评估拒绝后回到 DRAFT 或终止

    主循环根据 ctx.max_attempts_reached 决定回 DRAFT 还是转 ERROR。
    REJECT 会触发 ctx.reset_draft() — 清理 eval 状态 + 增加 draft_attempts。
    """
    ctx.reset_draft()  # 增加 draft_attempts, 清理 eval 状态
    return StepResult(
        success=True,
        state=NarrationState.REJECT,
        message=(
            f"reject (score={ctx.eval_score} < threshold, "
            f"attempt={ctx.draft_attempts}/max={2})"
        ),
    )


# ============================================
# 便捷: 一次性注册所有默认 Step
# ============================================


def register_default_steps(sm: NarrationStateMachine) -> None:
    """注册默认 Step (INGEST / ACCEPT / REJECT) 到状态机

    其余状态的 Step 由真实实现模块注册:
        register_understanding_steps(sm)  # UNDERSTAND / STORYGRAPH / DRAFT
        register_evaluation_steps(sm)     # EVALUATE / HOOK_REWRITE
        register_assembly_steps(sm)       # TTS_LENGTH_ADJUST / TTS / ASSEMBLE

    使用示例:
        sm = NarrationStateMachine()
        register_default_steps(sm)
        register_understanding_steps(sm)
        register_evaluation_steps(sm)
        register_assembly_steps(sm)
        result = sm.run(ctx)
    """
    from .state_machine import NarrationStateMachine

    assert isinstance(sm, NarrationStateMachine)

    sm.register_step(NarrationState.INGEST, ingest_step)
    sm.register_step(NarrationState.ACCEPT, accept_step)
    sm.register_step(NarrationState.REJECT, reject_step)
