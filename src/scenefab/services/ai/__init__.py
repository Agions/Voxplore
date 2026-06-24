"""SceneFab AI 服务模块。"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS = {
    "BaseAIService": ".base",
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
    "SenseVoiceProvider": ".sensevoice_provider",
    "OCRSubtitleExtractor": ".subtitle_extractor",
    "SpeechSubtitleExtractor": ".subtitle_extractor",
    "SubtitleExtractionResult": ".subtitle_extractor",
    "SubtitleMerger": ".subtitle_extractor",
    "SubtitleSegment": ".subtitle_extractor",
    "SubtitleTranslator": ".subtitle_translator",
    "FIRST_PERSON_ANALYSIS_PROMPT": ".vision_providers",
    "VisionAnalyzerFactory": ".vision_providers",
    "VisionProvider": ".vision_providers",
    "VoiceConfig": ".voice_generator",
    "VoiceGenerator": ".voice_generator",
    "VoiceStyle": ".voice_models",
    "TranscriptionResult": ".whisper_asr_provider",
    "TranscriptSegment": ".whisper_asr_provider",
    "WhisperASRProvider": ".whisper_asr_provider",
}


def __getattr__(name: str) -> Any:
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name, __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value


__all__ = list(_EXPORTS)
