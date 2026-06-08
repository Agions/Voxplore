"""Feedback data store — SQLite-backed persistence for video metrics."""

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from scenefab.services.data_feedback.models import Platform, VideoMetrics

logger = logging.getLogger(__name__)

_METRICS_COLS = (
    "video_id, platform, publish_time, title, duration, views, likes, comments, "
    "shares, collects, completion_rate, avg_watch_duration, followers_gained, "
    "hook_type, emotion_tags, topic_tags, thumbnail_path, script_variant_id, collected_at"
)
_SNAPSHOT_COLS = "video_id, platform, snapshot_time, views, likes, comments, shares, collects, completion_rate"


def _metrics_to_row(m: VideoMetrics) -> tuple:
    return (
        m.video_id, m.platform.value, m.publish_time.isoformat(),
        m.title, m.duration, m.views, m.likes, m.comments,
        m.shares, m.collects, m.completion_rate, m.avg_watch_duration,
        m.followers_gained, m.hook_type,
        json.dumps(m.emotion_tags, ensure_ascii=False),
        json.dumps(m.topic_tags, ensure_ascii=False),
        m.thumbnail_path, m.script_variant_id, m.collected_at.isoformat(),
    )


class FeedbackDataStore:
    """数据回流本地存储 — 使用 SQLite 存储视频效果数据。"""

    def __init__(self, db_path: str | Path | None = None):
        if db_path is None:
            db_path = Path.home() / ".hermes" / "scene-fab" / "feedback.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info(f"FeedbackDataStore 初始化完成: {self.db_path}")

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS video_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id TEXT NOT NULL, platform TEXT NOT NULL,
                    publish_time TEXT, title TEXT, duration REAL,
                    views INTEGER DEFAULT 0, likes INTEGER DEFAULT 0,
                    comments INTEGER DEFAULT 0, shares INTEGER DEFAULT 0,
                    collects INTEGER DEFAULT 0, completion_rate REAL DEFAULT 0,
                    avg_watch_duration REAL DEFAULT 0, followers_gained INTEGER DEFAULT 0,
                    hook_type TEXT, emotion_tags TEXT, topic_tags TEXT,
                    thumbnail_path TEXT, script_variant_id TEXT,
                    collected_at TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(video_id, platform)
                );
                CREATE TABLE IF NOT EXISTS feedback_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id TEXT NOT NULL, platform TEXT NOT NULL,
                    snapshot_time TEXT, views INTEGER, likes INTEGER,
                    comments INTEGER, shares INTEGER, collects INTEGER,
                    completion_rate REAL, created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_metrics_platform ON video_metrics(platform);
                CREATE INDEX IF NOT EXISTS idx_metrics_publish_time ON video_metrics(publish_time);
                CREATE INDEX IF NOT EXISTS idx_metrics_hook_type ON video_metrics(hook_type);
            """)

    def save_metrics(self, metrics: VideoMetrics):
        """保存或更新视频效果数据"""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                f"INSERT OR REPLACE INTO video_metrics ({_METRICS_COLS}) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                _metrics_to_row(metrics),
            )
            conn.execute(
                f"INSERT INTO feedback_snapshots ({_SNAPSHOT_COLS}) VALUES (?,?,?,?,?,?,?,?,?)",
                (metrics.video_id, metrics.platform.value, now,
                 metrics.views, metrics.likes, metrics.comments,
                 metrics.shares, metrics.collects, metrics.completion_rate),
            )
            conn.commit()
        logger.debug(f"保存指标: {metrics.video_id} ({metrics.platform.value})")

    def save_metrics_batch(self, metrics_list: list[VideoMetrics]):
        """批量保存（单连接 + 事务，性能优化）"""
        if not metrics_list:
            return
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany(
                f"INSERT OR REPLACE INTO video_metrics ({_METRICS_COLS}) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [_metrics_to_row(m) for m in metrics_list],
            )
            conn.executemany(
                f"INSERT INTO feedback_snapshots ({_SNAPSHOT_COLS}) VALUES (?,?,?,?,?,?,?,?,?)",
                [(m.video_id, m.platform.value, now, m.views, m.likes,
                  m.comments, m.shares, m.collects, m.completion_rate)
                 for m in metrics_list],
            )
            conn.commit()
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
        conditions, params = [], []
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

        where = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"SELECT * FROM video_metrics WHERE {where} ORDER BY publish_time DESC LIMIT ?",
                params,
            ).fetchall()

        return [
            VideoMetrics(
                video_id=r["video_id"], platform=Platform(r["platform"]),
                publish_time=datetime.fromisoformat(r["publish_time"]),
                title=r["title"], duration=r["duration"],
                views=r["views"], likes=r["likes"], comments=r["comments"],
                shares=r["shares"], collects=r["collects"],
                completion_rate=r["completion_rate"],
                avg_watch_duration=r["avg_watch_duration"],
                followers_gained=r["followers_gained"],
                hook_type=r["hook_type"] or "",
                emotion_tags=json.loads(r["emotion_tags"] or "[]"),
                topic_tags=json.loads(r["topic_tags"] or "[]"),
                thumbnail_path=r["thumbnail_path"] or "",
                script_variant_id=r["script_variant_id"] or "",
                collected_at=datetime.fromisoformat(r["collected_at"]) if r["collected_at"] else datetime.now(),
            )
            for r in rows
        ]

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
        where = " AND ".join(conditions)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(f"""
                SELECT COUNT(*) as total_videos, SUM(views) as total_views,
                    SUM(likes) as total_likes, SUM(comments) as total_comments,
                    SUM(shares) as total_shares, AVG(completion_rate) as avg_completion_rate,
                    AVG(duration) as avg_duration, MAX(views) as max_views
                FROM video_metrics WHERE {where}
            """, params).fetchone()

            hook_stats = conn.execute(f"""
                SELECT hook_type, COUNT(*) as count, AVG(views) as avg_views,
                    AVG(likes) as avg_likes, AVG(completion_rate) as avg_completion_rate
                FROM video_metrics WHERE {where} AND hook_type IS NOT NULL AND hook_type != ''
                GROUP BY hook_type ORDER BY avg_views DESC
            """, params).fetchall()

            platform_stats = conn.execute(f"""
                SELECT platform, COUNT(*) as count, SUM(views) as total_views,
                    AVG(completion_rate) as avg_completion_rate
                FROM video_metrics WHERE {where}
                GROUP BY platform ORDER BY total_views DESC
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
