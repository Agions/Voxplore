"""
Voxplore Video Perspective & Interleave Models
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple
from typing_extensions import TypedDict


# ─────────────────────────────────────────────────────────────
# Perspective Mapper Models
# ─────────────────────────────────────────────────────────────

class SubjectRole(Enum):
    """画面主体角色"""
    PROTAGONIST = "protagonist"     # 主角（"我"）
    SUPPORTING = "supporting"       # 配角（他/她）
    BACKGROUND = "background"       # 背景人物
    UNKNOWN = "unknown"


class EmotionalIntensity(Enum):
    """情感强度等级"""
    CALM = 0.0      # 平静
    MILD = 0.3      # 轻微
    MODERATE = 0.5  # 中等
    HIGH = 0.7      # 强烈
    PEAK = 1.0      # 高潮


@dataclass
class SubjectPosition:
    """画面中主体位置"""
    subject_id: str
    role: SubjectRole
    x_percent: float       # 0-100, 画面中心为 50
    y_percent: float       # 0-100, 画面中心为 50
    width_percent: float   # 主体宽度占比
    height_percent: float  # 主体高度占比
    gaze_direction: str    # 视线方向: "left", "right", "center", "up", "down"
    depth_layer: int       # 深度层: 0=最近, 1=中景, 2=远景


@dataclass
class ViewpointAnchor:
    """视角锚点——"我"在画面中的位置"""
    spatial_x: float       # "我"在画面的 X 位置 (0-100)
    spatial_y: float       # "我"在画面的 Y 位置 (0-100)
    spatial_depth: int     # 深度层
    emotional_tone: str    # 情感基调: "neutral", "tense", "warm", "nostalgic"
    narration_pov: str     # 叙述视角: "first", "omniscient"


@dataclass
class SceneSegment:
    """场景片段（来自 SceneAnalyzer）"""
    scene_id: str
    start_time: float
    end_time: float
    scene_type: str              # "indoor", "outdoor", "transition"
    location: str                # 地点描述
    atmosphere: str              # 氛围: "bright", "dark", "mysterious"
    subjects: List[SubjectPosition] = field(default_factory=list)
    key_objects: List[str] = field(default_factory=list)  # 关键物体
    narration_importance: float = 0.5  # 0-1, 叙事重要性


@dataclass
class KeyFrame:
    """关键帧"""
    timestamp: float
    frame_index: int
    image_path: str
    subjects: List[SubjectPosition] = field(default_factory=list)
    scene_description: str = ""


@dataclass
class PerspectiveShot:
    """视角镜头——单个视角决策"""
    shot_id: str
    start_time: float
    end_time: float
    duration: float

    # 视角信息
    viewpoint: ViewpointAnchor

    # 主体关系
    primary_subject: Optional[SubjectPosition] = None
    secondary_subjects: List[SubjectPosition] = field(default_factory=list)

    # 穿插决策
    show_original_clip: bool = True
    original_clip_weight: float = 0.5   # 0=纯解说, 1=纯原片
    interleave_mode: str = "交替"        # "原片优先", "解说优先", "交替", "纯解说"

    # 情感
    emotional_intensity: float = 0.5
    narration_emotion: str = "平静"

    # 元数据
    narration_text: str = ""
    scene_context: str = ""


# ─────────────────────────────────────────────────────────────
# Video Interleaver Models
# ─────────────────────────────────────────────────────────────

class InterleaveMode(Enum):
    """穿插模式"""
    NARRATION_PRIORITY = "narration_priority"   # 解说优先，原片点缀
    ORIGINAL_PRIORITY = "original_priority"     # 原片优先，解说为辅
    EMOTIONAL_BURST = "emotional_burst"         # 情绪高潮时切入原片
    MINIMALIST = "minimalist"                   # 纯解说，最小化原片
    CINEMATIC = "cinematic"                     # 电影感交织


class TransitionType(Enum):
    """转场类型"""
    CUT = "cut"                     # 硬切
    FADE = "fade"                  # 淡入淡出
    DISSOLVE = "dissolve"          # 叠化
    ZOOM_HIGHLIGHT = "zoom"        # 放大高亮
    BLUR_TRANSITION = "blur"       # 模糊过渡
    SUBTITLE_ONLY = "subtitle"      # 仅字幕，无画面


@dataclass
class NarrationSegment:
    """解说片段"""
    segment_id: str
    text: str
    start_time: float
    end_time: float
    duration: float
    emotion: str = "neutral"
    emphasis_words: List[str] = field(default_factory=list)  # 重音词
    pause_before: float = 0.0    # 前停顿
    pause_after: float = 0.0     # 后停顿


@dataclass
class ClipSegment:
    """原片片段"""
    clip_id: str
    source_path: str
    start_time: float      # 在原片中的起始时间
    end_time: float
    duration: float
    is_key_moment: bool = False   # 是否为关键时刻
    key_content: str = ""         # 关键内容描述


@dataclass
class InterleaveDecision:
    """穿插决策"""
    narration_segment: NarrationSegment
    clip_segment: Optional[ClipSegment]

    # 穿插时序
    show_original: bool
    original_start: Optional[float] = None
    original_end: Optional[float] = None

    # 视觉效果
    transition: TransitionType = TransitionType.CUT
    zoom_factor: float = 1.0      # 放大因子
    highlight_box: Optional[Tuple[float, float, float, float]] = None  # x,y,w,h 百分比

    # 音频
    narration_volume: float = 1.0
    original_audio_volume: float = 0.0

    # 字幕
    subtitle_text: str = ""
    subtitle_style: str = "cinematic"


@dataclass
class InterleaveTimeline:
    """穿插时间线"""
    decisions: List[InterleaveDecision]
    total_duration: float
    original_video_duration: float
    narration_duration: float

    # 统计
    original_coverage_percent: float = 0.0   # 原片展示时长占比
    narration_coverage_percent: float = 0.0   # 解说覆盖时长占比

    # 元数据
    interleave_mode: InterleaveMode = InterleaveMode.CINEMATIC
    emotion_curve: List[float] = field(default_factory=list)


@dataclass
class InterleaveContext:
    """穿插上下文"""
    target_duration: Optional[float] = None   # 目标总时长
    max_original_ratio: float = 0.6           # 原片最大占比
    min_narration_ratio: float = 0.3          # 解说最小占比
    emotion_threshold: float = 0.7             # 情绪阈值（超过则展原片）
    allow_zoom_highlight: bool = True
    allow_subtitle_only_gaps: bool = True      # 允许纯字幕间隙
