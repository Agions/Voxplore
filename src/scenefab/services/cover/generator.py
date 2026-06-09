"""
SceneFab 封面生成器核心逻辑

提供封面生成流程编排：高光帧提取、最佳封面选择、
封面文案生成和视频元数据生成。
"""

import logging
from typing import Any

from scenefab.services.cover.frame_utils import FrameUtilsMixin
from scenefab.services.cover.models import CoverGenerationResult
from scenefab.services.cover.text_utils import TextUtilsMixin

logger = logging.getLogger(__name__)


class CoverGenerator(FrameUtilsMixin, TextUtilsMixin):
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
        cover_texts = self._generate_cover_texts(script_text, platform, num_covers)

        # 4. 生成视频元数据
        metadata = self._generate_metadata(script_text, platform, selected_cover)

        result = CoverGenerationResult(
            highlight_frames=highlight_frames,
            selected_cover=selected_cover,
            cover_texts=cover_texts,
            metadata=metadata,
        )

        logger.info(f"封面生成完成: {len(highlight_frames)} 个高光帧")
        return result


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
