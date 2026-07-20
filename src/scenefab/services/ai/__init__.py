"""SceneFab AI 服务模块。"""

from __future__ import annotations

from typing import Any

from scenefab.utils.lazy_imports import make_lazy_getattr

_EXPORTS = {
    "ServiceHealth": ".base",
    "ServiceStatus": ".base",
    "BaseLLMProvider": ".base_llm_provider",
    "LLMRequest": ".base_llm_provider",
    "LLMResponse": ".base_llm_provider",
    "ProviderType": ".base_llm_provider",
    "ProviderError": ".base_llm_provider",
    "LLMManager": ".llm_manager",
    "SceneAnalyzer": ".scene_analyzer",
    "ScriptGenerator": ".script_generator",
    "StreamingScriptGenerator": ".script_stream",
    "OCRSubtitleExtractor": ".subtitle_extractor",
    "SpeechSubtitleExtractor": ".subtitle_extractor",
    "SubtitleExtractionResult": ".subtitle_extractor",
    "SubtitleMerger": ".subtitle_extractor",
    "SubtitleSegment": ".subtitle_extractor",
    "SubtitleTranslator": ".subtitle_translator",
    "FIRST_PERSON_ANALYSIS_PROMPT": ".vision_providers",
    "VisionProvider": ".vision_providers",
    "VoiceConfig": ".voice_generator",
    "VoiceGenerator": ".voice_generator",
    "VoiceStyle": ".voice_models",
}


def __getattr__(name: str) -> Any:
    return _lazy_getattr(name)


_lazy_getattr = make_lazy_getattr(_EXPORTS, package_name=__name__)


__all__ = list(_EXPORTS)
