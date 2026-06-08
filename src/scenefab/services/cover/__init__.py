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

from scenefab.services.cover.generator import CoverGenerator, generate_cover
from scenefab.services.cover.models import (
    CoverGenerationResult,
    CoverText,
    HighlightFrame,
    VideoMetadata,
)

__all__ = [
    "CoverGenerationResult",
    "CoverGenerator",
    "CoverText",
    "HighlightFrame",
    "VideoMetadata",
    "generate_cover",
]
