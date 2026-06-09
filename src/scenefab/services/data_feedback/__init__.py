"""
SceneFab 数据回流模块

功能：
1. 多平台数据采集（抖音/快手/B站/YouTube）
2. 发布后效果追踪（播放/点赞/评论/转发/完播率）
3. 内容特征与效果关联分析
4. 智能优化建议生成
5. 数据反馈闭环（指导后续内容生产）

技术栈：
- httpx: 平台 API 数据采集
- SQLite: 本地数据存储
- 统计分析: 特征-效果关联

数据流向：
发布 → 平台数据采集 → 本地存储 → 分析引擎 → 优化建议 → 指导下次生产
"""

from pathlib import Path

from scenefab.services.data_feedback.analyzer import FeedbackAnalyzer
from scenefab.services.data_feedback.collector import PlatformDataCollector
from scenefab.services.data_feedback.manager import DataFeedbackManager
from scenefab.services.data_feedback.models import (
    ContentFeatureCorrelation,
    ContentType,
    FeedbackReport,
    MetricType,
    PerformanceInsight,
    PerformanceLevel,
    Platform,
    VideoMetrics,
)
from scenefab.services.data_feedback.store import FeedbackDataStore

__all__ = [
    # Enums
    "Platform",
    "MetricType",
    "ContentType",
    "PerformanceLevel",
    # Data classes
    "VideoMetrics",
    "PerformanceInsight",
    "ContentFeatureCorrelation",
    "FeedbackReport",
    # Service classes
    "PlatformDataCollector",
    "FeedbackDataStore",
    "FeedbackAnalyzer",
    "DataFeedbackManager",
    # Convenience functions
    "create_feedback_manager",
    "quick_report",
]


# ============================================================
# 便捷函数
# ============================================================


def create_feedback_manager(
    api_keys: dict[str, str] | None = None,
    db_path: str | Path | None = None,
) -> DataFeedbackManager:
    """
    便捷函数：创建数据回流管理器

    Args:
        api_keys: 各平台 API Key
        db_path: 本地数据库路径

    Returns:
        DataFeedbackManager: 管理器实例
    """
    return DataFeedbackManager(api_keys=api_keys, db_path=db_path)


def quick_report(
    db_path: str | Path | None = None,
    days: int = 30,
) -> FeedbackReport:
    """
    便捷函数：快速生成报告

    Args:
        db_path: 数据库路径
        days: 分析天数

    Returns:
        FeedbackReport: 报告
    """
    manager = DataFeedbackManager(db_path=db_path)
    return manager.generate_report(days=days)
