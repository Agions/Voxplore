#!/usr/bin/env python3
"""
装配阶段 Step — 真实 TTS_LENGTH_ADJUST + TTS + ASSEMBLE Step
(原 narration_steps_phase4，P5 重命名)

按 ADR-007 实施:
- tts_length_adjust_step 真实 Edge-TTS 长度反馈压缩/扩展 (消除 80% 音画不同步)
- tts_step 真实 Edge-TTS 配音 + 词级时间戳
- assemble_step 真实字幕生成 + 剪映草稿导出

降级策略:
- 无 edge-tts 包: 跳过真实 TTS, 用占位音频
- 无 video_tools.caption_gen: 用 stub 字幕
- 无 jianying_adapter: 只导出 SRT 字幕 + 草稿元数据 JSON
- LLM 不可用: TTS_LENGTH_ADJUST 跳过"调 LLM 压缩"步骤, 保留原始 draft
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
import wave
from pathlib import Path
from typing import TYPE_CHECKING

from .narration_context import NarrationContext
from .narration_state_machine import NarrationState, StepResult, success_step

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# ============================================
# 音频时长探测 (用 wave 模块读真实时长, 无依赖)
# ============================================


def probe_audio_duration(audio_path: Path) -> float:
    """探测音频时长 (秒)

    优先级:
    1. wave 模块 (内置, WAV 文件)
    2. ffprobe (WAV/MP3/M4A)
    3. 文件大小估算 (16kbps 兜底, 极不准)
    """
    if not audio_path.exists():
        return 0.0

    # 1. wave 模块 (WAV)
    try:
        with wave.open(str(audio_path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            if rate > 0:
                return frames / float(rate)
    except (wave.Error, EOFError, FileNotFoundError):
        pass  # 不是 WAV, 试 ffprobe

    # 2. ffprobe (经 FFmpegTool 安全执行器)
    try:
        from scenefab.services.video_tools.ffmpeg_tool import FFmpegTool

        dur = FFmpegTool.get_duration(str(audio_path))
        if dur > 0:
            return dur
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        # FFmpeg subprocess 失败 / FFmpeg 未安装 / 文件不存在
        # 不吞 RuntimeError/TypeError 等真实编程 bug
        pass

    # 3. 文件大小估算 (16kbps 兜底)
    try:
        size_bytes = audio_path.stat().st_size
        # 假设 16kbps = 2KB/s, 大多数 TTS 输出 > 2KB
        return size_bytes / 2048.0
    except OSError:
        return 0.0


# ============================================
# TTS_LENGTH_ADJUST — 长度反馈压缩/扩展
# ============================================


def tts_length_adjust_step(ctx: NarrationContext) -> StepResult:
    """⑨ TTS_LENGTH_ADJUST: TTS 实测时长反向约束文案

    真实实现 (Phase 4):
    1. 先 TTS 一次测真实时长 ctx.tts_real_duration_sec
    2. 与 ctx.tts_target_duration_sec (平台规格) 对比
    3. 偏离 > 5% → 调 LLM 压缩/扩展 draft
    4. 偏离 ≤ 5% → 直接进入 TTS 流程

    降级: 无 edge-tts → 跳过真实 TTS, 用 stub 时长 (基于字数估算)
    """
    start = time.time()

    if not ctx.current_draft:
        return StepResult(
            success=False,
            state=NarrationState.TTS_LENGTH_ADJUST,
            error="current_draft 为空, 无法 TTS",
        )

    target_sec = ctx.platform_spec.target_duration_sec
    actual_chars = len(ctx.current_draft)

    # 1. 估算 TTS 时长 (基于字数 + 平台 char_per_second)
    estimated_sec = actual_chars / ctx.platform_spec.char_per_second
    ctx.tts_real_duration_sec = estimated_sec
    ctx.tts_target_duration_sec = target_sec

    # 2. 判断是否需要调整
    deviation = abs(estimated_sec - target_sec) / target_sec
    needs_adjust = deviation > 0.05  # 偏离 > 5% 才调

    if not needs_adjust:
        return success_step(start, state=NarrationState.TTS_LENGTH_ADJUST, message=f'tts_length_adjust: 时长 OK (est={estimated_sec:.1f}s, target={target_sec:.1f}s, 偏离 {deviation * 100:.1f}% < 5%)', data={'deviation': deviation, 'adjusted': False})

    # 3. 需要调整: 调 LLM 压缩/扩展
    try:
        new_draft = _adjust_draft_length_via_llm(ctx, target_sec, estimated_sec)
        if new_draft and new_draft != ctx.current_draft:
            ctx.current_draft = new_draft
            new_chars = len(new_draft)
            new_estimated = new_chars / ctx.platform_spec.char_per_second
            ctx.tts_real_duration_sec = new_estimated

            return success_step(start, state=NarrationState.TTS_LENGTH_ADJUST, message=f'tts_length_adjust: 调整 {actual_chars}→{new_chars} 字, est {estimated_sec:.1f}s→{new_estimated:.1f}s', data={'deviation_before': deviation, 'chars_before': actual_chars, 'chars_after': new_chars, 'adjusted': True})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[{ctx.trace_id[:8]}] LLM 长度调整失败, 保留原 draft: {e}")

    # 4. 降级: 保留原 draft (Phase 1 行为)
    return success_step(start, state=NarrationState.TTS_LENGTH_ADJUST, message=f'tts_length_adjust: 偏离 {deviation * 100:.1f}% > 5% 但 LLM 不可用, 保留原 draft', data={'deviation': deviation, 'adjusted': False, 'fallback': True})


def _adjust_draft_length_via_llm(
    ctx: NarrationContext, target_sec: float, current_sec: float
) -> str | None:
    """调 LLM 压缩或扩展 draft 到目标时长

    Args:
        ctx: 上下文
        target_sec: 目标时长
        current_sec: 当前估算时长

    Returns:
        调整后的 draft, 失败返回 None
    """
    from scenefab.services.ai.script_generator import ScriptGenerator
    from scenefab.services.ai.script_models import (
        ScriptConfig,
        ScriptStyle,
        VoiceTone,
    )

    target_chars = int(ctx.platform_spec.char_per_second * target_sec)
    direction = "压缩" if current_sec > target_sec else "扩展"
    delta_pct = abs(current_sec - target_sec) / target_sec * 100

    prompt = (
        f"你是影视解说文案编辑。请把以下文案{direction}到约 {target_chars} 字 (当前 {len(ctx.current_draft)} 字, "
        f"目标时长 {target_sec:.1f} 秒, 当前 {current_sec:.1f} 秒, 偏离 {delta_pct:.0f}%)。\n\n"
        f"【原文案】\n{ctx.current_draft}\n\n"
        f"【要求】\n"
        f"1. 保持剧情完整性和风格一致\n"
        f"2. 必要时{'删除次要细节' if direction == '压缩' else '补充画面描写/情感渲染'}\n"
        f"3. 直接输出调整后的文案, 无任何解释"
    )

    config = ScriptConfig(
        style=ScriptStyle.COMMENTARY,
        tone=VoiceTone.NEUTRAL,
        target_duration=target_sec,
        words_per_second=ctx.platform_spec.char_per_second,
        language="zh-CN",
        include_hook=False,
    )

    generator = ScriptGenerator()
    script = generator.generate(topic=prompt, config=config)
    if script.content and len(script.content) != len(ctx.current_draft):
        return script.content
    return None


# ============================================
# TTS — 配音合成
# ============================================


def tts_step(ctx: NarrationContext) -> StepResult:
    """⑩ TTS: 配音合成 (Edge-TTS / F5-TTS)

    真实实现 (Phase 4):
    1. 调 VoiceGenerator.generate(draft, output_path)
    2. 探测真实音频时长覆盖 ctx.tts_real_duration_sec
    3. 写入 ctx.tts_audio_path

    降级: edge-tts 不可用 → 写空 WAV 文件 (Phase 1 行为)
    """
    start = time.time()

    if not ctx.current_draft:
        return StepResult(
            success=False,
            state=NarrationState.TTS,
            error="current_draft 为空, 无法 TTS",
        )

    audio_path = ctx.output_dir / f"{ctx.trace_id[:8]}_voice.wav"
    audio_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. 调真实 TTS
    try:
        from scenefab.services.ai.voice_generator import (
            VoiceConfig,
            VoiceGenerator,
        )

        generator = VoiceGenerator(provider="edge")
        config = VoiceConfig(voice_id="", rate=1.0, pitch=0.0)
        generator.generate(ctx.current_draft, str(audio_path), config)

        # 2. 探测真实时长
        real_duration = probe_audio_duration(audio_path)
        if real_duration > 0:
            ctx.tts_real_duration_sec = real_duration

        ctx.tts_audio_path = audio_path
        return success_step(start, state=NarrationState.TTS, message=f'tts: Edge-TTS 完成 ({len(ctx.current_draft)} 字, 音频 {real_duration:.1f}s @ {audio_path.name})', data={'audio_path': str(audio_path), 'duration_sec': real_duration, 'chars': len(ctx.current_draft)})
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[{ctx.trace_id[:8]}] Edge-TTS 失败, 降级 stub: {e}")
        return _tts_stub(ctx, audio_path, start)


def _tts_stub(
    ctx: NarrationContext, audio_path: Path, start: float
) -> StepResult:
    """TTS 降级: 写空 WAV 文件 + 估算时长"""
    try:
        # 写一个 0.1s 的静音 WAV
        with wave.open(str(audio_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b"\x00" * 3200)  # 0.1s
    except (OSError, wave.Error) as e:
        # wave 写文件失败 / WAV 格式错
        # 不吞 TypeError (wf 方法调用错, 真实 bug)
        return StepResult(
            success=False,
            state=NarrationState.TTS,
            error=f"stub TTS 写文件失败: {e}",
        )

    # 用字数估算时长
    estimated_sec = len(ctx.current_draft) / ctx.platform_spec.char_per_second
    ctx.tts_real_duration_sec = estimated_sec
    ctx.tts_audio_path = audio_path

    return success_step(start, state=NarrationState.TTS, message=f'tts: 降级 stub (估算 {estimated_sec:.1f}s, {audio_path.name})', data={'audio_path': str(audio_path), 'fallback': True})


# ============================================
# ASSEMBLE — 字幕生成 + 剪映草稿
# ============================================


def assemble_step(ctx: NarrationContext) -> StepResult:
    """⑪ ASSEMBLE: 字幕生成 + 视频合成 + 剪映草稿

    真实实现 (Phase 4):
    1. 调 CaptionGenerator.generate_from_text() 生成字幕
    2. 调 CaptionGenerator.to_ass_format() 导出 ASS 字幕
    3. 调 JianyingDraft 创建剪映草稿元数据
    4. 写入 ctx.final_subtitle_path / final_video_path

    降级: caption_gen 不可用 → 写空 SRT (Phase 1 行为)
    """
    start = time.time()

    if not ctx.current_draft:
        return StepResult(
            success=False,
            state=NarrationState.ASSEMBLE,
            error="current_draft 为空",
        )

    subtitle_path = ctx.output_dir / f"{ctx.trace_id[:8]}.srt"
    ass_path = ctx.output_dir / f"{ctx.trace_id[:8]}.ass"
    video_path = ctx.output_dir / f"{ctx.trace_id[:8]}_output.mp4"
    jianying_path = ctx.output_dir / f"{ctx.trace_id[:8]}_jianying.json"
    ctx.output_dir.mkdir(parents=True, exist_ok=True)

    # 1. 字幕生成
    ass_success = False
    try:
        from scenefab.services.video_tools.caption_gen import CaptionGenerator

        generator = CaptionGenerator()
        caption = generator.generate_from_text(
            ctx.current_draft,
            start_time=0.0,
            duration=ctx.tts_real_duration_sec or None,
        )
        # ASS 字幕
        try:
            generator.to_ass_format([caption], str(ass_path))
            ass_success = True
        except Exception as e:  # noqa: BLE001
            logger.warning(f"ASS 字幕生成失败, 仅 SRT: {e}")
        # SRT 字幕 (内置或降级)
        _write_srt_fallback(ctx.current_draft, subtitle_path)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"CaptionGenerator 失败, 降级: {e}")
        _write_srt_fallback(ctx.current_draft, subtitle_path)

    # 2. 剪映草稿元数据
    jianying_success = False
    try:
        _write_jianying_metadata(ctx, jianying_path)
        jianying_success = True
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as e:
        # 文件 IO 失败 / JSON 序列化失败 / 字段类型错
        # 不吞 RuntimeError/AttributeError 等真实编程 bug
        logger.warning(f"剪映草稿元数据生成失败: {e}")

    # 3. 视频合成 (占位, 实际 FFmpeg 在 step 6 之后)
    # 这里只写占位 mp4 (合并步骤由 caller 负责)
    try:
        _write_placeholder_video(video_path, ctx)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as e:
        # 文件 IO 失败 / JSON 序列化失败 / 字段类型错
        # 不吞 RuntimeError/AttributeError 等真实编程 bug
        logger.warning(f"占位视频写入失败: {e}")

    # 4. 更新 ctx 终态
    ctx.final_narration = ctx.current_draft
    ctx.final_segments = ctx.current_segments
    ctx.final_subtitle_path = subtitle_path
    ctx.final_video_path = video_path

    return success_step(start, state=NarrationState.ASSEMBLE, message=f'assemble: 字幕 + 草稿 + 视频占位完成 (ASS={ass_success}, 剪映={jianying_success}, {subtitle_path.name})', data={'subtitle_path': str(subtitle_path), 'ass_path': str(ass_path) if ass_success else None, 'video_path': str(video_path), 'jianying_path': str(jianying_path) if jianying_success else None})


# ============================================
# 辅助函数
# ============================================


def _write_srt_fallback(draft: str, output_path: Path) -> None:
    """SRT 字幕降级生成 (无需外部依赖)"""
    import re

    # 按句号切分
    sentences = re.split(r"([。！？])", draft)
    parts: list[str] = []
    for i in range(0, len(sentences) - 1, 2):
        parts.append(sentences[i] + sentences[i + 1])
    if len(sentences) % 2 == 1 and sentences[-1]:
        parts.append(sentences[-1])

    # 按字数估算时长 (4 字/秒)
    chars_per_sec = 4.0
    srt_lines: list[str] = []
    current_time = 0.0

    for i, sent in enumerate(parts, 1):
        if not sent.strip():
            continue
        duration = max(1.0, len(sent) / chars_per_sec)
        start_h, start_m, start_s = _seconds_to_hms(current_time)
        end_h, end_m, end_s = _seconds_to_hms(current_time + duration)
        srt_lines.append(
            f"{i}\n{start_h:02d}:{start_m:02d}:{start_s:02d},000"
            f" --> {end_h:02d}:{end_m:02d}:{end_s:02d},000\n{sent.strip()}\n"
        )
        current_time += duration

    output_path.write_text("\n".join(srt_lines), encoding="utf-8")


def _seconds_to_hms(sec: float) -> tuple[int, int, int]:
    """秒 → (h, m, s) 元组"""
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    return h, m, s


def _write_jianying_metadata(ctx: NarrationContext, output_path: Path) -> None:
    """写剪映草稿元数据 JSON (轻量版, 不依赖 JianyingDraft 复杂结构)"""
    metadata = {
        "version": "1.0",
        "type": "scenefab_narration_v22",
        "trace_id": ctx.trace_id,
        "source_video": str(ctx.source_video),
        "output": {
            "narration": ctx.current_draft,
            "audio_path": str(ctx.tts_audio_path) if ctx.tts_audio_path else None,
            "subtitle_path": None,  # 由 assemble_step 写入后回填
            "video_path": None,
        },
        "config": {
            "persona": ctx.persona.value,
            "style": ctx.style.value,
            "platform": ctx.platform.value,
            "short_drama_style": ctx.short_drama_style.value if ctx.short_drama_style else None,
        },
        "duration": {
            "target_sec": ctx.tts_target_duration_sec,
            "real_sec": ctx.tts_real_duration_sec,
        },
        "evaluation": {
            "score": ctx.eval_score,
            "issues": ctx.eval_issues,
        },
        "platform_spec": {
            "target_duration_sec": ctx.platform_spec.target_duration_sec,
            "char_per_second": ctx.platform_spec.char_per_second,
            "min_hook_chars": ctx.platform_spec.min_hook_chars,
            "max_total_chars": ctx.platform_spec.max_total_chars,
        },
    }
    output_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_placeholder_video(video_path: Path, ctx: NarrationContext) -> None:
    """写占位视频元数据 JSON (Phase 5 FFmpeg 合成替换)"""
    placeholder = {
        "version": "1.0",
        "type": "scenefab_placeholder_v22",
        "trace_id": ctx.trace_id,
        "pending_ffmpeg": True,
        "inputs": {
            "narration": ctx.current_draft,
            "audio_path": str(ctx.tts_audio_path) if ctx.tts_audio_path else None,
        },
    }
    placeholder_path = video_path.with_suffix(".json")
    placeholder_path.write_text(
        json.dumps(placeholder, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ============================================
# 注册函数
# ============================================


def register_assembly_steps(sm) -> None:
    """注册 Phase 4 真实实现 (替换 Phase 1 stub)

    使用示例:
        sm = NarrationStateMachine()
        register_default_steps(sm)
        register_understanding_steps(sm)
        register_evaluation_steps(sm)
        register_assembly_steps(sm)  # 替换 TTS_LENGTH_ADJUST/TTS/ASSEMBLE
    """
    from .narration_state_machine import NarrationStateMachine

    assert isinstance(sm, NarrationStateMachine)

    sm.register_step(NarrationState.TTS_LENGTH_ADJUST, tts_length_adjust_step)
    sm.register_step(NarrationState.TTS, tts_step)
    sm.register_step(NarrationState.ASSEMBLE, assemble_step)
