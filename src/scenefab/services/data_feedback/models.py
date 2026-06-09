"""Data feedback models — enums and dataclasses."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class Platform(str, Enum):
    """发布平台"""

    DOUYIN = "douyin"  # 抖音
    KUAISHOU = "kuaishou"  # 快手
    BILIBILI = "bilibili"  # B站
    YOUTUBE = "youtube"  # YouTube
    XIAOHONGSHU = "xiaohongshu"  # 小红书


class MetricType(str, Enum):
    """指标类型"""

    VIEWS = "views"  # 播放量
    LIKES = "likes"  # 点赞数
    COMMENTS = "comments"  # 评论数
    SHARES = "shares"  # 转发数
    COLLECTS = "collects"  # 收藏数
    COMPLETION_RATE = "completion_rate"  # 完播率
    AVG_WATCH_DURATION = "avg_watch_duration"  # 平均观看时长
    FOLLOWERS_GAINED = "followers_gained"  # 涨粉数


class ContentType(str, Enum):
    """内容类型（关联 A/B 测试的钩子类型）"""

    RESULT_FIRST = "result_first"
    CONFLICT = "conflict"
    SUSPENSE = "suspense"
    QUESTION = "question"
    SHOCK = "shock"
    EMOTIONAL = "emotional"
    HUMOROUS = "humorous"


class PerformanceLevel(str, Enum):
    """效果等级"""

    VIRAL = "viral"  # 爆款 (>100万播放)
    EXCELLENT = "excellent"  # 优秀 (>10万播放)
    GOOD = "good"  # 良好 (>1万播放)
    AVERAGE = "average"  # 一般 (>1000播放)
    LOW = "low"  # 较低 (<1000播放)


@dataclass
class VideoMetrics:
    """视频效果指标"""

    video_id: str
    platform: Platform
    publish_time: datetime
    title: str
    duration: float  # 秒
    # 基础指标
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    collects: int = 0
    # 高级指标
    completion_rate: float = 0.0  # 完播率 0-1
    avg_watch_duration: float = 0.0  # 平均观看时长（秒）
    followers_gained: int = 0
    # 内容特征标签
    hook_type: str = ""  # 钩子类型
    emotion_tags: list[str] = field(default_factory=list)
    topic_tags: list[str] = field(default_factory=list)
    # 元信息
    thumbnail_path: str = ""
    script_variant_id: str = ""  # 关联的 A/B 测试变体 ID
    collected_at: datetime = field(default_factory=datetime.now)


@dataclass
class PerformanceInsight:
    """效果洞察"""

    insight_type: str  # "hook_best", "duration_optimal", "emotion_trending", etc.
    title: str
    description: str
    confidence: float  # 置信度 0-1
    data_points: int  # 支撑数据点数量
    recommendation: str  # 具体建议
    related_metrics: dict[str, float] = field(default_factory=dict)


@dataclass
class ContentFeatureCorrelation:
    """内容特征与效果关联"""

    feature_name: str  # 特征名（如 hook_type, duration_range）
    feature_value: str  # 特征值（如 "suspense", "60-90s"）
    metric: MetricType
    avg_value: float  # 该特征下的平均指标值
    sample_count: int  # 样本数
    percentile: float  # 在所有特征中的百分位排名


@dataclass
class FeedbackReport:
    """数据回流报告"""

    report_id: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    total_videos: int
    platform_breakdown: dict[str, int]
    # 效果分布
    performance_distribution: dict[str, int]  # level -> count
    # 最佳实践
    top_insights: list[PerformanceInsight]
    # 特征关联
    feature_correlations: list[ContentFeatureCorrelation]
    # 优化建议
    optimization_suggestions: list[str]
    # 趋势
    trend_summary: str
