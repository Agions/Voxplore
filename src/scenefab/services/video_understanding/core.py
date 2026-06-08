"""
SceneFab 长视频理解器核心逻辑

提供长视频分段、并行/串行理解、API 客户端初始化等核心功能。
"""

import logging
import time

from scenefab.services.video_understanding.api_adapters import APIAdapterMixin
from scenefab.services.video_understanding.models import (
    LongVideoUnderstandingResult,
    UnderstandingLevel,
    VideoSegment,
)
from scenefab.services.video_understanding.story_builder import StoryBuilderMixin

logger = logging.getLogger(__name__)


class LongVideoUnderstanding(APIAdapterMixin, StoryBuilderMixin):
    """
    长视频理解器

    用于理解长视频（电影、剧集等）的剧情结构和内容。

    使用方法：
        understander = LongVideoUnderstanding()
        result = understander.understand(
            video_path="movie.mp4",
            level=UnderstandingLevel.DEEP,
        )
        print(result.story_graph.synopsis)
        for character in result.story_graph.characters:
            print(f"{character.name}: {character.description}")
    """

    # 分段参数
    SEGMENT_DURATION = 300  # 5 分钟一段
    OVERLAP_DURATION = 30  # 重叠 30 秒

    # 模型配置
    MODEL_CONFIGS = {
        UnderstandingLevel.FLASH: {
            "model": "qwen3.7-flash",
            "max_frames_per_segment": 10,
            "use_api": True,
        },
        UnderstandingLevel.STANDARD: {
            "model": "qwen3.7-max",
            "max_frames_per_segment": 20,
            "use_api": True,
        },
        UnderstandingLevel.DEEP: {
            "model": "gemini-3.1-pro",
            "max_frames_per_segment": 50,
            "use_api": True,
        },
    }

    def __init__(self, api_keys: dict[str, str] | None = None, max_workers: int = 3):
        """
        初始化长视频理解器

        Args:
            api_keys: API 密钥字典 {"qwen": "...", "gemini": "..."}
            max_workers: 并行处理线程数
        """
        self.api_keys = api_keys or {}
        self.max_workers = max_workers
        self._frame_cache: dict[str, list[dict]] = {}  # 帧缓存
        self._init_clients()
        logger.info(f"LongVideoUnderstanding 初始化完成 (workers={max_workers})")

    def _init_clients(self):
        """初始化 API 客户端"""
        # Qwen 客户端
        if "qwen" in self.api_keys:
            try:
                from openai import OpenAI
                self.qwen_client = OpenAI(
                    api_key=self.api_keys["qwen"],
                    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                )
            except Exception as e:
                logger.warning(f"Qwen 客户端初始化失败: {e}")
                self.qwen_client = None
        else:
            self.qwen_client = None

        # Gemini 客户端
        if "gemini" in self.api_keys:
            try:
                import httpx
                self.gemini_client = httpx.Client(timeout=300.0)
                self.gemini_api_key = self.api_keys["gemini"]
            except Exception as e:
                logger.warning(f"Gemini 客户端初始化失败: {e}")
                self.gemini_client = None
        else:
            self.gemini_client = None

    def understand(
        self,
        video_path: str,
        level: UnderstandingLevel = UnderstandingLevel.STANDARD,
        segment_duration: float | None = None,
        parallel: bool = True,
    ) -> LongVideoUnderstandingResult:
        """
        理解长视频

        Args:
            video_path: 视频文件路径
            level: 理解级别
            segment_duration: 分段时长（秒），默认 5 分钟
            parallel: 是否并行处理片段

        Returns:
            LongVideoUnderstandingResult: 理解结果
        """
        start_time = time.time()

        logger.info(f"开始长视频理解: {video_path}, 级别: {level}")

        # 获取视频时长
        video_duration = self._get_video_duration(video_path)

        # 分段
        segments = self._segment_video(
            video_path, video_duration, segment_duration or self.SEGMENT_DURATION
        )

        # 理解每个片段
        if parallel and len(segments) > 1:
            understood_segments = self._understand_parallel(segments, level)
        else:
            understood_segments = self._understand_sequential(segments, level)

        # 构建剧情图谱
        story_graph = self._build_story_graph(understood_segments, level)

        # 计算处理时间
        processing_time = time.time() - start_time

        result = LongVideoUnderstandingResult(
            video_path=video_path,
            video_duration=video_duration,
            understanding_level=level,
            segments=understood_segments,
            story_graph=story_graph,
            processing_time=processing_time,
        )

        logger.info(f"长视频理解完成: 处理时间={processing_time:.2f}秒")
        return result

    def _understand_parallel(self, segments: list, level: UnderstandingLevel) -> list:
        """并行理解视频片段"""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        results = [None] * len(segments)
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_idx = {
                executor.submit(self._understand_segment, seg, level): i
                for i, seg in enumerate(segments)
            }
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    logger.warning(f"片段 {idx} 理解失败: {e}")
                    results[idx] = segments[idx]  # 保留原始片段

        return [r for r in results if r is not None]

    def _understand_sequential(self, segments: list, level: UnderstandingLevel) -> list:
        """串行理解视频片段"""
        understood_segments = []
        for segment in segments:
            try:
                understood_segment = self._understand_segment(segment, level)
                understood_segments.append(understood_segment)
            except Exception as e:
                logger.warning(f"片段理解失败: {e}")
                understood_segments.append(segment)
        return understood_segments

    def _understand_segment(
        self,
        segment: VideoSegment,
        level: UnderstandingLevel,
    ) -> VideoSegment:
        """
        理解单个视频片段

        Args:
            segment: 视频片段
            level: 理解级别

        Returns:
            VideoSegment: 理解后的片段
        """
        config = self.MODEL_CONFIGS.get(level, self.MODEL_CONFIGS[UnderstandingLevel.STANDARD])

        # 提取关键帧
        key_frames = self._extract_key_frames(segment, config["max_frames_per_segment"])
        segment.key_frames = key_frames

        # 调用模型理解
        if config["model"] == "gemini-3.1-pro" and self.gemini_client:
            understanding = self._understand_with_gemini(segment, key_frames)
        elif self.qwen_client:
            understanding = self._understand_with_qwen(segment, key_frames, config["model"])
        else:
            understanding = self._understand_locally(segment, key_frames)

        # 更新片段信息
        segment.summary = understanding.get("summary", "")
        segment.characters = understanding.get("characters", [])
        segment.emotions = understanding.get("emotions", [])
        segment.events = understanding.get("events", [])

        return segment


def understand_long_video(
    video_path: str,
    level: UnderstandingLevel = UnderstandingLevel.STANDARD,
    api_keys: dict[str, str] | None = None,
) -> LongVideoUnderstandingResult:
    """
    便捷函数：理解长视频

    Args:
        video_path: 视频文件路径
        level: 理解级别
        api_keys: API 密钥

    Returns:
        LongVideoUnderstandingResult: 理解结果
    """
    understander = LongVideoUnderstanding(api_keys=api_keys)
    return understander.understand(video_path, level=level)
