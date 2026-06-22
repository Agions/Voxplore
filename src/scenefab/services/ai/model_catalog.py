"""Authoritative model catalog for SceneFab AI workflows.

The catalog keeps provider defaults, settings options, and documentation from
drifting apart. It intentionally lists only the current preferred models for
first-person film and short-drama narration.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelProfile:
    """Normalized model metadata used by provider adapters."""

    model: str
    name: str
    description: str
    max_tokens: int
    context_length: int
    vision: bool = False
    reasoning: bool = False
    open_source: bool = False

    def as_provider_dict(self) -> dict[str, int | str | bool]:
        """Return the legacy provider metadata shape."""
        data: dict[str, int | str | bool] = {
            "name": self.name,
            "description": self.description,
            "max_tokens": self.max_tokens,
            "context_length": self.context_length,
        }
        if self.vision:
            data["vision"] = True
        if self.reasoning:
            data["reasoning"] = True
        if self.open_source:
            data["open_source"] = True
        return data


MODEL_CATALOG: dict[str, tuple[ModelProfile, ...]] = {
    "qwen": (
        ModelProfile(
            model="qwen3.7-max",
            name="Qwen3.7 Max",
            description="Chinese-first multimodal reasoning model for story and scene understanding",
            max_tokens=32768,
            context_length=1_000_000,
            vision=True,
            reasoning=True,
        ),
        ModelProfile(
            model="qwen3.7-plus",
            name="Qwen3.7 Plus",
            description="High-throughput multimodal model for batch short-drama analysis",
            max_tokens=16384,
            context_length=1_000_000,
            vision=True,
        ),
    ),
    "deepseek": (
        ModelProfile(
            model="deepseek-v4-pro",
            name="DeepSeek V4 Pro",
            description="Primary Chinese narration and rewrite model with strong reasoning",
            max_tokens=32768,
            context_length=1_000_000,
            reasoning=True,
        ),
        ModelProfile(
            model="deepseek-v4-flash",
            name="DeepSeek V4 Flash",
            description="Fast script iteration model for hook rewrites and batch drafts",
            max_tokens=16384,
            context_length=1_000_000,
        ),
    ),
    "openai": (
        ModelProfile(
            model="gpt-5",
            name="GPT-5",
            description="International general-purpose model for high-precision planning and review",
            max_tokens=32768,
            context_length=1_000_000,
            vision=True,
            reasoning=True,
        ),
        ModelProfile(
            model="gpt-5-mini",
            name="GPT-5 Mini",
            description="Lower-latency model for lightweight creative variants",
            max_tokens=16384,
            context_length=1_000_000,
            vision=True,
        ),
    ),
    "claude": (
        ModelProfile(
            model="claude-opus-4-6",
            name="Claude Opus 4.6",
            description="Long-form reasoning model for structural critique and consistency review",
            max_tokens=16384,
            context_length=200000,
            vision=True,
            reasoning=True,
        ),
        ModelProfile(
            model="claude-sonnet-4-5",
            name="Claude Sonnet 4.5",
            description="Balanced model for production writing and editorial review",
            max_tokens=16384,
            context_length=200000,
            vision=True,
        ),
    ),
    "gemini": (
        ModelProfile(
            model="gemini-3.1-pro",
            name="Gemini 3.1 Pro",
            description="Global multimodal model for long-context video understanding",
            max_tokens=8192,
            context_length=2_000_000,
            vision=True,
            reasoning=True,
        ),
        ModelProfile(
            model="gemini-3.1-flash",
            name="Gemini 3.1 Flash",
            description="Fast global multimodal model for low-latency analysis",
            max_tokens=8192,
            context_length=1_000_000,
            vision=True,
        ),
    ),
    "kimi": (
        ModelProfile(
            model="moonshot-v1-128k",
            name="Kimi 128K",
            description="Chinese long-context assistant for reference-heavy scripts",
            max_tokens=8000,
            context_length=128000,
        ),
    ),
    "glm5": (
        ModelProfile(
            model="glm-5-plus",
            name="GLM-5 Plus",
            description="Zhipu flagship text model for Chinese editorial tasks",
            max_tokens=16384,
            context_length=128000,
            reasoning=True,
        ),
        ModelProfile(
            model="glm-5-flash",
            name="GLM-5 Flash",
            description="Fast Zhipu model for lightweight generation",
            max_tokens=8192,
            context_length=128000,
        ),
    ),
    "doubao": (
        ModelProfile(
            model="doubao-pro-128k",
            name="Doubao Pro 128K",
            description="Volcano Engine long-context model for production batches",
            max_tokens=64000,
            context_length=128000,
        ),
    ),
    "hunyuan": (
        ModelProfile(
            model="hunyuan-pro",
            name="Hunyuan Pro",
            description="Tencent flagship model for Chinese generation and review",
            max_tokens=8000,
            context_length=128000,
        ),
    ),
    "local": (
        ModelProfile(
            model="qwen3:32b",
            name="Qwen3 32B",
            description="Recommended open-source local model for private narration drafting",
            max_tokens=8192,
            context_length=128000,
            open_source=True,
        ),
        ModelProfile(
            model="deepseek-r1:32b",
            name="DeepSeek-R1 32B",
            description="Recommended open-source local reasoning model",
            max_tokens=8192,
            context_length=128000,
            reasoning=True,
            open_source=True,
        ),
    ),
}

DEFAULT_MODELS = {
    provider: profiles[0].model for provider, profiles in MODEL_CATALOG.items()
}

NARRATION_MODEL_STACK = {
    "video_understanding": DEFAULT_MODELS["qwen"],
    "script_generation": DEFAULT_MODELS["deepseek"],
    "quality_review": DEFAULT_MODELS["qwen"],
    "global_review": DEFAULT_MODELS["claude"],
    "local_private": DEFAULT_MODELS["local"],
    "tts": "edge-tts",
    "voice_clone": "f5-tts",
    "asr": "sensevoice",
}


def provider_models(provider: str) -> dict[str, dict[str, int | str | bool]]:
    """Return provider metadata keyed by model name."""
    return {
        profile.model: profile.as_provider_dict()
        for profile in MODEL_CATALOG.get(provider, ())
    }


def settings_model_options() -> list[str]:
    """Model names exposed in project settings."""
    ordered_providers = ("deepseek", "qwen", "openai", "claude", "gemini", "local")
    return [
        profile.model
        for provider in ordered_providers
        for profile in MODEL_CATALOG[provider]
    ]


__all__ = [
    "DEFAULT_MODELS",
    "MODEL_CATALOG",
    "NARRATION_MODEL_STACK",
    "ModelProfile",
    "provider_models",
    "settings_model_options",
]
