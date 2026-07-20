"""视频选择服务模块

片段选择策略：叙事优先、情感峰值优先、混合策略
"""

from .segment_selector import (
    SegmentSelector,
    SelectionStrategy,
)

__all__ = [
    "SelectionStrategy",
    "SegmentSelector",
]
