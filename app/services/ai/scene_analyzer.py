#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
场景分析器兼容模块

⚠️ 已废弃：此文件仅用于向后兼容。
所有功能已移至 scene_analyzer_v2.py。

推荐导入方式:
    from app.services.ai import SceneAnalyzerV2  # 推荐

旧导入（仍可用，但推荐迁移到 V2）:
    from app.services.ai import SceneAnalyzer
    from app.services.ai.scene_analyzer import SceneAnalyzer

迁移指南:
    # 旧
    from app.services.ai.scene_analyzer import SceneAnalyzer
    analyzer = SceneAnalyzer()
    scenes = analyzer.analyze('video.mp4')

    # 新
    from app.services.ai import SceneAnalyzer  # 或 SceneAnalyzerV2
    analyzer = SceneAnalyzer()  # 实际是 SceneAnalyzerV2
    scenes = analyzer.analyze_with_importance('video.mp4')  # V2 增强方法
"""

# 向后兼容：重新导出 V2 中的 SceneAnalyzer（即 SceneAnalyzerV2）
from .scene_analyzer_v2 import (
    SceneAnalyzer,   # 兼容别名，指向 SceneAnalyzerV2
    SceneAnalyzerV2,
    SceneAnalyzer as SceneAnalyzerBase,  # 向后兼容别名
    SCENE_TYPE_PRIORITY,
)

# 向后兼容的便捷函数
from .scene_analyzer_v2 import analyze_video, SceneInfo, AnalysisConfig, SceneType

__all__ = [
    'SceneAnalyzer',          # 主入口（实际是 V2）
    'SceneAnalyzerV2',       # 显式 V2
    'SceneAnalyzerBase',     # 向后兼容别名
    'SceneInfo',
    'AnalysisConfig',
    'SceneType',
    'SCENE_TYPE_PRIORITY',
    'analyze_video',
]
