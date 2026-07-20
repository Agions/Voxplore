#!/usr/bin/env python3
"""
v2.2 解说生成上下文 — 4 类上下文 (Context Engineering)

封装单次解说生成任务所需的全部上下文，遵循 2025 LLM 应用最佳实践:

    ① 指令上下文 (persona / style / platform) — 人设 + 风格 + 平台
    ② 数据上下文 (story_graph / scenes / bridges) — 剧情 + 场景 + 桥段
    ③ 历史上下文 (history_segments) — 前文已说, 防止重复
    ④ 工具上下文 (few_shots / bridge_templates) — 范例 + 桥段模板

设计原则:
- dataclass(slots=True) 零开销
- 与现有 services.video_understanding.models.StoryGraph 复用
- 与 services.ai.scene_models.SceneInfo 复用
- 与 pipeline.short_drama.ShortDramaNarrator.detect_bridges() 复用
- 不引入新依赖
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

# 复用现有模型, 避免重复定义
from scenefab.pipeline.short_drama import ShortDramaStyle

if TYPE_CHECKING:
    from scenefab.services.ai.scene_models import SceneInfo
    from scenefab.services.video_understanding.models import StoryGraph

# ============================================
# ① 指令上下文 — 人设 / 风格 / 平台
# ============================================


class Persona(str, Enum):
    """解说人设 (适用于第一人称独白)"""

    FILM_CRITIC = "film_critic"  # 影评人
    STORY_TELLER = "story_teller"  # 说书人
    SHORT_DRAMA_OBSERVER = "short_drama_observer"  # 短剧观察员
    DOCUMENTARY_HOST = "documentary_host"  # 纪录片主持人
    KNOWLEDGE_SHARER = "knowledge_sharer"  # 知识科普


class Platform(str, Enum):
    """目标平台 — 影响字数/语速"""

    DOUYIN = "douyin"  # 抖音: 30-60s, 1.2-1.5 倍速, 强 Hook
    BILIBILI = "bilibili"  # B 站: 60-180s, 0.9-1.1 倍速, 中等信息密度
    XIAOHONGSHU = "xiaohongshu"  # 小红书: 30-60s, 1.0 倍速, 精致
    YOUTUBE = "youtube"  # YouTube: 120-300s, 0.95 倍速, 信息密度高
    TIKTOK = "tiktok"  # TikTok: 15-60s, 1.3 倍速, 极致 Hook
    KUAISHOU = "kuaishou"  # 快手: 30-90s, 1.1 倍速, 接地气


class ProductionStyle(str, Enum):
    """v2.2 状态机解说制作风格 (Production Style)

    用于 NarrationStateMachine 的解说生成风格选择，决定脚本语气与叙事策略。

    注意: 此枚举与 ``scenefab.models.narration.NarrationStyle`` 是两个不同的枚举:
    - ``models.narration.NarrationStyle`` — 通用解说风格 (HEALING/MYSTERIOUS/…)，用于 VideoProject。
    - ``ProductionStyle`` (本枚举) — v2.2 状态机制作风格 (SUSPENSE/ROMANCE/…)，用于解说流水线。
    """

    SUSPENSE = "suspense"  # 悬疑 (留白 + 反转 + 钩子)
    ROMANCE = "romance"  # 甜宠 (甜蜜 + 轻快)
    REVENGE = "revenge"  # 复仇 (爽感 + 霸气)
    UNDERDOG = "underdog"  # 逆袭 (热血 + 励志)
    COMEDY = "comedy"  # 吐槽 (调侃 + 反差)
    LITERARY = "literary"  # 文艺 (文学化 + 慢节奏)
    NEUTRAL = "neutral"  # 中性解说


@dataclass(slots=True)
class PlatformSpec:
    """平台规格约束 (字数/语速/时长)"""

    target_duration_sec: float  # 目标时长
    char_per_second: float  # 语速 (字/秒)
    min_hook_chars: int  # Hook 最少字符数
    max_total_chars: int  # 单集最大字符数


# 平台默认规格 (v2.2 初始值, 可被用户配置覆盖)
PLATFORM_SPECS: dict[Platform, PlatformSpec] = {
    Platform.DOUYIN: PlatformSpec(
        target_duration_sec=45.0,
        char_per_second=4.5,
        min_hook_chars=20,
        max_total_chars=200,
    ),
    Platform.BILIBILI: PlatformSpec(
        target_duration_sec=120.0,
        char_per_second=4.0,
        min_hook_chars=30,
        max_total_chars=480,
    ),
    Platform.XIAOHONGSHU: PlatformSpec(
        target_duration_sec=45.0,
        char_per_second=4.0,
        min_hook_chars=20,
        max_total_chars=180,
    ),
    Platform.YOUTUBE: PlatformSpec(
        target_duration_sec=180.0,
        char_per_second=3.8,
        min_hook_chars=40,
        max_total_chars=680,
    ),
    Platform.TIKTOK: PlatformSpec(
        target_duration_sec=30.0,
        char_per_second=4.8,
        min_hook_chars=15,
        max_total_chars=145,
    ),
    Platform.KUAISHOU: PlatformSpec(
        target_duration_sec=60.0,
        char_per_second=4.2,
        min_hook_chars=20,
        max_total_chars=250,
    ),
}


# ============================================
# ② 数据上下文 — 桥段
# ============================================


class BridgeType(str, Enum):
    """短剧 7 大桥段 (与 short_drama.TropeType 对齐, 简化为 v2.2 子集)"""

    IDENTITY_REVEAL = "identity_reveal"  # 身份揭露
    SLAP_FACE = "slap_face"  # 打脸
    RESCUE = "rescue"  # 救场
    BETRAYAL = "betrayal"  # 背叛
    HEART_FLUTTER = "heart_flutter"  # 心动
    CONFRONTATION = "confrontation"  # 对峙
    PLOT_TWIST = "plot_twist"  # 反转


@dataclass(slots=True)
class Bridge:
    """桥段识别结果 (短剧 7 桥段之一)"""

    bridge_type: BridgeType
    scene_index: int  # 哪个 scene 触发
    confidence: float  # 0-1
    description: str = ""  # 桥段内容描述


@dataclass(slots=True)
class FewShot:
    """Few-shot 范例 (用于 prompt 风格注入)"""

    scene_desc: str  # 场景描述
    narration: str  # 对应解说稿
    style: ProductionStyle = ProductionStyle.NEUTRAL


# ============================================
# ③ 历史上下文
# ============================================


@dataclass(slots=True)
class HistorySegment:
    """历史解说片段 (用于防重复)"""

    scene_index: int
    characters_mentioned: list[str] = field(default_factory=list)  # 已提角色
    plot_points_told: list[str] = field(default_factory=list)  # 已说剧情点
    bridges_used: list[BridgeType] = field(default_factory=list)  # 已用桥段


# ============================================
# ④ 整合上下文
# ============================================


@dataclass(slots=True)
class NarrationContext:
    """v2.2 解说生成上下文 (4 类上下文整合)

    使用示例:
        ctx = NarrationContext(
            source_video=Path("episode_01.mp4"),
            persona=Persona.SHORT_DRAMA_OBSERVER,
            style=ProductionStyle.REVENGE,
            platform=Platform.DOUYIN,
        )
        ctx.story_graph = await long_video_understander.understand(...)
        ctx.scenes = scene_analyzer.analyze(source_video)
        ctx.bridges = detect_bridges(ctx.scenes)
    """

    # —— 输入源 ——
    source_video: Path
    output_dir: Path
    trace_id: str = field(default_factory=lambda: __import__("uuid").uuid4().hex)

    # —— ① 指令上下文 ——
    persona: Persona = Persona.STORY_TELLER
    style: ProductionStyle = ProductionStyle.NEUTRAL
    platform: Platform = Platform.BILIBILI
    short_drama_style: ShortDramaStyle | None = None  # 短剧联动 (v2.2 新增)
    content_tags: list[str] = field(default_factory=list)  # 题材/爽点标签
    relationship_notes: list[str] = field(default_factory=list)  # 人物关系
    episode_index: int | None = None  # 连续短剧集数
    previous_episode_summary: str = ""  # 上一集/前情摘要
    next_hook_hint: str = ""  # 下一集钩子提示

    # —— ② 数据上下文 (由 UNDERSTAND/STORYGRAPH 状态填充) ——
    story_graph: StoryGraph = field(
        default_factory=lambda: __import__(
            "scenefab.services.video_understanding.models", fromlist=["StoryGraph"]
        ).StoryGraph()
    )
    scenes: list[SceneInfo] = field(default_factory=list)
    bridges: list[Bridge] = field(default_factory=list)

    # —— ③ 历史上下文 (整季/整片用, 单集可空) ——
    history: list[HistorySegment] = field(default_factory=list)

    # —— ④ 工具上下文 (Few-shot + 桥段模板) ——
    few_shots: list[FewShot] = field(default_factory=list)
    bridge_templates: dict[BridgeType, str] = field(default_factory=dict)

    # —— 状态机内部状态 (DRAFT/EVALUATE 状态读写) ——
    current_draft: str = ""
    current_segments: list[dict[str, Any]] = field(default_factory=list)
    eval_score: float = 0.0
    eval_issues: list[str] = field(default_factory=list)
    eval_suggestion: str = ""
    draft_attempts: int = 0  # DRAFT 重试次数 (上限 2)

    # —— TTS_LENGTH_ADJUST 状态写入 ——
    tts_real_duration_sec: float = 0.0
    tts_target_duration_sec: float = 0.0
    tts_audio_path: Path | None = None

    # —— 最终产物 (TTS/ASSEMBLE 后填充) ——
    final_narration: str = ""
    final_segments: list[dict[str, Any]] = field(default_factory=list)
    final_audio_path: Path | None = None
    final_subtitle_path: Path | None = None
    final_video_path: Path | None = None

    # ============================================================
    # 派生属性
    # ============================================================

    @property
    def platform_spec(self) -> PlatformSpec:
        """当前平台规格"""
        return PLATFORM_SPECS[self.platform]

    @property
    def max_attempts_reached(self) -> bool:
        """DRAFT 是否达到默认最大重试次数 (2 次)

        注: 实际限制值由 NarrationStateMachine.config.max_draft_attempts 控制。
        需要自定义阈值时使用 is_max_attempts_reached(max_attempts)。
        """
        return self.draft_attempts >= 2

    def is_max_attempts_reached(self, max_attempts: int) -> bool:
        """DRAFT 是否达到 max_attempts 次重试"""
        return self.draft_attempts >= max_attempts

    def reset_draft(self) -> None:
        """新一轮 DRAFT 前重置"""
        self.current_draft = ""
        self.current_segments = []
        self.eval_score = 0.0
        self.eval_issues = []
        self.eval_suggestion = ""
        self.draft_attempts += 1

    def add_history(self, segment: HistorySegment) -> None:
        """追加历史片段"""
        self.history.append(segment)
