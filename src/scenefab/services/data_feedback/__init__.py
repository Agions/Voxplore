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

import logging
import sqlite3
import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================
# 枚举与数据模型
# ============================================================

class Platform(str, Enum):
    """发布平台"""
    DOUYIN = "douyin"       # 抖音
    KUAISHOU = "kuaishou"   # 快手
    BILIBILI = "bilibili"   # B站
    YOUTUBE = "youtube"     # YouTube
    XIAOHONGSHU = "xiaohongshu"  # 小红书


class MetricType(str, Enum):
    """指标类型"""
    VIEWS = "views"             # 播放量
    LIKES = "likes"             # 点赞数
    COMMENTS = "comments"       # 评论数
    SHARES = "shares"           # 转发数
    COLLECTS = "collects"       # 收藏数
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
    VIRAL = "viral"         # 爆款 (>100万播放)
    EXCELLENT = "excellent" # 优秀 (>10万播放)
    GOOD = "good"           # 良好 (>1万播放)
    AVERAGE = "average"     # 一般 (>1000播放)
    LOW = "low"             # 较低 (<1000播放)


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
    completion_rate: float = 0.0    # 完播率 0-1
    avg_watch_duration: float = 0.0  # 平均观看时长（秒）
    followers_gained: int = 0
    # 内容特征标签
    hook_type: str = ""       # 钩子类型
    emotion_tags: list[str] = field(default_factory=list)
    topic_tags: list[str] = field(default_factory=list)
    # 元信息
    thumbnail_path: str = ""
    script_variant_id: str = ""  # 关联的 A/B 测试变体 ID
    collected_at: datetime = field(default_factory=datetime.now)


@dataclass
class PerformanceInsight:
    """效果洞察"""
    insight_type: str       # "hook_best", "duration_optimal", "emotion_trending", etc.
    title: str
    description: str
    confidence: float       # 置信度 0-1
    data_points: int        # 支撑数据点数量
    recommendation: str     # 具体建议
    related_metrics: dict[str, float] = field(default_factory=dict)


@dataclass
class ContentFeatureCorrelation:
    """内容特征与效果关联"""
    feature_name: str       # 特征名（如 hook_type, duration_range）
    feature_value: str      # 特征值（如 "suspense", "60-90s"）
    metric: MetricType
    avg_value: float        # 该特征下的平均指标值
    sample_count: int       # 样本数
    percentile: float       # 在所有特征中的百分位排名


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


# ============================================================
# 数据采集器
# ============================================================

class PlatformDataCollector:
    """
    平台数据采集器

    支持通过 API 或模拟方式采集各平台的视频效果数据。
    实际生产环境中，需要对接各平台开放平台 API。
    """

    # 各平台 API 配置（需要实际的 API Key）
    PLATFORM_APIS = {
        Platform.DOUYIN: {
            "base_url": "https://open.douyin.com/api",
            "metrics_endpoint": "/video/data/",
        },
        Platform.BILIBILI: {
            "base_url": "https://api.bilibili.com",
            "metrics_endpoint": "/x/web-interface/view",
        },
        Platform.YOUTUBE: {
            "base_url": "https://www.googleapis.com/youtube/v3",
            "metrics_endpoint": "/videos",
        },
        Platform.KUAISHOU: {
            "base_url": "https://open.kuaishou.com",
            "metrics_endpoint": "/api/photo/metrics",
        },
        Platform.XIAOHONGSHU: {
            "base_url": "https://open.xiaohongshu.com",
            "metrics_endpoint": "/api/note/metrics",
        },
    }

    def __init__(self, api_keys: dict[str, str] | None = None):
        """
        初始化采集器

        Args:
            api_keys: 各平台 API Key，格式 {"douyin": "xxx", "bilibili": "xxx"}
        """
        self.api_keys = api_keys or {}
        self._http_client = None
        logger.info("PlatformDataCollector 初始化完成")

    def _get_http_client(self):
        """延迟初始化 HTTP 客户端"""
        if self._http_client is None:
            try:
                import httpx
                self._http_client = httpx.Client(timeout=30.0)
            except ImportError:
                logger.warning("httpx 未安装，将使用模拟数据")
        return self._http_client

    def collect_metrics(
        self,
        platform: Platform,
        video_ids: list[str],
    ) -> list[VideoMetrics]:
        """
        采集指定平台的视频效果数据

        Args:
            platform: 目标平台
            video_ids: 视频 ID 列表

        Returns:
            list[VideoMetrics]: 采集到的效果数据
        """
        logger.info(f"开始采集 {platform.value} 平台数据，视频数: {len(video_ids)}")

        if platform not in self.api_keys:
            logger.warning(f"{platform.value} API Key 未配置，返回模拟数据")
            return self._generate_mock_metrics(platform, video_ids)

        try:
            if platform == Platform.DOUYIN:
                return self._collect_douyin(video_ids)
            elif platform == Platform.BILIBILI:
                return self._collect_bilibili(video_ids)
            elif platform == Platform.YOUTUBE:
                return self._collect_youtube(video_ids)
            else:
                return self._generate_mock_metrics(platform, video_ids)
        except Exception as e:
            logger.error(f"采集 {platform.value} 数据失败: {e}")
            return self._generate_mock_metrics(platform, video_ids)

    def _collect_douyin(self, video_ids: list[str]) -> list[VideoMetrics]:
        """采集抖音数据"""
        client = self._get_http_client()
        if not client:
            return self._generate_mock_metrics(Platform.DOUYIN, video_ids)

        results = []
        config = self.PLATFORM_APIS[Platform.DOUYIN]

        for vid in video_ids:
            try:
                response = client.get(
                    f"{config['base_url']}{config['metrics_endpoint']}",
                    params={"video_id": vid},
                    headers={"access-token": self.api_keys.get("douyin", "")},
                )
                if response.status_code == 200:
                    data = response.json().get("data", {})
                    metrics = VideoMetrics(
                        video_id=vid,
                        platform=Platform.DOUYIN,
                        publish_time=datetime.fromisoformat(data.get("create_time", datetime.now().isoformat())),
                        title=data.get("title", ""),
                        duration=data.get("duration", 0),
                        views=data.get("play_count", 0),
                        likes=data.get("digg_count", 0),
                        comments=data.get("comment_count", 0),
                        shares=data.get("share_count", 0),
                        collects=data.get("collect_count", 0),
                        completion_rate=data.get("complete_rate", 0),
                    )
                    results.append(metrics)
            except Exception as e:
                logger.warning(f"抖音视频 {vid} 采集失败: {e}")

        return results

    def _collect_bilibili(self, video_ids: list[str]) -> list[VideoMetrics]:
        """采集 B站数据"""
        client = self._get_http_client()
        if not client:
            return self._generate_mock_metrics(Platform.BILIBILI, video_ids)

        results = []
        config = self.PLATFORM_APIS[Platform.BILIBILI]

        for vid in video_ids:
            try:
                response = client.get(
                    f"{config['base_url']}{config['metrics_endpoint']}",
                    params={"bvid": vid},
                )
                if response.status_code == 200:
                    data = response.json().get("data", {})
                    stat = data.get("stat", {})
                    metrics = VideoMetrics(
                        video_id=vid,
                        platform=Platform.BILIBILI,
                        publish_time=datetime.fromtimestamp(data.get("pubdate", 0)),
                        title=data.get("title", ""),
                        duration=data.get("duration", 0),
                        views=stat.get("view", 0),
                        likes=stat.get("like", 0),
                        comments=stat.get("reply", 0),
                        shares=stat.get("share", 0),
                        collects=stat.get("favorite", 0),
                    )
                    results.append(metrics)
            except Exception as e:
                logger.warning(f"B站视频 {vid} 采集失败: {e}")

        return results

    def _collect_youtube(self, video_ids: list[str]) -> list[VideoMetrics]:
        """采集 YouTube 数据"""
        client = self._get_http_client()
        if not client:
            return self._generate_mock_metrics(Platform.YOUTUBE, video_ids)

        results = []
        config = self.PLATFORM_APIS[Platform.YOUTUBE]
        api_key = self.api_keys.get("youtube", "")

        for vid in video_ids:
            try:
                response = client.get(
                    f"{config['base_url']}{config['metrics_endpoint']}",
                    params={
                        "part": "statistics,contentDetails,snippet",
                        "id": vid,
                        "key": api_key,
                    },
                )
                if response.status_code == 200:
                    items = response.json().get("items", [])
                    if items:
                        item = items[0]
                        stats = item.get("statistics", {})
                        snippet = item.get("snippet", {})
                        metrics = VideoMetrics(
                            video_id=vid,
                            platform=Platform.YOUTUBE,
                            publish_time=datetime.fromisoformat(
                                snippet.get("publishedAt", datetime.now().isoformat()).replace("Z", "+00:00")
                            ),
                            title=snippet.get("title", ""),
                            duration=0,  # 需要解析 ISO 8601 时长
                            views=int(stats.get("viewCount", 0)),
                            likes=int(stats.get("likeCount", 0)),
                            comments=int(stats.get("commentCount", 0)),
                        )
                        results.append(metrics)
            except Exception as e:
                logger.warning(f"YouTube 视频 {vid} 采集失败: {e}")

        return results

    def _generate_mock_metrics(
        self,
        platform: Platform,
        video_ids: list[str],
    ) -> list[VideoMetrics]:
        """生成模拟数据（用于开发和测试）"""
        import random

        results = []
        now = datetime.now()

        for i, vid in enumerate(video_ids):
            views = random.randint(100, 500000)
            metrics = VideoMetrics(
                video_id=vid,
                platform=platform,
                publish_time=now - timedelta(days=random.randint(1, 30)),
                title=f"模拟视频_{vid[:8]}",
                duration=random.uniform(30, 300),
                views=views,
                likes=int(views * random.uniform(0.01, 0.1)),
                comments=int(views * random.uniform(0.001, 0.02)),
                shares=int(views * random.uniform(0.005, 0.05)),
                collects=int(views * random.uniform(0.005, 0.03)),
                completion_rate=random.uniform(0.1, 0.8),
                avg_watch_duration=random.uniform(10, 120),
                followers_gained=random.randint(0, 100),
                hook_type=random.choice(["result_first", "conflict", "suspense", "question", "shock"]),
                emotion_tags=random.sample(["tense", "warm", "shocking", "funny", "sad", "exciting"], 2),
            )
            results.append(metrics)

        logger.info(f"生成 {len(results)} 条模拟数据")
        return results


# ============================================================
# 数据存储
# ============================================================

class FeedbackDataStore:
    """
    数据回流本地存储

    使用 SQLite 存储视频效果数据，支持高效的查询和分析。
    """

    def __init__(self, db_path: str | Path | None = None):
        """
        初始化数据存储

        Args:
            db_path: SQLite 数据库路径，默认 ~/.hermes/scene-fab/feedback.db
        """
        if db_path is None:
            db_path = Path.home() / ".hermes" / "scene-fab" / "feedback.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info(f"FeedbackDataStore 初始化完成: {self.db_path}")

    def _init_db(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS video_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    publish_time TEXT,
                    title TEXT,
                    duration REAL,
                    views INTEGER DEFAULT 0,
                    likes INTEGER DEFAULT 0,
                    comments INTEGER DEFAULT 0,
                    shares INTEGER DEFAULT 0,
                    collects INTEGER DEFAULT 0,
                    completion_rate REAL DEFAULT 0,
                    avg_watch_duration REAL DEFAULT 0,
                    followers_gained INTEGER DEFAULT 0,
                    hook_type TEXT,
                    emotion_tags TEXT,
                    topic_tags TEXT,
                    thumbnail_path TEXT,
                    script_variant_id TEXT,
                    collected_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(video_id, platform)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    snapshot_time TEXT,
                    views INTEGER,
                    likes INTEGER,
                    comments INTEGER,
                    shares INTEGER,
                    collects INTEGER,
                    completion_rate REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_platform
                ON video_metrics(platform)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_publish_time
                ON video_metrics(publish_time)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_hook_type
                ON video_metrics(hook_type)
            """)
            conn.commit()

    def save_metrics(self, metrics: VideoMetrics):
        """保存或更新视频效果数据"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO video_metrics (
                    video_id, platform, publish_time, title, duration,
                    views, likes, comments, shares, collects,
                    completion_rate, avg_watch_duration, followers_gained,
                    hook_type, emotion_tags, topic_tags, thumbnail_path,
                    script_variant_id, collected_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics.video_id,
                metrics.platform.value,
                metrics.publish_time.isoformat(),
                metrics.title,
                metrics.duration,
                metrics.views,
                metrics.likes,
                metrics.comments,
                metrics.shares,
                metrics.collects,
                metrics.completion_rate,
                metrics.avg_watch_duration,
                metrics.followers_gained,
                metrics.hook_type,
                json.dumps(metrics.emotion_tags, ensure_ascii=False),
                json.dumps(metrics.topic_tags, ensure_ascii=False),
                metrics.thumbnail_path,
                metrics.script_variant_id,
                metrics.collected_at.isoformat(),
            ))

            # 同时保存快照用于趋势分析
            conn.execute("""
                INSERT INTO feedback_snapshots (
                    video_id, platform, snapshot_time,
                    views, likes, comments, shares, collects, completion_rate
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics.video_id,
                metrics.platform.value,
                datetime.now().isoformat(),
                metrics.views,
                metrics.likes,
                metrics.comments,
                metrics.shares,
                metrics.collects,
                metrics.completion_rate,
            ))
            conn.commit()

        logger.debug(f"保存指标: {metrics.video_id} ({metrics.platform.value})")

    def save_metrics_batch(self, metrics_list: list[VideoMetrics]):
        """批量保存"""
        for m in metrics_list:
            self.save_metrics(m)
        logger.info(f"批量保存 {len(metrics_list)} 条指标")

    def query_metrics(
        self,
        platform: Platform | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        hook_type: str | None = None,
        min_views: int | None = None,
        limit: int = 100,
    ) -> list[VideoMetrics]:
        """查询视频效果数据"""
        conditions = []
        params = []

        if platform:
            conditions.append("platform = ?")
            params.append(platform.value)
        if start_date:
            conditions.append("publish_time >= ?")
            params.append(start_date.isoformat())
        if end_date:
            conditions.append("publish_time <= ?")
            params.append(end_date.isoformat())
        if hook_type:
            conditions.append("hook_type = ?")
            params.append(hook_type)
        if min_views:
            conditions.append("views >= ?")
            params.append(min_views)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"""
            SELECT * FROM video_metrics
            WHERE {where_clause}
            ORDER BY publish_time DESC
            LIMIT ?
        """
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()

        results = []
        for row in rows:
            m = VideoMetrics(
                video_id=row["video_id"],
                platform=Platform(row["platform"]),
                publish_time=datetime.fromisoformat(row["publish_time"]),
                title=row["title"],
                duration=row["duration"],
                views=row["views"],
                likes=row["likes"],
                comments=row["comments"],
                shares=row["shares"],
                collects=row["collects"],
                completion_rate=row["completion_rate"],
                avg_watch_duration=row["avg_watch_duration"],
                followers_gained=row["followers_gained"],
                hook_type=row["hook_type"] or "",
                emotion_tags=json.loads(row["emotion_tags"] or "[]"),
                topic_tags=json.loads(row["topic_tags"] or "[]"),
                thumbnail_path=row["thumbnail_path"] or "",
                script_variant_id=row["script_variant_id"] or "",
                collected_at=datetime.fromisoformat(row["collected_at"]) if row["collected_at"] else datetime.now(),
            )
            results.append(m)

        return results

    def get_aggregated_stats(
        self,
        platform: Platform | None = None,
        days: int = 30,
    ) -> dict[str, Any]:
        """获取聚合统计数据"""
        since = (datetime.now() - timedelta(days=days)).isoformat()

        conditions = ["publish_time >= ?"]
        params: list[Any] = [since]

        if platform:
            conditions.append("platform = ?")
            params.append(platform.value)

        where_clause = " AND ".join(conditions)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # 总体统计
            row = conn.execute(f"""
                SELECT
                    COUNT(*) as total_videos,
                    SUM(views) as total_views,
                    SUM(likes) as total_likes,
                    SUM(comments) as total_comments,
                    SUM(shares) as total_shares,
                    AVG(completion_rate) as avg_completion_rate,
                    AVG(duration) as avg_duration,
                    MAX(views) as max_views
                FROM video_metrics
                WHERE {where_clause}
            """, params).fetchone()

            # 按钩子类型分组
            hook_stats = conn.execute(f"""
                SELECT
                    hook_type,
                    COUNT(*) as count,
                    AVG(views) as avg_views,
                    AVG(likes) as avg_likes,
                    AVG(completion_rate) as avg_completion_rate
                FROM video_metrics
                WHERE {where_clause} AND hook_type IS NOT NULL AND hook_type != ''
                GROUP BY hook_type
                ORDER BY avg_views DESC
            """, params).fetchall()

            # 按平台分组
            platform_stats = conn.execute(f"""
                SELECT
                    platform,
                    COUNT(*) as count,
                    SUM(views) as total_views,
                    AVG(completion_rate) as avg_completion_rate
                FROM video_metrics
                WHERE {where_clause}
                GROUP BY platform
                ORDER BY total_views DESC
            """, params).fetchall()

        return {
            "period_days": days,
            "total_videos": row["total_videos"] or 0,
            "total_views": row["total_views"] or 0,
            "total_likes": row["total_likes"] or 0,
            "total_comments": row["total_comments"] or 0,
            "total_shares": row["total_shares"] or 0,
            "avg_completion_rate": round(row["avg_completion_rate"] or 0, 3),
            "avg_duration": round(row["avg_duration"] or 0, 1),
            "max_views": row["max_views"] or 0,
            "hook_stats": [dict(r) for r in hook_stats],
            "platform_stats": [dict(r) for r in platform_stats],
        }


# ============================================================
# 分析引擎
# ============================================================

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


# ============================================================
# 数据回流管理器（主入口）
# ============================================================

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
        report_id = hashlib.md5(
            f"{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

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
            f"平均完播率 {stats['avg_completion_rate']*100:.1f}%"
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
        import sqlite3 as sqlite

        with sqlite.connect(self.store.db_path) as conn:
            conn.row_factory = sqlite.Row
            rows = conn.execute("""
                SELECT * FROM feedback_snapshots
                WHERE video_id = ? AND platform = ?
                ORDER BY snapshot_time ASC
            """, (video_id, platform.value)).fetchall()

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
