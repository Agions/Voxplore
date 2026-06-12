#!/usr/bin/env python3
"""
v2.2 Phase 2 — UNDERSTAND / STORYGRAPH / DRAFT 真实实现

把 Phase 1 的 stub step 替换为真实调用:
- understand_step   → SceneAnalyzer.analyze() + ShortDramaNarrator 桥段检测
- storygraph_step   → LongVideoUnderstanding.understand() (API key 可选)
- draft_step        → ScriptGenerator.generate() (4 类上下文注入)
- _build_narration_prompt  → 把 NarrationContext 翻译成 ScriptConfig + topic

设计原则:
- **API 不可用时优雅降级**: 没 API key 用 stub, 没 StoryGraph 用 scenes 替代
- **零破坏兼容 v2.1**: 现有 monologue_maker.generate_script 完全不动
- **复用现有模型**: SceneInfo / StoryGraph / ScriptConfig / GeneratedScript 直接复用
- **错误隔离**: 任何底层异常被捕获, 状态机主循环接到 StepResult(success=False) 转 ERROR

v2.2 决策: docs/adr/007-narration-state-machine.md
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from .narration_context import (
    Bridge,
    BridgeType,
    NarrationContext,
    NarrationStyle,
)
from .narration_state_machine import NarrationState, StepResult

if TYPE_CHECKING:
    from scenefab.services.ai.script_generator.script_generator import ScriptGenerator
    from scenefab.services.ai.script_models import ScriptConfig

logger = logging.getLogger(__name__)


# ============================================
# NarrationStyle ↔ ScriptStyle 映射
# ============================================


# v2.2 NarrationStyle → v2.1 ScriptStyle + VoiceTone
# 复用 scenefab.services.ai.script_models 已有枚举
_NARRATION_TO_SCRIPT_STYLE: dict[NarrationStyle, str] = {
    NarrationStyle.SUSPENSE: "monologue",  # 悬疑 = 第一人称独白
    NarrationStyle.ROMANCE: "monologue",  # 甜宠 = 独白
    NarrationStyle.REVENGE: "commentary",  # 复仇 = 客观解说
    NarrationStyle.UNDERDOG: "commentary",  # 逆袭 = 客观解说
    NarrationStyle.COMEDY: "viral",  # 吐槽 = 爆款
    NarrationStyle.LITERARY: "narration",  # 文艺 = 旁白
    NarrationStyle.NEUTRAL: "commentary",  # 中性 = 解说
}

_NARRATION_TO_TONE: dict[NarrationStyle, str] = {
    NarrationStyle.SUSPENSE: "mysterious",
    NarrationStyle.ROMANCE: "emotional",
    NarrationStyle.REVENGE: "excited",
    NarrationStyle.UNDERDOG: "excited",
    NarrationStyle.COMEDY: "humorous",
    NarrationStyle.LITERARY: "calm",
    NarrationStyle.NEUTRAL: "neutral",
}


# ============================================
# UNDERSTAND — 场景识别 + 桥段检测
# ============================================


def understand_step(ctx: NarrationContext) -> StepResult:
    """② UNDERSTAND: 视觉模型理解场景 + 桥段检测

    真实实现 (Phase 2):
    1. 调用 scenefab.services.ai.scene_analyzer.SceneAnalyzer.analyze()
    2. 填充 ctx.scenes (list[SceneInfo])
    3. 调用 scenefab.core.short_drama.ShortDramaNarrator.detect_trope()
    4. 填充 ctx.bridges (list[Bridge])

    降级: SceneAnalyzer 不可用 → 用 stub (从视频时长均匀分段)
    """
    start = time.time()
    video_path = str(ctx.source_video)

    # 1. 场景识别
    try:
        from scenefab.services.ai.scene_analyzer import SceneAnalyzer

        analyzer = SceneAnalyzer()
        scenes = analyzer.analyze(video_path)
        ctx.scenes = scenes
        logger.info(f"[{ctx.trace_id[:8]}] 场景识别: {len(scenes)} 个场景")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[{ctx.trace_id[:8]}] SceneAnalyzer 失败, 降级 stub: {e}")
        ctx.scenes = _stub_scenes(ctx)

    # 2. 桥段检测 (仅短剧模式启用)
    if ctx.short_drama_style is not None:
        try:
            from scenefab.core.short_drama import ShortDramaNarrator, ShortDramaPreset

            # 根据 ctx.short_drama_style 选择 preset
            preset = ShortDramaPreset.suspense()  # 默认悬疑
            if ctx.short_drama_style.value == "short_drama_romance":
                preset = ShortDramaPreset.romance()
            elif ctx.short_drama_style.value == "short_drama_revenge":
                preset = ShortDramaPreset.revenge()
            elif ctx.short_drama_style.value == "short_drama_counterattack":
                preset = ShortDramaPreset.counterattack()

            narrator = ShortDramaNarrator(preset=preset)
            ctx.bridges = _detect_bridges(narrator, ctx.scenes)
            logger.info(
                f"[{ctx.trace_id[:8]}] 桥段检测: {len(ctx.bridges)} 个桥段"
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[{ctx.trace_id[:8]}] 桥段检测失败, 跳过: {e}")
            ctx.bridges = []

    duration_ms = (time.time() - start) * 1000
    return StepResult(
        success=True,
        state=NarrationState.UNDERSTAND,
        duration_ms=duration_ms,
        message=(
            f"understand: {len(ctx.scenes)} 场景, "
            f"{len(ctx.bridges)} 桥段"
        ),
        data={
            "scenes": len(ctx.scenes),
            "bridges": len(ctx.bridges),
        },
    )


# ============================================
# STORYGRAPH — 长视频剧情图谱
# ============================================


def storygraph_step(ctx: NarrationContext) -> StepResult:
    """③ STORYGRAPH: 长视频剧情图谱 (LongVideoUnderstanding)

    真实实现 (Phase 2):
    1. 判断视频时长 (短片 < 10min 跳过 LongVideoUnderstanding)
    2. 调用 scenefab.services.video_understanding.LongVideoUnderstanding.understand()
    3. 填充 ctx.story_graph

    降级: API key 未配置 或 长视频理解器不可用 → 用空 StoryGraph + scenes 摘要
    """
    start = time.time()
    video_path = str(ctx.source_video)
    video_duration = _probe_duration(video_path)

    # 短视频 (< 10 分钟) 跳过 LongVideoUnderstanding, 用 scenes 拼一份简化 story_graph
    if video_duration < 600:
        ctx.story_graph = _build_minimal_story_graph(ctx)
        duration_ms = (time.time() - start) * 1000
        return StepResult(
            success=True,
            state=NarrationState.STORYGRAPH,
            duration_ms=duration_ms,
            message=(
                f"storygraph: 短视频 ({video_duration:.0f}s), "
                f"跳过 LongVideoUnderstanding, 用 scenes 拼装"
            ),
            data={"duration_sec": video_duration, "skipped_long": True},
        )

    # 长视频: 尝试 LongVideoUnderstanding
    try:
        from scenefab.services.video_understanding import LongVideoUnderstanding
        from scenefab.services.video_understanding.models import UnderstandingLevel

        understander = LongVideoUnderstanding()
        result = understander.understand(
            video_path=video_path,
            level=UnderstandingLevel.FLASH,  # Phase 2 默认 FLASH (省 token)
        )
        ctx.story_graph = result.story_graph
        duration_ms = (time.time() - start) * 1000
        return StepResult(
            success=True,
            state=NarrationState.STORYGRAPH,
            duration_ms=duration_ms,
            message=(
                f"storygraph: 长视频 ({video_duration:.0f}s), "
                f"LongVideoUnderstanding 完成"
            ),
            data={
                "duration_sec": video_duration,
                "characters": len(result.story_graph.characters),
                "plot_events": len(result.story_graph.plot_events),
            },
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(
            f"[{ctx.trace_id[:8]}] LongVideoUnderstanding 失败, 降级: {e}"
        )
        ctx.story_graph = _build_minimal_story_graph(ctx)
        duration_ms = (time.time() - start) * 1000
        return StepResult(
            success=True,
            state=NarrationState.STORYGRAPH,
            duration_ms=duration_ms,
            message=(
                f"storygraph: 长视频 ({video_duration:.0f}s) 但理解失败, 降级"
            ),
            data={"duration_sec": video_duration, "fallback": True},
        )


# ============================================
# DRAFT — 4 类上下文 + LLM 生成
# ============================================


def draft_step(ctx: NarrationContext) -> StepResult:
    """④ DRAFT: 把 4 类上下文注入 ScriptGenerator, 生成解说稿

    真实实现 (Phase 2):
    1. _build_narration_prompt(ctx) → ScriptConfig + topic
    2. ScriptGenerator.generate(topic, config)
    3. 填充 ctx.current_draft + ctx.current_segments

    降级: ScriptGenerator 不可用 / 无 LLM key → 用模板生成 stub 文案
    """
    start = time.time()
    ctx.reset_draft()  # 准备新一轮 draft (清 eval 状态, attempts++)

    # 1. 组装 4 类上下文
    try:
        topic, config = _build_narration_prompt(ctx)
    except Exception as e:  # noqa: BLE001
        return StepResult(
            success=False,
            state=NarrationState.DRAFT,
            error=f"组装 4 类上下文失败: {e}",
        )

    # 2. 调用 LLM
    try:
        from scenefab.services.ai.script_generator import ScriptGenerator

        generator: ScriptGenerator = ScriptGenerator()
        script = generator.generate(topic=topic, config=config)
        ctx.current_draft = script.content
        ctx.current_segments = [
            {
                "text": seg.content,
                "duration": seg.duration,
                "start_time": seg.start_time,
            }
            for seg in script.segments
        ]
    except Exception as e:  # noqa: BLE001
        logger.warning(
            f"[{ctx.trace_id[:8]}] ScriptGenerator 失败, 降级模板: {e}"
        )
        ctx.current_draft = _stub_draft(ctx, topic)
        ctx.current_segments = _stub_segments(ctx, ctx.current_draft)

    duration_ms = (time.time() - start) * 1000
    return StepResult(
        success=True,
        state=NarrationState.DRAFT,
        duration_ms=duration_ms,
        message=(
            f"draft 完成 (attempt={ctx.draft_attempts + 1}, "
            f"chars={len(ctx.current_draft)})"
        ),
        data={
            "chars": len(ctx.current_draft),
            "segments": len(ctx.current_segments),
        },
    )


# ============================================
# 辅助函数
# ============================================


def _build_narration_prompt(
    ctx: NarrationContext,
) -> tuple[str, ScriptConfig]:
    """把 NarrationContext 翻译成 ScriptGenerator 友好的 (topic, ScriptConfig)

    4 类上下文映射:
    ① 指令上下文 (persona/style/platform) → ScriptConfig.style/tone/target_duration
    ② 数据上下文 (story_graph/scenes/bridges) → topic 主体
    ③ 历史上下文 (history) → topic 末尾"前情提要"段
    ④ 工具上下文 (few_shots/bridge_templates) → ScriptConfig.keywords 注入
    """
    from scenefab.services.ai.script_models import (
        ScriptConfig,
        ScriptStyle,
        VoiceTone,
    )

    # —— ① 指令上下文 ——
    script_style_str = _NARRATION_TO_SCRIPT_STYLE.get(ctx.style, "commentary")
    tone_str = _NARRATION_TO_TONE.get(ctx.style, "neutral")

    style_enum = ScriptStyle(script_style_str)
    tone_enum = VoiceTone(tone_str)

    # 平台规格 → 目标时长
    platform_spec = ctx.platform_spec
    target_duration = platform_spec.target_duration_sec
    # 抖音 4.5字/秒, B站 4.0字/秒, 已在 platform_spec 里
    words_per_second = platform_spec.char_per_second

    # —— ② 数据上下文 → topic 主体 ——
    topic_parts: list[str] = []

    # 剧情梗概
    if ctx.story_graph and ctx.story_graph.synopsis:
        topic_parts.append(f"【剧情】{ctx.story_graph.synopsis}")

    # 角色 (最多 3 个)
    if ctx.story_graph and ctx.story_graph.characters:
        char_descs = [
            f"{c.name}: {c.description[:30]}"
            for c in ctx.story_graph.characters[:3]
        ]
        topic_parts.append("【角色】" + "; ".join(char_descs))

    # 场景摘要 (最多 5 个)
    if ctx.scenes:
        scene_descs = [
            f"场景{s.index + 1}: {s.description[:40] or s.type.value}"
            for s in ctx.scenes[:5]
        ]
        topic_parts.append("【场景】" + " | ".join(scene_descs))

    # 桥段 (短剧特化)
    if ctx.bridges:
        bridge_strs = [b.bridge_type.value for b in ctx.bridges[:5]]
        topic_parts.append(f"【桥段】触发: {', '.join(bridge_strs)}")

    # —— ③ 历史上下文 → 前情提要 ——
    if ctx.history:
        prev_chars = set()
        for h in ctx.history[-3:]:  # 最近 3 段
            prev_chars.update(h.characters_mentioned)
        if prev_chars:
            topic_parts.append(
                f"【前情已提角色】{', '.join(list(prev_chars)[:5])}"
            )

    # —— ④ 工具上下文 → keywords ——
    keywords: list[str] = []
    # 桥段模板里高频词注入
    for bt, template in ctx.bridge_templates.items():
        if isinstance(bt, BridgeType) and template:
            # 提取模板里的中文词
            for word in ["冲突", "反转", "打脸", "心动", "背叛", "对峙"]:
                if word in template and word not in keywords:
                    keywords.append(word)

    # 组装 topic
    topic = "\n".join(topic_parts) if topic_parts else "通用影视解说"

    # 组装 ScriptConfig
    config = ScriptConfig(
        style=style_enum,
        tone=tone_enum,
        target_duration=target_duration,
        words_per_second=words_per_second,
        language="zh-CN",
        include_hook=True,
        keywords=keywords[:5],  # 最多 5 个关键词
    )

    return topic, config


# ============================================
# Stub 降级实现 (无 AI 能力时)
# ============================================


def _stub_scenes(ctx: NarrationContext) -> list:
    """场景识别降级: 按 30s 均匀分段"""
    from scenefab.services.ai.scene_models import SceneInfo, SceneType

    duration = _probe_duration(str(ctx.source_video))
    if duration <= 0:
        return []

    # 30s 一段, 最多 10 段
    seg_len = min(30.0, max(10.0, duration / 10))
    n = max(1, int(duration / seg_len))

    scenes: list[SceneInfo] = []
    for i in range(n):
        s = SceneInfo(
            index=i,
            start=i * seg_len,
            end=min((i + 1) * seg_len, duration),
            duration=seg_len,
            type=SceneType.UNKNOWN,
            description=f"stub scene {i + 1}",
        )
        scenes.append(s)
    return scenes


def _detect_bridges(narrator, scenes: list) -> list[Bridge]:
    """桥段检测: 调 ShortDramaNarrator.detect_trope()"""
    bridges: list[Bridge] = []
    for scene in scenes:
        if not scene.description:
            continue
        try:
            trope = narrator.detect_trope(scene.description)
            if trope and trope.value != "general":
                # TropeType → BridgeType 映射
                bridge_type = _trope_to_bridge(trope)
                if bridge_type is not None:
                    bridges.append(
                        Bridge(
                            bridge_type=bridge_type,
                            scene_index=scene.index,
                            confidence=0.7,  # 默认置信度
                            description=scene.description[:50],
                        )
                    )
        except Exception:  # noqa: BLE001
            continue
    return bridges


def _trope_to_bridge(trope) -> BridgeType | None:
    """TropeType → BridgeType 映射 (v2.2 状态机 vs v2.0 short_drama)"""
    from scenefab.core.short_drama import TropeType

    mapping = {
        TropeType.IDENTITY_REVEAL: BridgeType.IDENTITY_REVEAL,
        TropeType.FACE_SLAP: BridgeType.SLAP_FACE,
        TropeType.RESCUE: BridgeType.RESCUE,
        TropeType.BETRAYAL: BridgeType.BETRAYAL,
        TropeType.ROMANCE_CLIMAX: BridgeType.HEART_FLUTTER,
        TropeType.CONFRONTATION: BridgeType.CONFRONTATION,
        TropeType.REVEAL_TWIST: BridgeType.PLOT_TWIST,
    }
    return mapping.get(trope)


def _probe_duration(video_path: str) -> float:
    """探测视频时长 (ffprobe), 失败返回 0"""
    try:
        import json
        import subprocess

        out = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                video_path,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode == 0:
            data = json.loads(out.stdout)
            return float(data.get("format", {}).get("duration", 0))
    except Exception:  # noqa: BLE001
        pass
    return 0.0


def _build_minimal_story_graph(ctx: NarrationContext):
    """短视频 / 长视频理解失败时, 用 scenes 拼一份简化 StoryGraph"""
    from scenefab.services.video_understanding.models import (
        Character,
        PlotEvent,
        StoryGraph,
    )

    title = ctx.source_video.stem
    synopsis_parts = [f"基于 {len(ctx.scenes)} 个场景的解说"]
    if ctx.bridges:
        synopsis_parts.append(
            f"含 {len(ctx.bridges)} 个桥段"
        )
    synopsis = "; ".join(synopsis_parts)

    characters: list[Character] = []
    plot_events: list[PlotEvent] = []

    for i, scene in enumerate(ctx.scenes[:5]):
        plot_events.append(
            PlotEvent(
                event_id=f"evt_{i}",
                description=scene.description or f"场景 {i + 1}",
                timestamp=scene.start,
                event_type="development",
                importance=0.5,
            )
        )

    return StoryGraph(
        title=title,
        genre="unknown",
        synopsis=synopsis,
        characters=characters,
        plot_events=plot_events,
    )


def _stub_draft(ctx: NarrationContext, topic: str) -> str:
    """LLM 不可用时, 模板生成 stub 解说稿"""
    style_emoji = {
        NarrationStyle.SUSPENSE: "🔍",
        NarrationStyle.ROMANCE: "💕",
        NarrationStyle.REVENGE: "⚔️",
        NarrationStyle.UNDERDOG: "🔥",
        NarrationStyle.COMEDY: "😄",
        NarrationStyle.LITERARY: "📖",
        NarrationStyle.NEUTRAL: "🎬",
    }
    emoji = style_emoji.get(ctx.style, "🎬")

    target_chars = int(ctx.platform_spec.char_per_second * ctx.platform_spec.target_duration_sec)

    draft = f"""{emoji} 【Stub v2.2 Phase 2】{ctx.style.value} 风格, {ctx.platform.value} 平台。

【开场钩子】(第 {ctx.draft_attempts + 1} 次草稿)
你以为这只是一段普通的视频? 错了, 接下来 30 秒, 我将带你进入一个完全不同的世界。

【主体内容】
{topic[:200]}

【结尾留白】
想知道接下来发生了什么? 关注我, 下集更精彩!

(注: 这是 Phase 2 stub 版本, 真实文案需 ScriptGenerator + LLM 调用, 当前字符数 ≈ {target_chars})"""

    # 截断到目标字数
    if len(draft) > target_chars:
        draft = draft[:target_chars]
    return draft


def _stub_segments(ctx: NarrationContext, draft: str) -> list[dict]:
    """stub 段落切分: 按句号切分, 每段 5s"""
    import re

    sentences = re.split(r"[。！？]", draft)
    sentences = [s.strip() + "。" for s in sentences if s.strip()]
    if not sentences:
        sentences = [draft]

    return [
        {
            "text": s,
            "duration": max(3.0, len(s) / ctx.platform_spec.char_per_second),
            "start_time": i * 5.0,
        }
        for i, s in enumerate(sentences)
    ]


# ============================================
# 注册函数
# ============================================


def register_phase2_steps(sm) -> None:
    """注册 Phase 2 真实实现 (替换 Phase 1 stub)

    使用示例:
        sm = NarrationStateMachine()
        register_phase2_steps(sm)  # 替换 stub
    """
    from .narration_state_machine import NarrationStateMachine

    assert isinstance(sm, NarrationStateMachine)

    sm.register_step(NarrationState.UNDERSTAND, understand_step)
    sm.register_step(NarrationState.STORYGRAPH, storygraph_step)
    sm.register_step(NarrationState.DRAFT, draft_step)
