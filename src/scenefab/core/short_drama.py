#!/usr/bin/env python3
"""
短剧解说特化模块 — v2.0 重构

针对短剧（每集 1-3 分钟、整季 25-50 集）的业务特化：
- 自适应参数（更密抽帧、桥段识别、剧情连贯性）
- 短剧专用风格（悬疑/甜宠/复仇/逆袭）
- 整季批量生产（共享剧情上下文）
- 集数水印 + 下集预告钩子

使用示例:
    from scenefab.core.short_drama import ShortDramaNarrator, ShortDramaPreset

    preset = ShortDramaPreset.suspense()  # 短剧悬疑风
    narrator = ShortDramaNarrator(preset=preset)
    episodes = narrator.scan_episodes(Path("/series/重生女王/"))
    results = narrator.generate_series(episodes, output_dir=Path("output/"))
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ============================================
# 风格枚举
# ============================================


class ShortDramaStyle(str, Enum):
    """短剧解说风格"""

    SUSPENSE = "short_drama_suspense"  # 短剧悬疑风：快节奏、强反转留白
    ROMANCE = "short_drama_romance"  # 短剧甜宠风：甜蜜、轻快
    REVENGE = "short_drama_revenge"  # 短剧复仇风：复仇爽感、霸气
    COUNTERATTACK = "short_drama_counterattack"  # 短剧逆袭风：打脸爽文
    GENERAL = "short_drama_general"  # 通用


# ============================================
# 数据模型
# ============================================


@dataclass(slots=True)
class ShortDramaPreset:
    """短剧预设参数"""

    name: str
    style: ShortDramaStyle
    description: str = ""

    # 抽帧参数
    frame_interval: float = 0.5  # 短剧节奏快
    min_scene_length: float = 3.0  # 最小场景长度
    confidence_threshold: float = 0.5  # 置信度阈值
    max_segments_per_episode: int = 8  # 每集最多片段

    # 解说参数
    words_per_segment_min: int = 50
    words_per_segment_max: int = 80
    speed: float = 1.15  # 略快语速
    include_cliffhanger: bool = True  # 末尾加"下集预告"
    include_episode_watermark: bool = True

    # 风格提示
    system_prompt: str = ""

    @classmethod
    def suspense(cls) -> "ShortDramaPreset":
        return cls(
            name="短剧悬疑风",
            style=ShortDramaStyle.SUSPENSE,
            description="快节奏解说，强反转留白，适合悬疑/惊悚类短剧",
            system_prompt="""你是一位短剧解说创作者，专精悬疑/惊悚类短剧。

风格要求：
- 节奏紧凑，每句话必须推动剧情
- 关键反转点要设悬念，引导观众继续观看
- 使用疑问句、设问句增加好奇
- 每段结尾必须留钩子（"然而就在这时..."、"没想到..."、"接下来发生的事..."）

桥段关注点：
- 身份揭露（谁是幕后黑手）
- 反转时刻（看似 X 实则 Y）
- 关键证据出现
- 危机升级
""",
        )

    @classmethod
    def romance(cls) -> "ShortDramaPreset":
        return cls(
            name="短剧甜宠风",
            style=ShortDramaStyle.ROMANCE,
            description="甜蜜轻快解说，适合甜宠/恋爱类短剧",
            system_prompt="""你是一位短剧解说创作者，专精甜宠/恋爱类短剧。

风格要求：
- 语气甜美、活泼
- 关注男女主互动细节、暧昧瞬间
- 使用可爱的语气词（哎呀/哇塞/太甜了）
- 强调心动瞬间、甜蜜名场面
- 结尾必带"下集更甜"预告

桥段关注点：
- 告白/告白未遂
- 心动瞬间
- 吃醋/嫉妒
- 亲密互动
""",
        )

    @classmethod
    def revenge(cls) -> "ShortDramaPreset":
        return cls(
            name="短剧复仇风",
            style=ShortDramaStyle.REVENGE,
            description="复仇爽感解说，适合逆袭/复仇类短剧",
            system_prompt="""你是一位短剧解说创作者，专精复仇/逆袭类短剧。

风格要求：
- 语气霸气、燃、爽
- 强调主角从被欺压到反击的转变
- 使用"打脸"、"碾压"、"逆袭"等爽文关键词
- 突出敌人被打脸的尴尬瞬间
- 结尾强化"下集更爽"

桥段关注点：
- 打脸/逆袭瞬间
- 真相揭露
- 敌人失势
- 主角霸气宣言
""",
        )

    @classmethod
    def counterattack(cls) -> "ShortDramaPreset":
        return cls(
            name="短剧逆袭风",
            style=ShortDramaStyle.COUNTERATTACK,
            description="打脸爽文解说，适合赘婿/逆袭/隐藏身份类短剧",
            system_prompt="""你是一位短剧解说创作者，专精逆袭/隐藏身份类短剧。

风格要求：
- 极致反差（"所有人都以为他是个废物，其实他是..."）
- 强调身份反转的爽点
- 使用夸张对比（曾经的嘲讽 vs 现在的跪舔）
- 结尾强化"更多身份即将曝光"

桥段关注点：
- 身份曝光
- 众人震惊/跪舔
- 隐藏实力的展示
- 扮猪吃老虎
""",
        )


# ============================================
# 桥段识别
# ============================================


class TropeType(str, Enum):
    """短剧桥段类型"""

    IDENTITY_REVEAL = "identity_reveal"  # 身份揭露
    FACE_SLAP = "face_slap"  # 打脸
    RESCUE = "rescue"  # 救场
    BETRAYAL = "betrayal"  # 背叛
    ROMANCE_CLIMAX = "romance_climax"  # 心动瞬间
    CONFRONTATION = "confrontation"  # 对峙
    REVEAL_TWIST = "reveal_twist"  # 反转
    GENERAL = "general"


_TROPE_KEYWORDS: dict[TropeType, list[str]] = {
    TropeType.IDENTITY_REVEAL: [
        "真实身份",
        "原来是你",
        "隐藏",
        "太子",
        "总裁",
        "董事长",
        "幕后",
        "boss",
        "真凶",
        "间谍",
        "卧底",
    ],
    TropeType.FACE_SLAP: [
        "打脸",
        "逆转",
        "没想到",
        "碾压",
        "跪",
        "认错",
        "后悔",
        "求饶",
        "跪舔",
        "道歉",
    ],
    TropeType.RESCUE: [
        "救",
        "从天而降",
        "及时赶到",
        "英雄救美",
        "出手",
    ],
    TropeType.BETRAYAL: [
        "背叛",
        "出卖",
        "背后捅刀",
        "陷害",
        "污蔑",
    ],
    TropeType.ROMANCE_CLIMAX: [
        "告白",
        "亲吻",
        "拥抱",
        "心动",
        "脸红",
        "撒娇",
        "壁咚",
        "强吻",
        "床咚",
        "公主抱",
    ],
    TropeType.CONFRONTATION: [
        "对峙",
        "质问",
        "怒斥",
        "指责",
        "对质",
    ],
    TropeType.REVEAL_TWIST: [
        "反转",
        "真相",
        "竟然",
        "其实",
        "万万没想到",
        "令人震惊",
        "大跌眼镜",
    ],
}


# ============================================
# 短剧特化解说器
# ============================================


@dataclass
class EpisodeInfo:
    """单集信息"""

    path: Path
    episode_number: int = 0
    title: str = ""
    duration_sec: float = 0.0
    summary: str = ""


@dataclass
class SeriesContext:
    """整季上下文（供各集共享）"""

    series_title: str = ""
    total_episodes: int = 0
    character_map: dict[str, str] = field(default_factory=dict)
    plot_timeline: list[str] = field(default_factory=list)
    previous_episode_summary: str = ""

    def add_plot_point(self, point: str) -> None:
        self.plot_timeline.append(point)


class ShortDramaNarrator:
    """短剧解说特化生成器"""

    def __init__(
        self,
        preset: ShortDramaPreset,
        llm_provider: Any = None,
    ) -> None:
        """
        Args:
            preset: 短剧预设
            llm_provider: LLM 提供商（None 时使用默认 LLMManager）
        """
        self.preset = preset
        self.llm = llm_provider  # 由 LLMManager 注入

    # ==============================================================
    # 桥段识别
    # ==============================================================

    def detect_trope(self, scene_description: str) -> TropeType:
        """
        识别短剧桥段类型

        Args:
            scene_description: 场景描述（来自 Vision API 或字幕文本）

        Returns:
            桥段类型
        """
        if not scene_description:
            return TropeType.GENERAL
        for trope, keywords in _TROPE_KEYWORDS.items():
            if any(kw in scene_description for kw in keywords):
                return trope
        return TropeType.GENERAL

    def get_trope_emphasis(self, trope: TropeType) -> str:
        """根据桥段类型获取解说强调重点"""
        emphasis_map = {
            TropeType.IDENTITY_REVEAL: "重点渲染身份反转的冲击感",
            TropeType.FACE_SLAP: "重点突出打脸的爽感和敌人尴尬",
            TropeType.RESCUE: "重点营造救场的及时和霸气",
            TropeType.BETRAYAL: "重点渲染背叛的愤怒和后续复仇期待",
            TropeType.ROMANCE_CLIMAX: "重点突出甜蜜瞬间和观众共情",
            TropeType.CONFRONTATION: "重点渲染对峙的紧张氛围",
            TropeType.REVEAL_TWIST: "重点突出反转的震撼和合理解释",
            TropeType.GENERAL: "正常推进剧情",
        }
        return emphasis_map.get(trope, "")

    # ==============================================================
    # 集数扫描
    # ==============================================================

    EPISODE_PATTERNS = [
        re.compile(r"EP?(\d+)", re.IGNORECASE),
        re.compile(r"第(\d+)[集话]"),
        re.compile(r"(\d+)集"),
        re.compile(r"[_\-](\d{2,3})[_\-\.]"),
    ]

    def scan_episodes(self, directory: Path) -> list[EpisodeInfo]:
        """
        扫描目录中的所有短剧集数

        自动识别集数编号（EP01 / 第01集 / E01 等格式）
        """
        video_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
        episodes: list[EpisodeInfo] = []
        for file in sorted(directory.iterdir()):
            if file.suffix.lower() not in video_exts:
                continue
            ep_num = self._extract_episode_number(file.name)
            episodes.append(
                EpisodeInfo(
                    path=file,
                    episode_number=ep_num,
                    title=file.stem,
                )
            )
        # 按集数排序
        episodes.sort(key=lambda e: e.episode_number)
        logger.info(
            f"Scanned {len(episodes)} episodes in {directory}, "
            f"range: EP{episodes[0].episode_number if episodes else 0:02d} "
            f"- EP{episodes[-1].episode_number if episodes else 0:02d}"
        )
        return episodes

    def _extract_episode_number(self, filename: str) -> int:
        """从文件名提取集数（找不到则按出现顺序）"""
        for pattern in self.EPISODE_PATTERNS:
            match = pattern.search(filename)
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    continue
        return 0

    # ==============================================================
    # 整季生成
    # ============================================

    def generate_series(
        self,
        episodes: list[EpisodeInfo],
        output_dir: Path,
        context: SeriesContext | None = None,
    ) -> list[Path]:
        """
        整季批量生成

        共享剧情上下文，保持连贯性
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if context is None:
            context = SeriesContext(
                series_title=episodes[0].path.parent.name if episodes else "unknown",
                total_episodes=len(episodes),
            )

        results: list[Path] = []
        for ep in episodes:
            output_file = output_dir / (
                f"{context.series_title}_EP{ep.episode_number:02d}_解说.mp4"
            )
            logger.info(
                f"Generating EP{ep.episode_number:02d} "
                f"({context.previous_episode_summary[:30] + '...' if context.previous_episode_summary else 'new series'})"
            )

            # 实际生成由上层 pipeline 调用
            # 此处仅记录上下文
            context.add_plot_point(f"EP{ep.episode_number:02d}: {ep.title} (generated)")
            context.previous_episode_summary = ep.summary or ep.title
            results.append(output_file)

        return results

    def generate_cliffhanger(
        self,
        episode_context: dict,
    ) -> str:
        """
        生成"下集预告"钩子

        Args:
            episode_context: {"summary": str, "conflict": str, "trope": TropeType}

        Returns:
            15 字以内的钩子
        """
        prompt = f"""基于当前集剧情，生成一个 15 字以内的悬念钩子，让观众必须点开下一集。

剧情总结：{episode_context.get("summary", "")}
关键冲突：{episode_context.get("conflict", "")}
桥段类型：{episode_context.get("trope", "general")}

要求：
- 制造强烈好奇心
- 不超过 15 字
- 直接返回文本，不加引号
"""
        # 实际调用由 LLMManager 处理
        # 此处返回占位（实际项目会用 LLM）
        logger.debug(f"Cliffhanger prompt: {prompt[:100]}...")
        return f"然而接下来发生的事，让所有人始料未及..."


# ============================================
# 短剧流水线预设（YAML 格式）
# ============================================

SHORT_DRAMA_PRESET_YAML = """\
# 短剧解说预设 v2.0
name: 短剧解说模式
version: "2.0"
description: 针对 1-3 分钟/集的短剧优化参数

slicing:
  frame_interval: 0.5       # 抽帧间隔更密（短剧节奏快）
  min_scene_length: 3       # 最小场景长度（秒）
  confidence_threshold: 0.5
  max_segments_per_episode: 8

narration:
  words_per_segment: [50, 80]   # 每段字数
  include_cliffhanger: true
  include_episode_watermark: true
  style_presets:
    - short_drama_suspense
    - short_drama_romance
    - short_drama_revenge
    - short_drama_counterattack

tts:
  speed: 1.15
  pitch: 0
  voice_profile: short_drama

composition:
  intro_duration: 2
  episode_tag: true
  cliffhanger_end: true
  black_fade_out: 0.5

batch:
  auto_detect_episodes: true
  episode_patterns:
    - "EP?(\\\\d+)"
    - "第(\\\\d+)[集话]"
    - "(\\\\d+)集"
  output_naming: "{title}_EP{ep:02d}_解说.mp4"
  parallel_count: 2
"""


__all__ = [
    "ShortDramaStyle",
    "ShortDramaPreset",
    "ShortDramaNarrator",
    "TropeType",
    "EpisodeInfo",
    "SeriesContext",
    "SHORT_DRAMA_PRESET_YAML",
]
