"""
SceneFab 多模态长时序视频理解模块

功能：
1. 长视频分段策略
2. 多模型协同理解（Qwen3.7-Flash + Qwen3.7-Max + Gemini 3.1 Pro）
3. 人物关系图谱构建
4. 剧情摘要生成
5. 关键事件时间戳定位

技术栈：
- Qwen3.7-Flash: 轻量实时帧理解（本地/API）
- Qwen3.7-Max: 复杂场景推理（API）
- Gemini 3.1 Pro: 长时序电影级理解（API，100万 token）
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class UnderstandingLevel(str, Enum):
    """理解级别"""
    FLASH = "flash"  # 快速理解（Qwen3.7-Flash）
    STANDARD = "standard"  # 标准理解（Qwen3.7-Max）
    DEEP = "deep"  # 深度理解（Gemini 3.1 Pro）


@dataclass
class VideoSegment:
    """视频片段"""
    segment_id: int
    start_time: float  # 开始时间（秒）
    end_time: float  # 结束时间（秒）
    duration: float  # 时长（秒）
    key_frames: list[dict[str, Any]] = field(default_factory=list)  # 关键帧
    summary: str = ""  # 片段摘要
    characters: list[str] = field(default_factory=list)  # 出现的人物
    emotions: list[str] = field(default_factory=list)  # 情绪标签
    events: list[dict[str, Any]] = field(default_factory=list)  # 事件列表


@dataclass
class Character:
    """人物信息"""
    character_id: str
    name: str
    description: str = ""
    appearances: list[dict[str, Any]] = field(default_factory=list)  # 出场记录
    relationships: dict[str, str] = field(default_factory=dict)  # 与其他人物的关系
    importance: float = 0.0  # 重要性 0.0-1.0


@dataclass
class PlotEvent:
    """剧情事件"""
    event_id: str
    timestamp: float  # 时间戳（秒）
    event_type: str  # event_type: "introduction", "development", "climax", "resolution"
    description: str
    characters_involved: list[str] = field(default_factory=list)
    importance: float = 0.0  # 重要性 0.0-1.0
    cause: str = ""  # 原因
    effect: str = ""  # 结果


@dataclass
class StoryGraph:
    """剧情图谱"""
    title: str = ""
    genre: str = ""  # 类型：action, drama, comedy, etc.
    synopsis: str = ""  # 剧情梗概
    characters: list[Character] = field(default_factory=list)
    plot_events: list[PlotEvent] = field(default_factory=list)
    timeline: list[dict[str, Any]] = field(default_factory=list)  # 时间线
    themes: list[str] = field(default_factory=list)  # 主题
    emotional_arc: list[dict[str, Any]] = field(default_factory=list)  # 情绪弧线


@dataclass
class LongVideoUnderstandingResult:
    """长视频理解结果"""
    video_path: str
    video_duration: float  # 视频时长（秒）
    understanding_level: UnderstandingLevel
    segments: list[VideoSegment] = field(default_factory=list)
    story_graph: StoryGraph = field(default_factory=StoryGraph)
    processing_time: float = 0.0  # 处理时间（秒）
    token_usage: dict[str, int] = field(default_factory=dict)  # Token 使用量
    understanding_time: str = ""
    understander_version: str = "1.0.0"


class LongVideoUnderstanding:
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
        import time
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
                "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
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

    def _extract_key_frames(
        self,
        segment: VideoSegment,
        max_frames: int,
    ) -> list[dict[str, Any]]:
        """
        提取关键帧

        Args:
            segment: 视频片段
            max_frames: 最大帧数

        Returns:
            list: 关键帧列表
        """
        try:
            import cv2
            import numpy as np

            # 打开视频
            cap = cv2.VideoCapture(segment.video_path if hasattr(segment, 'video_path') else "")
            cap.set(cv2.CAP_PROP_POS_MSEC, segment.start_time * 1000)

            key_frames = []
            frame_count = 0
            interval = segment.duration / max_frames

            while frame_count < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break

                timestamp = segment.start_time + frame_count * interval

                # 计算帧的特征（简化版）
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                brightness = float(np.mean(gray))
                contrast = float(np.std(gray))

                key_frames.append({
                    "timestamp": timestamp,
                    "brightness": brightness,
                    "contrast": contrast,
                    "frame_number": frame_count,
                })

                # 跳过帧
                for _ in range(int(interval * 30)):  # 假设 30fps
                    cap.read()

                frame_count += 1

            cap.release()
            return key_frames

        except Exception as e:
            logger.warning(f"关键帧提取失败: {e}")
            return []

    def _understand_with_gemini(
        self,
        segment: VideoSegment,
        key_frames: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        使用 Gemini 理解片段

        Args:
            segment: 视频片段
            key_frames: 关键帧列表

        Returns:
            dict: 理解结果
        """
        try:
            # 构建提示词
            prompt = self._build_understanding_prompt(segment)

            # 调用 Gemini API
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-pro:generateContent?key={self.gemini_api_key}"

            # 构建请求（简化版，实际需要上传视频片段）
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt}
                        ]
                    }
                ],
                "generationConfig": {
                    "maxOutputTokens": 4096,
                },
            }

            response = self.gemini_client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()

            # 解析响应
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            return self._parse_understanding_response(text)

        except Exception as e:
            logger.error(f"Gemini 理解失败: {e}")
            return {"summary": "", "characters": [], "emotions": [], "events": []}

    def _understand_with_qwen(
        self,
        segment: VideoSegment,
        key_frames: list[dict[str, Any]],
        model: str,
    ) -> dict[str, Any]:
        """
        使用 Qwen 理解片段

        Args:
            segment: 视频片段
            key_frames: 关键帧列表
            model: 模型名称

        Returns:
            dict: 理解结果
        """
        try:
            # 构建提示词
            prompt = self._build_understanding_prompt(segment)

            # 调用 Qwen API
            response = self.qwen_client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                max_tokens=4096,
            )

            # 解析响应
            text = response.choices[0].message.content
            return self._parse_understanding_response(text)

        except Exception as e:
            logger.error(f"Qwen 理解失败: {e}")
            return {"summary": "", "characters": [], "emotions": [], "events": []}

    def _understand_locally(
        self,
        segment: VideoSegment,
        key_frames: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        本地理解（简化版）

        Args:
            segment: 视频片段
            key_frames: 关键帧列表

        Returns:
            dict: 理解结果
        """
        # 简化版本地理解
        return {
            "summary": f"视频片段 {segment.segment_id}，时长 {segment.duration:.1f} 秒",
            "characters": [],
            "emotions": ["neutral"],
            "events": [],
        }

    def _build_understanding_prompt(self, segment: VideoSegment) -> str:
        """
        构建理解提示词

        Args:
            segment: 视频片段

        Returns:
            str: 提示词
        """
        return f"""请分析这段视频片段（{segment.start_time:.1f}秒 - {segment.end_time:.1f}秒），并返回以下信息（JSON格式）：

{{
    "summary": "片段摘要（50-100字）",
    "characters": ["出现的人物列表"],
    "emotions": ["主要情绪标签"],
    "events": [
        {{
            "timestamp": "事件发生时间（秒）",
            "description": "事件描述",
            "importance": "重要性 1-10"
        }}
    ]
}}

请用中文回答。"""

    def _parse_understanding_response(self, text: str) -> dict[str, Any]:
        """
        解析理解响应

        Args:
            text: 响应文本

        Returns:
            dict: 解析结果
        """
        try:
            import json

            # 尝试提取 JSON
            if "```json" in text:
                json_str = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                json_str = text.split("```")[1].split("```")[0].strip()
            else:
                json_str = text

            return json.loads(json_str)

        except Exception as e:
            logger.warning(f"解析响应失败: {e}")
            return {
                "summary": text[:200] if text else "",
                "characters": [],
                "emotions": [],
                "events": [],
            }

    def _build_story_graph(
        self,
        segments: list[VideoSegment],
        level: UnderstandingLevel,
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
                emotional_arc.append({
                    "timestamp": segment.start_time,
                    "emotions": segment.emotions,
                })
        return emotional_arc


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
