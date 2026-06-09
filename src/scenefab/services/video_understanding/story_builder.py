"""
SceneFab 剧情图谱构建混入

提供剧情图谱构建、摘要生成和情绪弧线生成等方法。
"""

import logging
from typing import Any

from scenefab.services.video_understanding.models import (
    Character,
    PlotEvent,
    StoryGraph,
    VideoSegment,
)

logger = logging.getLogger(__name__)


class StoryBuilderMixin:
    """剧情图谱构建混入类"""

    def _get_video_duration(self, video_path: str) -> float:
        """
        获取视频时长

        Args:
            video_path: 视频文件路径

        Returns:
            float: 视频时长（秒）
        """
        try:
            import subprocess

            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                video_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return float(result.stdout.strip())
        except Exception as e:
            logger.warning(f"获取视频时长失败: {e}")
            return 0.0

    def _segment_video(
        self,
        video_path: str,
        video_duration: float,
        segment_duration: float,
    ) -> list[VideoSegment]:
        """
        将视频分段

        Args:
            video_path: 视频文件路径
            video_duration: 视频时长
            segment_duration: 分段时长

        Returns:
            list: 视频片段列表
        """
        segments = []
        segment_id = 0
        start_time = 0.0

        while start_time < video_duration:
            end_time = min(start_time + segment_duration, video_duration)
            duration = end_time - start_time

            segment = VideoSegment(
                segment_id=segment_id,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
            )
            segments.append(segment)

            # 下一段（考虑重叠）
            start_time = end_time - self.OVERLAP_DURATION
            segment_id += 1

        logger.info(f"视频分段完成: {len(segments)} 个片段")
        return segments

    def _build_story_graph(
        self,
        segments: list[VideoSegment],
        level: Any,
    ) -> StoryGraph:
        """
        构建剧情图谱

        Args:
            segments: 视频片段列表
            level: 理解级别

        Returns:
            StoryGraph: 剧情图谱
        """
        # 收集所有人物
        all_characters = set()
        for segment in segments:
            all_characters.update(segment.characters)

        # 创建人物对象
        characters = []
        for char_name in all_characters:
            character = Character(
                character_id=char_name.lower().replace(" ", "_"),
                name=char_name,
            )
            characters.append(character)

        # 收集所有事件
        all_events = []
        for segment in segments:
            for event in segment.events:
                plot_event = PlotEvent(
                    event_id=f"event_{len(all_events)}",
                    timestamp=event.get("timestamp", 0),
                    event_type="development",
                    description=event.get("description", ""),
                    importance=event.get("importance", 5) / 10.0,
                )
                all_events.append(plot_event)

        # 生成剧情摘要
        synopsis = self._generate_synopsis(segments)

        # 生成情绪弧线
        emotional_arc = self._generate_emotional_arc(segments)

        return StoryGraph(
            title="",
            genre="",
            synopsis=synopsis,
            characters=characters,
            plot_events=all_events,
            emotional_arc=emotional_arc,
        )

    def _generate_synopsis(self, segments: list[VideoSegment]) -> str:
        """
        生成剧情摘要

        Args:
            segments: 视频片段列表

        Returns:
            str: 剧情摘要
        """
        # 合并所有片段摘要
        summaries = [s.summary for s in segments if s.summary]
        if not summaries:
            return ""

        # 简单合并（实际应该用 LLM 生成更好的摘要）
        return " ".join(summaries[:5])  # 取前 5 个片段的摘要

    def _generate_emotional_arc(
        self,
        segments: list[VideoSegment],
    ) -> list[dict[str, Any]]:
        """
        生成情绪弧线

        Args:
            segments: 视频片段列表

        Returns:
            list: 情绪弧线数据
        """
        emotional_arc = []
        for segment in segments:
            if segment.emotions:
                emotional_arc.append(
                    {
                        "timestamp": segment.start_time,
                        "emotions": segment.emotions,
                    }
                )
        return emotional_arc
