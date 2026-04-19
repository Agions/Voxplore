"""
Voxplore AI 服务模块

提供 AI 能力:
- LLM: 大语言模型支持（DeepSeek-V3 主力）
- Vision: 视觉理解（Qwen2.5-VL 72B SOTA）
- Voice: 语音合成（Edge-TTS / F5-TTS）
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
    ProviderType,
    ProviderError,
    RateLimitError,
    CircuitOpenError,
    RetryHandler,
    RateLimiter,
    CircuitBreaker,
)
from .llm_manager import LLMManager

# 视觉相关
from .vision_providers import (
    VisionProvider,
    VisionAnalyzerFactory,
    FIRST_PERSON_ANALYSIS_PROMPT,
)

# 语音相关
from .voice_generator import VoiceGenerator, VoiceConfig, VoiceStyle

# 解说文案生成
from .script_generator import ScriptGenerator
from .script_models import (
    ScriptStyle,
    VoiceTone,
    ScriptConfig,
    ScriptSegment,
    GeneratedScript,
)

# 字幕提取
from .subtitle_extractor import (
    SubtitleSegment,
    SubtitleExtractionResult,
    OCRSubtitleExtractor,
    SpeechSubtitleExtractor,
    SubtitleMerger,
    SubtitleTranslator,
)

# ASR
from .sensevoice_provider import SenseVoiceProvider
from .whisper_asr_provider import WhisperASRProvider, TranscriptionResult, TranscriptSegment

# 场景分析
from .scene_analyzer_v2 import SceneAnalyzer, SceneAnalyzerV2

# 接口抽象
from ..interfaces import (
    IVideoMaker,
    IScriptGenerator,
    IVoiceGenerator,
    ISceneAnalyzer,
    ProgressCallback,
)

# 缓存
from .cache import LLMMemoryCache

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

    # Interfaces
    "IVideoMaker",
    "IScriptGenerator",
    "IVoiceGenerator",
    "ISceneAnalyzer",
    "ProgressCallback",
]
