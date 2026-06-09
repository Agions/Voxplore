"""
SceneFab AI 服务模块

提供 AI 能力:
- LLM: 大语言模型支持（DeepSeek-V4 主力）
- Vision: 视觉理解（Qwen3.7 Max/Plus / Gemini 3.5 Flash）
- Voice: 语音合成（Edge-TTS / F5-TTS / PilotTTS / OmniVoice / IndexTTS2）
- Subtitle: 字幕提取与生成
- ASR: 语音识别（SenseVoice）

核心入口:
- MonologueMaker (services/video/monologue_maker.py) — 第一人称解说编排
"""

# LLM 相关
from .base_llm_provider import (
    BaseLLMProvider,
    LLMRequest,
    LLMResponse,
    ProviderError,
    ProviderType,
)

# 缓存
from .cache import LLMMemoryCache
from .llm_manager import LLMManager

# 场景分析
from .scene_analyzer import SceneAnalyzer
from .scene_analyzer_v2 import SceneAnalyzerV2

# 解说文案生成
from .script_generator import ScriptGenerator
from .script_stream import StreamingScriptGenerator

# ASR
from .sensevoice_provider import SenseVoiceProvider

# 字幕提取
from .subtitle_extractor import (
    OCRSubtitleExtractor,
    SpeechSubtitleExtractor,
    SubtitleExtractionResult,
    SubtitleMerger,
    SubtitleSegment,
    SubtitleTranslator,
)

# 视觉相关
from .vision_providers import (
    FIRST_PERSON_ANALYSIS_PROMPT,
    VisionAnalyzerFactory,
    VisionProvider,
)

# 语音相关
from .voice_generator import VoiceConfig, VoiceGenerator
from .voice_models import VoiceStyle
from .whisper_asr_provider import (
    TranscriptionResult,
    TranscriptSegment,
    WhisperASRProvider,
)

__all__ = [
    # LLM
    "BaseLLMProvider",
    "LLMRequest",
    "LLMResponse",
    "ProviderType",
    "ProviderError",
    "LLMManager",
    # Vision
    "VisionProvider",
    "VisionAnalyzerFactory",
    "FIRST_PERSON_ANALYSIS_PROMPT",
    # Voice
    "VoiceGenerator",
    "VoiceConfig",
    "VoiceStyle",
    # Script
    "ScriptGenerator",
    "StreamingScriptGenerator",
    # Subtitle
    "SubtitleSegment",
    "SubtitleExtractionResult",
    "OCRSubtitleExtractor",
    "SpeechSubtitleExtractor",
    "SubtitleMerger",
    "SubtitleTranslator",
    # ASR
    "SenseVoiceProvider",
    "WhisperASRProvider",
    "TranscriptionResult",
    "TranscriptSegment",
    # Cache
    "LLMMemoryCache",
    # Scene Analyzer
    "SceneAnalyzer",
    "SceneAnalyzerV2",
]
