"""
工作流数据模型

类型安全的 Pydantic v2 模型，替代原有的 dataclass。
"""
from typing import Optional, List, Callable

from pydantic import BaseModel, Field

from .enums import WorkflowStep, WorkflowStatus, CreationMode, ExportFormat


# ---------------------------------------------------------------------------
# 内部子类型（TypedDict 风格，保留 dict 接口供序列化兼容）
# ---------------------------------------------------------------------------


class SceneInfo(BaseModel):
    """场景信息（来自视频分析）"""
    index: int = Field(ge=0, description="场景序号")
    start: float = Field(ge=0, description="开始时间（秒）")
    end: float = Field(ge=0, description="结束时间（秒）")
    duration: float = Field(ge=0, description="持续时长（秒）")
    type: str = Field(default="unknown", description="场景类型标签")
    description: str = Field(default="", description="场景描述")
    keyframe_path: str = Field(default="", description="关键帧图片路径")
    avg_brightness: float = Field(default=0.0, ge=0, le=1, description="平均亮度")
    motion_level: float = Field(default=0.0, ge=0, le=1, description="运动程度")
    audio_level: float = Field(default=0.0, ge=0, description="音频音量")
    suitability_score: float = Field(default=0.0, ge=0, le=100, description="适用性评分")


class EmotionInfo(BaseModel):
    """情感片段信息（来自语音/视觉分析）"""
    start: float = Field(ge=0, description="开始时间（秒）")
    end: float = Field(ge=0, description="结束时间（秒）")
    label: str = Field(default="neutral", description="情感标签")
    score: float = Field(default=0.0, ge=0, le=1, description="置信度")


class ScriptSegmentInfo(BaseModel):
    """文案片段信息"""
    content: str = Field(default="", description="文案内容")
    start_time: float = Field(default=0.0, ge=0, description="开始时间（秒）")
    duration: float = Field(default=0.0, ge=0, description="持续时间（秒）")
    scene_hint: str = Field(default="", description="画面提示")
    emotion: str = Field(default="neutral", description="情感标签")


class VideoTrackClip(BaseModel):
    """视频轨道片段"""
    id: str = Field(default="", description="片段ID")
    start: float = Field(ge=0, description="开始时间（秒）")
    end: float = Field(ge=0, description="结束时间（秒）")
    source: str = Field(default="", description="素材路径")


class AudioTrackClip(BaseModel):
    """音频轨道片段"""
    id: str = Field(default="", description="片段ID")
    start: float = Field(ge=0, description="开始时间（秒）")
    end: float = Field(ge=0, description="结束时间（秒）")
    source: str = Field(default="", description="素材路径")


class SubtitleTrackClip(BaseModel):
    """字幕轨道片段"""
    id: str = Field(default="", description="片段ID")
    start: float = Field(ge=0, description="开始时间（秒）")
    end: float = Field(ge=0, description="结束时间（秒）")
    text: str = Field(default="", description="字幕文本")


class VoiceoverSegment(BaseModel):
    """配音片段"""
    content: str = Field(default="", description="配音文案")
    start_time: float = Field(default=0.0, ge=0, description="开始时间（秒）")
    duration: float = Field(default=0.0, ge=0, description="持续时间（秒）")
    emotion: str = Field(default="neutral", description="情感标签")


# ---------------------------------------------------------------------------
# 主模型（Pydantic BaseModel）
# ---------------------------------------------------------------------------


class VideoSource(BaseModel):
    """视频素材源"""
    id: str = Field(default="", description="素材唯一ID")
    path: str = Field(default="", min_length=1, description="文件路径")
    name: str = Field(default="", description="显示名称")
    duration: float = Field(default=0.0, ge=0, description="时长（秒）")
    width: int = Field(default=0, gt=0, description="宽度（像素）")
    height: int = Field(default=0, gt=0, description="高度（像素）")
    fps: float = Field(default=0.0, ge=0, description="帧率")
    size: int = Field(default=0, ge=0, description="文件大小（字节）")


class AnalysisResult(BaseModel):
    """视频分析结果"""
    scenes: List[SceneInfo] = Field(default_factory=list, description="场景列表")
    characters: List[str] = Field(default_factory=list, description="识别的人物列表")
    emotions: List[EmotionInfo] = Field(default_factory=list, description="情感片段列表")
    summary: str = Field(default="", description="分析摘要")
    tags: List[str] = Field(default_factory=list, description="标签列表")


class ScriptData(BaseModel):
    """脚本数据"""
    id: str = Field(default="", description="脚本ID")
    title: str = Field(default="", description="脚本标题")
    content: str = Field(default="", description="完整文案")
    segments: List[ScriptSegmentInfo] = Field(default_factory=list, description="分段文案")
    word_count: int = Field(default=0, ge=0, description="总字数")
    estimated_duration: float = Field(default=0.0, ge=0, description="预估时长（秒）")
    style: str = Field(default="", description="文风/风格")
    model_used: str = Field(default="", description="使用的模型")


class TimelineData(BaseModel):
    """时间线数据"""
    video_track: List[VideoTrackClip] = Field(default_factory=list, description="视频轨道")
    audio_track: List[AudioTrackClip] = Field(default_factory=list, description="音频轨道")
    subtitle_track: List[SubtitleTrackClip] = Field(default_factory=list, description="字幕轨道")
    total_duration: float = Field(default=0.0, ge=0, description="总时长（秒）")


class VoiceoverData(BaseModel):
    """配音数据"""
    segments: List[VoiceoverSegment] = Field(default_factory=list, description="配音片段列表")
    voice_style: str = Field(default="", description="声音风格")
    beat_sync: bool = Field(default=False, description="是否启用节拍同步")


class WorkflowState(BaseModel):
    """工作流状态"""
    project_id: str = Field(default="", description="项目ID")
    step: WorkflowStep = Field(default=WorkflowStep.IMPORT, description="当前步骤")
    status: WorkflowStatus = Field(default=WorkflowStatus.IDLE, description="工作流状态")
    progress: float = Field(default=0.0, ge=0, le=1, description="完成进度")
    error: str = Field(default="", description="错误信息")
    mode: Optional[CreationMode] = Field(default=None, description="创作模式")
    sources: List[VideoSource] = Field(default_factory=list, description="素材列表")
    analysis: Optional[AnalysisResult] = Field(default=None, description="分析结果")
    script: Optional[ScriptData] = Field(default=None, description="脚本数据")
    timeline: Optional[TimelineData] = Field(default=None, description="时间线数据")
    voiceover: Optional[VoiceoverData] = Field(default=None, description="配音数据")
    export_path: str = Field(default="", description="导出路径")
    export_format: Optional[ExportFormat] = Field(default=None, description="导出格式")


class WorkflowCallbacks(BaseModel):
    """工作流回调函数集合"""
    on_step_change: Optional[Callable[[WorkflowStep], None]] = Field(
        default=None, description="步骤变化回调"
    )
    on_progress: Optional[Callable[[float], None]] = Field(
        default=None, description="进度回调"
    )
    on_status_change: Optional[Callable[[WorkflowStatus], None]] = Field(
        default=None, description="状态变化回调"
    )
    on_error: Optional[Callable[[str], None]] = Field(
        default=None, description="错误回调"
    )
    on_complete: Optional[Callable[[], None]] = Field(
        default=None, description="完成回调"
    )
