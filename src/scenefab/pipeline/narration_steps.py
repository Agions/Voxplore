#!/usr/bin/env python3
"""
v2.2 解说生成默认 Step Stub — Phase 1 骨架版

每个 Step 函数签名: (ctx: NarrationContext) -> StepResult

Phase 1: 仅提供"骨架实现", 验证状态机流转
Phase 2: 接入 UNDERSTAND/STORYGRAPH/DRAFT 真实实现
Phase 3: 接入 EVALUATE/HOOK_REWRITE
Phase 4: 接入 TTS_LENGTH_ADJUST/TTS/ASSEMBLE
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from .narration_context import NarrationContext
from .narration_state_machine import NarrationState, StepResult, success_step

logger = logging.getLogger(__name__)


# ============================================
# 5 个主路径状态 (Phase 2/3/4 完善)
# ============================================


def ingest_step(ctx: NarrationContext) -> StepResult:
    """① INGEST: 校验源视频 + 创建工作目录

    Phase 2 完善:
        - 校验 ctx.source_video 存在
        - 创建 ctx.output_dir (含 trace_id 子目录)
        - 检查 ffprobe 可用
    """
    start = time.time()

    # Phase 1 骨架: 仅校验路径存在
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

    return success_step(
        start,
        NarrationState.INGEST,
        f"ingest 完成 (video={ctx.source_video.name}, dir={ctx.output_dir})",
    )


def understand_step(ctx: NarrationContext) -> StepResult:
    """② UNDERSTAND: 视觉模型理解场景 (Qwen3.7/Gemini)

    Phase 2 完善:
        - 调用 services.ai.scene_analyzer.SceneAnalyzer.analyze()
        - 填充 ctx.scenes
    """
    start = time.time()
    # Phase 1 骨架: 仅占位, 等待 Phase 2 实现
    return success_step(start, state=NarrationState.UNDERSTAND, message='understand (Phase 1 stub — Phase 2 接入 SceneAnalyzer)', data={'stub': True})


def storygraph_step(ctx: NarrationContext) -> StepResult:
    """③ STORYGRAPH: 长视频剧情图谱 (LongVideoUnderstanding)

    Phase 2 完善:
        - 对 >30min 视频调用 LongVideoUnderstanding
        - 填充 ctx.story_graph
        - 检测短剧集数 → 桥段识别
    """
    start = time.time()
    # Phase 1 骨架: 仅占位
    return success_step(start, state=NarrationState.STORYGRAPH, message='storygraph (Phase 1 stub — Phase 2 接入 LongVideoUnderstanding)', data={'stub': True})


def draft_step(ctx: NarrationContext) -> StepResult:
    """④ DRAFT: LLM 生成初稿

    Phase 2 完善:
        - 组装 4 类上下文到 prompt
        - 调用 LLM (DeepSeek-V4 / Qwen3.7)
        - 填充 ctx.current_draft + ctx.current_segments
    """
    start = time.time()
    # Phase 1 骨架: 模拟一段文案, 方便测试
    ctx.current_draft = (
        f"[Phase 1 Stub] 这是第 {ctx.draft_attempts + 1} 次草稿, "
        f"平台 {ctx.platform.value}, 风格 {ctx.style.value}。"
    )
    ctx.current_segments = [{"text": ctx.current_draft, "duration": 5.0}]

    return success_step(start, state=NarrationState.DRAFT, message=f'draft 完成 (attempt={ctx.draft_attempts + 1})', data={'chars': len(ctx.current_draft)})


def hook_rewrite_step(ctx: NarrationContext) -> StepResult:
    """⑤ HOOK_REWRITE: 开场 Hook 改写 (前 2 句强化留人)

    Phase 3 完善:
        - 提取 ctx.current_draft 前 2 句
        - 调用 LLM 改写为 5 种 Hook 风格候选
        - 评估器选最佳 → 替换原文前 2 句
    """
    start = time.time()
    # Phase 1 骨架: 仅占位
    return success_step(start, state=NarrationState.HOOK_REWRITE, message='hook_rewrite (Phase 1 stub — Phase 3 接入)', data={'stub': True})


# ============================================
# 评估循环 (Phase 3 完善)
# ============================================


def evaluate_step(ctx: NarrationContext) -> StepResult:
    """⑥ EVALUATE: 评估器打分 (Qwen3.7-flash, 5 维加权)

    Phase 3 完善:
        - 调用 NarrationEvaluator.evaluate()
        - 填充 ctx.eval_score / ctx.eval_issues / ctx.eval_suggestion
    """
    start = time.time()
    # Phase 1 骨架: 默认 PASS (Phase 3 接入评估器)
    ctx.eval_score = 9.0
    ctx.eval_issues = []
    ctx.eval_suggestion = ""

    return success_step(start, state=NarrationState.EVALUATE, message=f'evaluate 完成 (score={ctx.eval_score})', data={'score': ctx.eval_score, 'stub': True})


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
# TTS 流程 (Phase 4 完善)
# ============================================


def tts_length_adjust_step(ctx: NarrationContext) -> StepResult:
    """⑨ TTS_LENGTH_ADJUST: TTS 实测时长反向约束文案

    Phase 4 完善:
        1. 先 TTS 出 ctx.current_draft
        2. 测真实时长 ctx.tts_real_duration_sec
        3. 调 LLM 压缩/扩展到 target ± 5%
        4. 再 TTS 一次
    """
    start = time.time()
    # Phase 1 骨架: 模拟 TTS
    ctx.tts_real_duration_sec = 45.0
    ctx.tts_target_duration_sec = ctx.platform_spec.target_duration_sec

    return success_step(start, state=NarrationState.TTS_LENGTH_ADJUST, message=f'tts_length_adjust (Phase 1 stub — real={ctx.tts_real_duration_sec:.1f}s, target={ctx.tts_target_duration_sec:.1f}s)', data={'stub': True})


def tts_step(ctx: NarrationContext) -> StepResult:
    """⑩ TTS: 配音合成 (Edge-TTS / F5-TTS)

    Phase 4 完善:
        - 调用 services.ai.voice_generator.VoiceGenerator
        - 写入 ctx.tts_audio_path
    """
    start = time.time()
    ctx.tts_audio_path = ctx.output_dir / f"{ctx.trace_id[:8]}_voice.mp3"
    # Phase 1 骨架: 模拟写入空文件
    try:
        ctx.tts_audio_path.touch()
    except Exception as e:  # noqa: BLE001
        return StepResult(
            success=False,
            state=NarrationState.TTS,
            error=f"写入音频文件失败: {e}",
        )

    return success_step(
        start,
        NarrationState.TTS,
        f"tts 完成 (audio={ctx.tts_audio_path.name})",
    )


def assemble_step(ctx: NarrationContext) -> StepResult:
    """⑪ ASSEMBLE: 字幕对齐 + 视频合成 + 剪映草稿

    Phase 4 完善:
        - 调用 services.video_tools.caption_gen.CaptionGenerator
        - 调用 services.export.jianying_adapter.JianyingDraft.export()
        - 写入 ctx.final_video_path / final_subtitle_path
    """
    start = time.time()
    ctx.final_subtitle_path = ctx.output_dir / f"{ctx.trace_id[:8]}.srt"
    ctx.final_video_path = ctx.output_dir / f"{ctx.trace_id[:8]}.mp4"
    ctx.final_narration = ctx.current_draft
    ctx.final_segments = ctx.current_segments

    # Phase 1 骨架: 仅占位
    duration_ms = (time.time() - start) * 1000
    return StepResult(
        success=True,
        state=NarrationState.ASSEMBLE,
        duration_ms=duration_ms,
        message=(
            f"assemble 完成 (subtitle={ctx.final_subtitle_path.name}, "
            f"video={ctx.final_video_path.name})"
        ),
    )


# ============================================
# 便捷: 一次性注册所有骨架 Step
# ============================================


def register_default_steps(sm: NarrationStateMachine) -> None:  # type: ignore[name-defined]  # noqa: F821
    """注册所有默认骨架 Step 到状态机

    使用示例:
        sm = NarrationStateMachine()
        register_default_steps(sm)
        result = sm.run(ctx)
    """
    from .narration_state_machine import NarrationStateMachine

    assert isinstance(sm, NarrationStateMachine)

    sm.register_step(NarrationState.INGEST, ingest_step)
    sm.register_step(NarrationState.UNDERSTAND, understand_step)
    sm.register_step(NarrationState.STORYGRAPH, storygraph_step)
    sm.register_step(NarrationState.DRAFT, draft_step)
    sm.register_step(NarrationState.HOOK_REWRITE, hook_rewrite_step)
    sm.register_step(NarrationState.EVALUATE, evaluate_step)
    sm.register_step(NarrationState.ACCEPT, accept_step)
    sm.register_step(NarrationState.REJECT, reject_step)
    sm.register_step(NarrationState.TTS_LENGTH_ADJUST, tts_length_adjust_step)
    sm.register_step(NarrationState.TTS, tts_step)
    sm.register_step(NarrationState.ASSEMBLE, assemble_step)
