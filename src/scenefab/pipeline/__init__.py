"""
SceneFab 核心处理流水线 V2
性能优化版本：
- 帧分析并行处理
- 批量 API 调用
- 流式处理
- 进度实时反馈
"""

from .config import PipelineConfig
from .emotion_detector import EmotionPeakDetector
from .first_person_extractor import FirstPersonExtractor
from .scene_pipeline import SceneFabPipeline
from .script_generator import ScriptGenerator
from .tts_generator import TTSGenerator

__all__ = [
    "PipelineConfig",
    "EmotionPeakDetector",
    "FirstPersonExtractor",
    "ScriptGenerator",
    "TTSGenerator",
    "SceneFabPipeline",
]
