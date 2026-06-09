"""
SceneFab 封面生成数据模型

包含高光帧、封面文案、视频元数据和生成结果等数据结构。
"""

from dataclasses import dataclass, field


@dataclass
class HighlightFrame:
    """高光帧"""

    timestamp: float  # 时间戳（秒）
    frame_path: str = ""  # 帧图片路径
    visual_score: float = 0.0  # 视觉显著性分数 0.0-1.0
    emotion_score: float = 0.0  # 情感分数 0.0-1.0
    combined_score: float = 0.0  # 综合分数 0.0-1.0
    description: str = ""  # 帧描述


@dataclass
class CoverText:
    """封面文案"""

    title: str  # 标题
    subtitle: str = ""  # 副标题
    hook: str = ""  # 钩子文案
    keywords: list[str] = field(default_factory=list)  # 关键词


@dataclass
class VideoMetadata:
    """视频元数据"""

    title: str
    description: str
    tags: list[str] = field(default_factory=list)
    category: str = ""
    language: str = "zh-CN"
    thumbnail_path: str = ""  # 封面图片路径
    duration: float = 0.0  # 视频时长（秒）


@dataclass
class CoverGenerationResult:
    """封面生成结果"""

    highlight_frames: list[HighlightFrame] = field(default_factory=list)
    selected_cover: HighlightFrame | None = None
    cover_texts: list[CoverText] = field(default_factory=list)
    metadata: VideoMetadata | None = None
    generation_time: str = ""
    generator_version: str = "1.0.0"
