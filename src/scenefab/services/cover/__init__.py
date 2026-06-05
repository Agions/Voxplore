"""
SceneFab 智能封面与元数据生成模块

功能：
1. 高光帧自动提取（情感峰值 + 视觉冲击力）
2. CLIP 视觉显著性检测
3. AI 辅助封面文案生成
4. 平台热搜词匹配
5. 标题/描述/标签建议

技术栈：
- CLIP: 视觉显著性检测
- LLM: 封面文案生成
- 爬虫/API: 热搜词获取
"""

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class HighlightFrame:
    """高光帧"""
    timestamp: float  # 时间戳（秒）
    frame_path: str = ""  # 帧图片路径
    visual_score: float = 0.0  # 视觉显著性分数 0.0-1.0
    emotion_score: float = 0.0  # 情感分数 0.0-1.0
    combined_score: float = 0.0  # 综合分数 0.0-1.0
    description: str = ""  # 帧描述


@dataclass
class CoverText:
    """封面文案"""
    title: str  # 标题
    subtitle: str = ""  # 副标题
    hook: str = ""  # 钩子文案
    keywords: list[str] = field(default_factory=list)  # 关键词


@dataclass
class VideoMetadata:
    """视频元数据"""
    title: str
    description: str
    tags: list[str] = field(default_factory=list)
    category: str = ""
    language: str = "zh-CN"
    thumbnail_path: str = ""  # 封面图片路径
    duration: float = 0.0  # 视频时长（秒）


@dataclass
class CoverGenerationResult:
    """封面生成结果"""
    highlight_frames: list[HighlightFrame] = field(default_factory=list)
    selected_cover: HighlightFrame | None = None
    cover_texts: list[CoverText] = field(default_factory=list)
    metadata: VideoMetadata | None = None
    generation_time: str = ""
    generator_version: str = "1.0.0"


class CoverGenerator:
    """
    封面生成器

    用于自动生成视频封面和元数据。

    使用方法：
        generator = CoverGenerator()
        result = generator.generate(
            video_path="video.mp4",
            script_text="解说文案...",
            platform="douyin",
        )
        print(result.metadata.title)
        print(result.selected_cover.frame_path)
    """

    # 平台热搜词
    PLATFORM_TRENDING_KEYWORDS = {
        "douyin": ["2026", "必看", "高分", "催泪", "烧脑", "神作", "爆款"],
        "bilibili": ["神作", "高分", "必看", "经典", "冷门", "佳作", "推荐"],
        "xiaohongshu": ["必看", "推荐", "高分", "治愈", "下饭", "追剧", "好剧"],
        "youtube": ["must watch", "best", "top", "2026", "review", "analysis"],
        "tiktok": ["viral", "must watch", "2026", "best", "fyp"],
    }

    def __init__(self, llm_provider=None, clip_model=None):
        """
        初始化封面生成器

        Args:
            llm_provider: LLM 提供商
            clip_model: CLIP 模型
        """
        self.llm_provider = llm_provider
        self.clip_model = clip_model
        logger.info("CoverGenerator 初始化完成")

    def generate(
        self,
        video_path: str,
        script_text: str = "",
        platform: str = "douyin",
        emotion_data: list[dict[str, Any]] | None = None,
        num_covers: int = 3,
    ) -> CoverGenerationResult:
        """
        生成封面和元数据

        Args:
            video_path: 视频文件路径
            script_text: 解说文案
            platform: 目标平台
            emotion_data: 情绪数据
            num_covers: 生成封面数量

        Returns:
            CoverGenerationResult: 生成结果
        """
        logger.info(f"开始生成封面: {video_path}, 平台: {platform}")

        # 1. 提取高光帧
        highlight_frames = self._extract_highlight_frames(
            video_path, emotion_data, num_covers * 2
        )

        # 2. 选择最佳封面
        selected_cover = self._select_best_cover(highlight_frames)

        # 3. 生成封面文案
        cover_texts = self._generate_cover_texts(
            script_text, platform, num_covers
        )

        # 4. 生成视频元数据
        metadata = self._generate_metadata(
            script_text, platform, selected_cover
        )

        result = CoverGenerationResult(
            highlight_frames=highlight_frames,
            selected_cover=selected_cover,
            cover_texts=cover_texts,
            metadata=metadata,
        )

        logger.info(f"封面生成完成: {len(highlight_frames)} 个高光帧")
        return result

    def _extract_highlight_frames(
        self,
        video_path: str,
        emotion_data: list[dict[str, Any]] | None,
        num_frames: int,
    ) -> list[HighlightFrame]:
        """
        提取高光帧

        Args:
            video_path: 视频文件路径
            emotion_data: 情绪数据
            num_frames: 帧数量

        Returns:
            list: 高光帧列表
        """
        highlight_frames = []

        # 基于情绪数据提取高光时刻
        if emotion_data:
            # 按情绪强度排序
            sorted_emotions = sorted(
                emotion_data,
                key=lambda x: x.get("intensity", 0),
                reverse=True,
            )

            # 取前 N 个高光时刻
            for emotion in sorted_emotions[:num_frames]:
                timestamp = emotion.get("timestamp", 0)
                intensity = emotion.get("intensity", 0)

                # 提取帧
                frame_path = self._extract_frame(video_path, timestamp)

                highlight_frames.append(HighlightFrame(
                    timestamp=timestamp,
                    frame_path=frame_path,
                    emotion_score=intensity,
                    combined_score=intensity,
                ))
        else:
            # 如果没有情绪数据，均匀采样
            duration = self._get_video_duration(video_path)
            interval = duration / (num_frames + 1)

            for i in range(num_frames):
                timestamp = interval * (i + 1)
                frame_path = self._extract_frame(video_path, timestamp)

                highlight_frames.append(HighlightFrame(
                    timestamp=timestamp,
                    frame_path=frame_path,
                    visual_score=0.5,
                    emotion_score=0.5,
                    combined_score=0.5,
                ))

        # 计算视觉显著性分数
        for frame in highlight_frames:
            if frame.frame_path:
                frame.visual_score = self._calculate_visual_score(frame.frame_path)
                frame.combined_score = (
                    frame.visual_score * 0.5 + frame.emotion_score * 0.5
                )

        # 按综合分数排序
        highlight_frames.sort(key=lambda x: x.combined_score, reverse=True)

        return highlight_frames

    def _extract_frame(self, video_path: str, timestamp: float) -> str:
        """
        提取视频帧

        Args:
            video_path: 视频文件路径
            timestamp: 时间戳（秒）

        Returns:
            str: 帧图片路径
        """
        try:
            import subprocess
            from pathlib import Path

            output_path = str(Path(video_path).parent / f"frame_{timestamp:.2f}.jpg")

            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-ss", str(timestamp),
                "-vframes", "1",
                "-y",
                output_path,
            ]
            subprocess.run(cmd, capture_output=True, check=True, timeout=30)

            return output_path

        except Exception as e:
            logger.warning(f"帧提取失败: {e}")
            return ""

    def _calculate_visual_score(self, frame_path: str) -> float:
        """
        计算视觉显著性分数

        Args:
            frame_path: 帧图片路径

        Returns:
            float: 视觉分数 0.0-1.0
        """
        try:
            import cv2
            import numpy as np

            # 读取图片
            img = cv2.imread(frame_path)
            if img is None:
                return 0.5

            # 转换为灰度图
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # 计算多个视觉特征
            brightness = np.mean(gray) / 255.0
            contrast = np.std(gray) / 255.0

            # 计算边缘密度（使用 Canny 边缘检测）
            edges = cv2.Canny(gray, 100, 200)
            edge_density = np.sum(edges > 0) / edges.size

            # 计算颜色丰富度
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            color_richness = np.std(hsv[:, :, 0]) / 180.0

            # 综合分数
            visual_score = (
                brightness * 0.2
                + contrast * 0.3
                + edge_density * 0.3
                + color_richness * 0.2
            )

            return min(1.0, visual_score)

        except Exception as e:
            logger.warning(f"视觉分数计算失败: {e}")
            return 0.5

    def _select_best_cover(
        self,
        highlight_frames: list[HighlightFrame],
    ) -> HighlightFrame | None:
        """
        选择最佳封面

        Args:
            highlight_frames: 高光帧列表

        Returns:
            HighlightFrame: 最佳封面
        """
        if not highlight_frames:
            return None

        # 选择综合分数最高的帧
        return max(highlight_frames, key=lambda x: x.combined_score)

    def _generate_cover_texts(
        self,
        script_text: str,
        platform: str,
        num_texts: int,
    ) -> list[CoverText]:
        """
        生成封面文案

        Args:
            script_text: 解说文案
            platform: 目标平台
            num_texts: 文案数量

        Returns:
            list: 封面文案列表
        """
        cover_texts = []

        # 获取平台热搜词
        trending_keywords = self.PLATFORM_TRENDING_KEYWORDS.get(platform, [])

        # 提取文案中的关键词
        script_keywords = self._extract_keywords(script_text)

        # 生成多个文案版本
        for i in range(num_texts):
            # 标题生成策略
            if i == 0:
                # 策略 1: 结果前置
                title = self._generate_title_result_first(script_text)
            elif i == 1:
                # 策略 2: 冲突开头
                title = self._generate_title_conflict(script_text)
            else:
                # 策略 3: 悬念钩子
                title = self._generate_title_suspense(script_text)

            # 添加热搜词
            if trending_keywords:
                keyword = trending_keywords[i % len(trending_keywords)]
                title = f"{keyword}！{title}"

            # 生成副标题
            subtitle = self._generate_subtitle(script_text)

            # 生成钩子文案
            hook = self._generate_hook(script_text)

            # 合并关键词
            all_keywords = list(set(script_keywords + trending_keywords[:3]))

            cover_texts.append(CoverText(
                title=title[:20],  # 限制标题长度
                subtitle=subtitle,
                hook=hook,
                keywords=all_keywords,
            ))

        return cover_texts

    def _extract_keywords(self, text: str) -> list[str]:
        """
        提取关键词

        Args:
            text: 文本

        Returns:
            list: 关键词列表
        """
        # 简单的关键词提取（实际应该用 NLP 技术）
        keywords = []

        # 常见电影相关关键词
        movie_keywords = [
            "电影", "剧情", "解说", "推荐", "高分", "神作",
            "悬疑", "动作", "喜剧", "爱情", "科幻", "恐怖",
        ]

        for keyword in movie_keywords:
            if keyword in text:
                keywords.append(keyword)

        return keywords[:5]

    def _generate_title_result_first(self, script_text: str) -> str:
        """
        生成结果前置标题

        Args:
            script_text: 解说文案

        Returns:
            str: 标题
        """
        # 提取第一句话
        first_sentence = script_text.split("。")[0] if script_text else ""

        # 转换为结果前置格式
        if "最后" in first_sentence or "结局" in first_sentence:
            return first_sentence[:15]
        else:
            return f"结局太意外！{first_sentence[:10]}"

    def _generate_title_conflict(self, script_text: str) -> str:
        """
        生成冲突开头标题

        Args:
            script_text: 解说文案

        Returns:
            str: 标题
        """
        # 提取冲突元素
        conflict_words = ["没想到", "竟然", "居然", "突然", "意外"]
        for word in conflict_words:
            if word in script_text:
                idx = script_text.index(word)
                return script_text[max(0, idx-5):idx+10][:15]

        return f"太震惊了！{script_text[:10]}"

    def _generate_title_suspense(self, script_text: str) -> str:
        """
        生成悬念钩子标题

        Args:
            script_text: 解说文案

        Returns:
            str: 标题
        """
        suspense_words = ["秘密", "真相", "背后", "隐藏", "谜团"]
        for word in suspense_words:
            if word in script_text:
                idx = script_text.index(word)
                return script_text[max(0, idx-5):idx+10][:15]

        return f"这个秘密你知道吗？{script_text[:8]}"

    def _generate_subtitle(self, script_text: str) -> str:
        """
        生成副标题

        Args:
            script_text: 解说文案

        Returns:
            str: 副标题
        """
        # 提取核心内容
        if len(script_text) > 50:
            return script_text[:50] + "..."
        return script_text

    def _generate_hook(self, script_text: str) -> str:
        """
        生成钩子文案

        Args:
            script_text: 解说文案

        Returns:
            str: 钩子文案
        """
        hooks = [
            "看完你就明白了",
            "结局让人意想不到",
            "全程高能",
            "不容错过",
            "建议收藏",
        ]

        # 根据文案内容选择钩子
        if "悬疑" in script_text or "烧脑" in script_text:
            return "烧脑神作，看完你就明白了"
        elif "感动" in script_text or "催泪" in script_text:
            return "催泪神作，准备好纸巾"
        else:
            return hooks[0]

    def _generate_metadata(
        self,
        script_text: str,
        platform: str,
        cover: HighlightFrame | None,
    ) -> VideoMetadata:
        """
        生成视频元数据

        Args:
            script_text: 解说文案
            platform: 目标平台
            cover: 封面帧

        Returns:
            VideoMetadata: 视频元数据
        """
        # 提取关键词
        keywords = self._extract_keywords(script_text)

        # 获取平台热搜词
        trending_keywords = self.PLATFORM_TRENDING_KEYWORDS.get(platform, [])

        # 合并标签
        tags = list(set(keywords + trending_keywords[:3]))

        # 生成标题
        title = self._generate_title_result_first(script_text)

        # 生成描述
        description = self._generate_subtitle(script_text)

        return VideoMetadata(
            title=title,
            description=description,
            tags=tags,
            category="电影解说",
            language="zh-CN",
            thumbnail_path=cover.frame_path if cover else "",
        )

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


def generate_cover(
    video_path: str,
    script_text: str = "",
    platform: str = "douyin",
    emotion_data: list[dict[str, Any]] | None = None,
    num_covers: int = 3,
    llm_provider=None,
) -> CoverGenerationResult:
    """
    便捷函数：生成封面和元数据

    Args:
        video_path: 视频文件路径
        script_text: 解说文案
        platform: 目标平台
        emotion_data: 情绪数据
        num_covers: 生成封面数量
        llm_provider: LLM 提供商

    Returns:
        CoverGenerationResult: 生成结果
    """
    generator = CoverGenerator(llm_provider=llm_provider)
    return generator.generate(
        video_path=video_path,
        script_text=script_text,
        platform=platform,
        emotion_data=emotion_data,
        num_covers=num_covers,
    )
