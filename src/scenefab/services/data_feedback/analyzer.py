"""Feedback analyzer — correlation analysis and insight generation."""

import logging

from scenefab.services.data_feedback.models import (
    ContentFeatureCorrelation,
    MetricType,
    PerformanceInsight,
    PerformanceLevel,
    VideoMetrics,
)
from scenefab.services.data_feedback.store import FeedbackDataStore

logger = logging.getLogger(__name__)


class FeedbackAnalyzer:
    """
    数据分析引擎

    分析内容特征与效果之间的关联，生成优化建议。
    """

    # 完播率基准线（各时长段）
    COMPLETION_BENCHMARKS = {
        (0, 30): 0.60,    # 30秒内，完播率基准 60%
        (30, 60): 0.45,   # 30-60秒，基准 45%
        (60, 120): 0.30,  # 1-2分钟，基准 30%
        (120, 300): 0.20, # 2-5分钟，基准 20%
        (300, 600): 0.12, # 5-10分钟，基准 12%
    }

    # 效果等级阈值
    PERFORMANCE_THRESHOLDS = {
        PerformanceLevel.VIRAL: 1_000_000,
        PerformanceLevel.EXCELLENT: 100_000,
        PerformanceLevel.GOOD: 10_000,
        PerformanceLevel.AVERAGE: 1_000,
        PerformanceLevel.LOW: 0,
    }

    def __init__(self, store: FeedbackDataStore):
        self.store = store

    def classify_performance(self, views: int) -> PerformanceLevel:
        """分类视频效果等级"""
        for level, threshold in self.PERFORMANCE_THRESHOLDS.items():
            if views >= threshold:
                return level
        return PerformanceLevel.LOW

    def analyze_hook_effectiveness(
        self,
        days: int = 30,
    ) -> list[ContentFeatureCorrelation]:
        """
        分析不同钩子类型的效果

        Returns:
            list[ContentFeatureCorrelation]: 各钩子类型的指标关联
        """
        stats = self.store.get_aggregated_stats(days=days)
        hook_stats = stats.get("hook_stats", [])

        if not hook_stats:
            return []

        # 计算各钩子类型的百分位排名
        all_avg_views = [h["avg_views"] for h in hook_stats]
        all_avg_views.sort()

        correlations = []
        for hook in hook_stats:
            avg_views = hook["avg_views"]
            percentile = (all_avg_views.index(avg_views) + 1) / len(all_avg_views) if all_avg_views else 0

            correlations.append(ContentFeatureCorrelation(
                feature_name="hook_type",
                feature_value=hook["hook_type"],
                metric=MetricType.VIEWS,
                avg_value=avg_views,
                sample_count=hook["count"],
                percentile=round(percentile, 2),
            ))

            correlations.append(ContentFeatureCorrelation(
                feature_name="hook_type",
                feature_value=hook["hook_type"],
                metric=MetricType.COMPLETION_RATE,
                avg_value=hook["avg_completion_rate"],
                sample_count=hook["count"],
                percentile=0,  # 简化处理
            ))

        return correlations

    def analyze_duration_impact(
        self,
        days: int = 30,
    ) -> list[ContentFeatureCorrelation]:
        """
        分析视频时长对效果的影响
        """
        metrics = self.store.query_metrics(limit=1000)
        if not metrics:
            return []

        # 按时长分组
        duration_buckets: dict[str, list[VideoMetrics]] = {
            "<30s": [], "30-60s": [], "1-2min": [], "2-5min": [], ">5min": [],
        }

        for m in metrics:
            if m.duration < 30:
                duration_buckets["<30s"].append(m)
            elif m.duration < 60:
                duration_buckets["30-60s"].append(m)
            elif m.duration < 120:
                duration_buckets["1-2min"].append(m)
            elif m.duration < 300:
                duration_buckets["2-5min"].append(m)
            else:
                duration_buckets[">5min"].append(m)

        correlations = []
        for bucket_name, bucket_metrics in duration_buckets.items():
            if not bucket_metrics:
                continue

            avg_views = sum(m.views for m in bucket_metrics) / len(bucket_metrics)
            avg_completion = sum(m.completion_rate for m in bucket_metrics) / len(bucket_metrics)

            correlations.append(ContentFeatureCorrelation(
                feature_name="duration_range",
                feature_value=bucket_name,
                metric=MetricType.VIEWS,
                avg_value=avg_views,
                sample_count=len(bucket_metrics),
                percentile=0,
            ))

            correlations.append(ContentFeatureCorrelation(
                feature_name="duration_range",
                feature_value=bucket_name,
                metric=MetricType.COMPLETION_RATE,
                avg_value=avg_completion,
                sample_count=len(bucket_metrics),
                percentile=0,
            ))

        return correlations

    def generate_insights(
        self,
        days: int = 30,
    ) -> list[PerformanceInsight]:
        """
        生成效果洞察
        """
        insights = []
        stats = self.store.get_aggregated_stats(days=days)

        # 1. 最佳钩子类型分析
        hook_stats = stats.get("hook_stats", [])
        if hook_stats:
            best_hook = max(hook_stats, key=lambda h: h["avg_views"])
            worst_hook = min(hook_stats, key=lambda h: h["avg_views"])

            if best_hook["hook_type"] != worst_hook["hook_type"]:
                improvement = (
                    (best_hook["avg_views"] - worst_hook["avg_views"])
                    / worst_hook["avg_views"] * 100
                ) if worst_hook["avg_views"] > 0 else 0

                insights.append(PerformanceInsight(
                    insight_type="hook_best",
                    title="最佳钩子类型",
                    description=(
                        f"「{best_hook['hook_type']}」类型的平均播放量 "
                        f"({best_hook['avg_views']:.0f}) 显著高于 "
                        f"「{worst_hook['hook_type']}」({worst_hook['avg_views']:.0f})，"
                        f"提升 {improvement:.1f}%"
                    ),
                    confidence=min(0.9, best_hook["count"] / 30),
                    data_points=best_hook["count"],
                    recommendation=f"建议优先使用「{best_hook['hook_type']}」类型的开头钩子",
                    related_metrics={
                        "avg_views": best_hook["avg_views"],
                        "avg_completion_rate": best_hook["avg_completion_rate"],
                    },
                ))

        # 2. 完播率分析
        avg_completion = stats.get("avg_completion_rate", 0)
        if avg_completion > 0:
            if avg_completion < 0.25:
                insights.append(PerformanceInsight(
                    insight_type="completion_low",
                    title="完播率偏低",
                    description=f"近 {days} 天平均完播率仅 {avg_completion*100:.1f}%，低于行业基准",
                    confidence=0.8,
                    data_points=stats["total_videos"],
                    recommendation="建议优化开头吸引力，缩短无效内容，增加转折点密度",
                ))
            elif avg_completion > 0.45:
                insights.append(PerformanceInsight(
                    insight_type="completion_high",
                    title="完播率优秀",
                    description=f"近 {days} 天平均完播率 {avg_completion*100:.1f}%，表现优秀",
                    confidence=0.8,
                    data_points=stats["total_videos"],
                    recommendation="当前内容节奏良好，可尝试增加视频时长以提升总播放时长",
                ))

        # 3. 平台差异分析
        platform_stats = stats.get("platform_stats", [])
        if len(platform_stats) >= 2:
            best_platform = max(platform_stats, key=lambda p: p["avg_completion_rate"])
            insights.append(PerformanceInsight(
                insight_type="platform_best",
                title="最佳表现平台",
                description=(
                    f"「{best_platform['platform']}」平台的完播率最高 "
                    f"({best_platform['avg_completion_rate']*100:.1f}%)，"
                    f"共 {best_platform['count']} 个视频"
                ),
                confidence=0.7,
                data_points=best_platform["count"],
                recommendation=f"建议在「{best_platform['platform']}」平台加大投放力度",
            ))

        # 4. 互动率分析
        total_views = stats.get("total_views", 0)
        total_likes = stats.get("total_likes", 0)
        total_comments = stats.get("total_comments", 0)

        if total_views > 0:
            like_rate = total_likes / total_views
            comment_rate = total_comments / total_views

            if like_rate < 0.02:
                insights.append(PerformanceInsight(
                    insight_type="engagement_low",
                    title="互动率偏低",
                    description=f"点赞率仅 {like_rate*100:.2f}%，低于 2% 基准线",
                    confidence=0.7,
                    data_points=stats["total_videos"],
                    recommendation="建议在视频中增加情感共鸣点和互动引导",
                ))

            if comment_rate > 0.01:
                insights.append(PerformanceInsight(
                    insight_type="comments_high",
                    title="评论互动活跃",
                    description=f"评论率 {comment_rate*100:.2f}%，用户参与度高",
                    confidence=0.7,
                    data_points=stats["total_videos"],
                    recommendation="建议在评论区置顶引导性评论，增加二次传播",
                ))

        return insights

    def generate_optimization_suggestions(
        self,
        days: int = 30,
    ) -> list[str]:
        """
        生成优化建议列表
        """
        suggestions = []
        insights = self.generate_insights(days)

        for insight in insights:
            suggestions.append(insight.recommendation)

        # 补充通用建议
        stats = self.store.get_aggregated_stats(days=days)
        if stats["total_videos"] < 10:
            suggestions.append("样本量不足（<10个视频），建议积累更多数据后再做深度分析")

        avg_duration = stats.get("avg_duration", 0)
        if avg_duration > 180:
            suggestions.append(f"平均时长 {avg_duration:.0f}s 偏长，建议控制在 2-3 分钟内提升完播率")
        elif avg_duration < 30:
            suggestions.append(f"平均时长 {avg_duration:.0f}s 偏短，可尝试 60-90 秒的中等时长")

        return suggestions
