"""Data feedback manager — orchestrates collection, storage, and analysis."""

import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from scenefab.services.data_feedback.analyzer import FeedbackAnalyzer
from scenefab.services.data_feedback.collector import PlatformDataCollector
from scenefab.services.data_feedback.models import (
    FeedbackReport,
    MetricType,
    Platform,
    VideoMetrics,
)
from scenefab.services.data_feedback.store import FeedbackDataStore

logger = logging.getLogger(__name__)


class DataFeedbackManager:
    """
    数据回流管理器

    整合数据采集、存储、分析的完整数据回流闭环。

    使用方法：
        manager = DataFeedbackManager(api_keys={"douyin": "xxx"})
        # 采集数据
        metrics = manager.collect_from_platform(Platform.DOUYIN, ["video_id_1", "video_id_2"])
        # 生成报告
        report = manager.generate_report(days=30)
        # 获取优化建议
        suggestions = manager.get_optimization_suggestions()
        # 获取最佳实践
        best_hook = manager.get_best_hook_type()
    """

    def __init__(
        self,
        api_keys: dict[str, str] | None = None,
        db_path: str | Path | None = None,
    ):
        """
        初始化数据回流管理器

        Args:
            api_keys: 各平台 API Key
            db_path: 本地数据库路径
        """
        self.collector = PlatformDataCollector(api_keys=api_keys)
        self.store = FeedbackDataStore(db_path=db_path)
        self.analyzer = FeedbackAnalyzer(self.store)
        logger.info("DataFeedbackManager 初始化完成")

    def collect_from_platform(
        self,
        platform: Platform,
        video_ids: list[str],
        auto_save: bool = True,
    ) -> list[VideoMetrics]:
        """
        从指定平台采集数据并存储

        Args:
            platform: 目标平台
            video_ids: 视频 ID 列表
            auto_save: 是否自动保存到本地

        Returns:
            list[VideoMetrics]: 采集到的指标
        """
        metrics = self.collector.collect_metrics(platform, video_ids)

        if auto_save:
            self.store.save_metrics_batch(metrics)

        return metrics

    def collect_all_platforms(
        self,
        platform_videos: dict[Platform, list[str]],
    ) -> dict[Platform, list[VideoMetrics]]:
        """
        从多个平台采集数据

        Args:
            platform_videos: {平台: [视频ID列表]}

        Returns:
            dict: {平台: [指标列表]}
        """
        results = {}
        for platform, video_ids in platform_videos.items():
            results[platform] = self.collect_from_platform(platform, video_ids)
        return results

    def record_manual_metrics(self, metrics: VideoMetrics):
        """
        手动录入视频效果数据（适用于无 API 的平台）

        Args:
            metrics: 视频指标数据
        """
        self.store.save_metrics(metrics)
        logger.info(f"手动录入: {metrics.video_id} ({metrics.platform.value})")

    def generate_report(
        self,
        days: int = 30,
    ) -> FeedbackReport:
        """
        生成数据回流报告

        Args:
            days: 分析天数

        Returns:
            FeedbackReport: 完整报告
        """
        report_id = hashlib.md5(f"{datetime.now().isoformat()}".encode()).hexdigest()[
            :12
        ]

        stats = self.store.get_aggregated_stats(days=days)
        insights = self.analyzer.generate_insights(days)
        correlations = self.analyzer.analyze_hook_effectiveness(days)
        suggestions = self.analyzer.generate_optimization_suggestions(days)

        # 效果分布
        metrics = self.store.query_metrics(limit=10000)
        distribution: dict[str, int] = {}
        for m in metrics:
            level = self.analyzer.classify_performance(m.views)
            distribution[level.value] = distribution.get(level.value, 0) + 1

        # 平台分布
        platform_breakdown: dict[str, int] = {}
        for ps in stats.get("platform_stats", []):
            platform_breakdown[ps["platform"]] = ps["count"]

        # 趋势摘要
        total_videos = stats["total_videos"]
        avg_views = stats["total_views"] / total_videos if total_videos > 0 else 0
        trend = (
            f"近 {days} 天共发布 {total_videos} 个视频，"
            f"平均播放 {avg_views:.0f} 次，"
            f"平均完播率 {stats['avg_completion_rate'] * 100:.1f}%"
        )

        report = FeedbackReport(
            report_id=report_id,
            generated_at=datetime.now(),
            period_start=datetime.now() - timedelta(days=days),
            period_end=datetime.now(),
            total_videos=total_videos,
            platform_breakdown=platform_breakdown,
            performance_distribution=distribution,
            top_insights=insights[:5],
            feature_correlations=correlations,
            optimization_suggestions=suggestions,
            trend_summary=trend,
        )

        logger.info(f"报告生成完成: {report_id}")
        return report

    def get_best_hook_type(self, days: int = 30) -> str | None:
        """获取效果最好的钩子类型"""
        correlations = self.analyzer.analyze_hook_effectiveness(days)
        if not correlations:
            return None

        view_correlations = [c for c in correlations if c.metric == MetricType.VIEWS]
        if not view_correlations:
            return None

        best = max(view_correlations, key=lambda c: c.avg_value)
        return best.feature_value

    def get_optimization_suggestions(self, days: int = 30) -> list[str]:
        """获取优化建议"""
        return self.analyzer.generate_optimization_suggestions(days)

    def get_performance_trend(
        self,
        video_id: str,
        platform: Platform,
    ) -> list[dict[str, Any]]:
        """
        获取单个视频的效果趋势

        Args:
            video_id: 视频 ID
            platform: 平台

        Returns:
            list[dict]: 时间序列数据
        """
        with sqlite3.connect(self.store.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM feedback_snapshots
                WHERE video_id = ? AND platform = ?
                ORDER BY snapshot_time ASC
            """,
                (video_id, platform.value),
            ).fetchall()

        return [dict(r) for r in rows]

    def export_report_json(
        self,
        report: FeedbackReport,
        output_path: str | Path,
    ):
        """
        导出报告为 JSON 文件

        Args:
            report: 报告对象
            output_path: 输出路径
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "report_id": report.report_id,
            "generated_at": report.generated_at.isoformat(),
            "period": {
                "start": report.period_start.isoformat(),
                "end": report.period_end.isoformat(),
            },
            "summary": {
                "total_videos": report.total_videos,
                "platform_breakdown": report.platform_breakdown,
                "performance_distribution": report.performance_distribution,
                "trend_summary": report.trend_summary,
            },
            "insights": [
                {
                    "type": i.insight_type,
                    "title": i.title,
                    "description": i.description,
                    "confidence": i.confidence,
                    "recommendation": i.recommendation,
                }
                for i in report.top_insights
            ],
            "feature_correlations": [
                {
                    "feature": f"{c.feature_name}={c.feature_value}",
                    "metric": c.metric.value,
                    "avg_value": c.avg_value,
                    "sample_count": c.sample_count,
                    "percentile": c.percentile,
                }
                for c in report.feature_correlations
            ],
            "optimization_suggestions": report.optimization_suggestions,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"报告已导出: {output_path}")
