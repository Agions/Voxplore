"""Platform data collector — fetches video metrics from various platforms."""

import logging
from datetime import datetime, timedelta

from scenefab.services.data_feedback.models import Platform, VideoMetrics

logger = logging.getLogger(__name__)


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

        for _i, vid in enumerate(video_ids):
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
