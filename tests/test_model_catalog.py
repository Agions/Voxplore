"""Tests for the authoritative AI model catalog."""

from __future__ import annotations

import pytest

from scenefab.services.ai.llm_manager import LLMManager
from scenefab.services.ai.model_catalog import (
    DEFAULT_MODELS,
    MODEL_CATALOG,
    NARRATION_MODEL_STACK,
    ModelProfile,
    provider_models,
    settings_model_options,
)
from scenefab.services.ai.provider_types import LLMRequest, ProviderType

# ---------------------------------------------------------------------------
# All providers that must appear in MODEL_CATALOG
# ---------------------------------------------------------------------------
EXPECTED_PROVIDERS = frozenset(
    {
        "qwen",
        "deepseek",
        "openai",
        "claude",
        "gemini",
        "kimi",
        "glm5",
        "doubao",
        "hunyuan",
        "local",
    }
)

# Roles in NARRATION_MODEL_STACK whose values are actual model identifiers
# (as opposed to TTS / ASR engine names).
MODEL_ROLES = frozenset(
    {
        "video_understanding",
        "script_generation",
        "quality_review",
        "global_review",
        "local_private",
    }
)


# ===================================================================
# Original tests (preserved)
# ===================================================================


def test_catalog_has_current_narration_defaults() -> None:
    assert DEFAULT_MODELS["deepseek"] == "deepseek-v4-pro"
    assert DEFAULT_MODELS["qwen"] == "qwen3.7-max"
    assert DEFAULT_MODELS["openai"] == "gpt-5"
    assert MODEL_CATALOG["local"][0].open_source is True


def test_settings_options_are_catalog_backed() -> None:
    options = settings_model_options()

    assert "deepseek-v4-pro" in options
    assert "qwen3.7-max" in options
    assert "gpt-5" in options


def test_llm_manager_applies_configured_default_model() -> None:
    manager = LLMManager(
        {
            "LLM": {
                "default_provider": "qwen",
                "qwen": {
                    "enabled": True,
                    "api_key": "sk-test",
                    "model": "qwen3.7-plus",
                },
            }
        }
    )

    request = LLMRequest(prompt="test")
    active_request = manager._apply_configured_model(request, ProviderType.QWEN)

    assert request.model == "default"
    assert active_request.model == "qwen3.7-plus"


# ===================================================================
# ModelProfile dataclass tests
# ===================================================================


class TestModelProfile:
    """Tests for the ModelProfile frozen dataclass."""

    def test_basic_construction(self) -> None:
        profile = ModelProfile(
            model="test-model",
            name="Test Model",
            description="A test model",
            max_tokens=4096,
            context_length=128000,
        )
        assert profile.model == "test-model"
        assert profile.name == "Test Model"
        assert profile.vision is False
        assert profile.reasoning is False
        assert profile.open_source is False

    def test_defaults_are_false(self) -> None:
        profile = ModelProfile(
            model="m", name="M", description="d", max_tokens=1, context_length=1
        )
        assert profile.vision is False
        assert profile.reasoning is False
        assert profile.open_source is False

    def test_frozen_raises_on_mutation(self) -> None:
        profile = ModelProfile(
            model="m", name="M", description="d", max_tokens=1, context_length=1
        )
        with pytest.raises(AttributeError):
            profile.model = "other"  # type: ignore[misc]

    def test_as_provider_dict_minimal(self) -> None:
        profile = ModelProfile(
            model="m",
            name="M",
            description="desc",
            max_tokens=100,
            context_length=200,
        )
        result = profile.as_provider_dict()
        assert result == {
            "name": "M",
            "description": "desc",
            "max_tokens": 100,
            "context_length": 200,
        }
        # Boolean flags should be absent when False
        assert "vision" not in result
        assert "reasoning" not in result
        assert "open_source" not in result

    def test_as_provider_dict_all_flags_true(self) -> None:
        profile = ModelProfile(
            model="m",
            name="M",
            description="desc",
            max_tokens=100,
            context_length=200,
            vision=True,
            reasoning=True,
            open_source=True,
        )
        result = profile.as_provider_dict()
        assert result["vision"] is True
        assert result["reasoning"] is True
        assert result["open_source"] is True

    def test_as_provider_dict_partial_flags(self) -> None:
        profile = ModelProfile(
            model="m",
            name="M",
            description="desc",
            max_tokens=100,
            context_length=200,
            vision=True,
        )
        result = profile.as_provider_dict()
        assert result["vision"] is True
        assert "reasoning" not in result
        assert "open_source" not in result


# ===================================================================
# MODEL_CATALOG structure tests
# ===================================================================


class TestModelCatalog:
    """Structural invariants for MODEL_CATALOG."""

    def test_all_expected_providers_present(self) -> None:
        assert set(MODEL_CATALOG.keys()) == EXPECTED_PROVIDERS

    def test_each_entry_contains_model_profiles(self) -> None:
        for provider, profiles in MODEL_CATALOG.items():
            assert isinstance(profiles, tuple), (
                f"{provider}: expected tuple, got {type(profiles).__name__}"
            )
            assert len(profiles) >= 1, f"{provider}: must have at least one model"
            for profile in profiles:
                assert isinstance(profile, ModelProfile), (
                    f"{provider}: expected ModelProfile, got {type(profile).__name__}"
                )

    def test_default_models_first_profile(self) -> None:
        for provider, profiles in MODEL_CATALOG.items():
            assert DEFAULT_MODELS[provider] == profiles[0].model

    def test_open_source_flag_only_on_local(self) -> None:
        for provider, profiles in MODEL_CATALOG.items():
            for profile in profiles:
                if provider == "local":
                    assert profile.open_source is True, (
                        f"local model {profile.model} should be open_source"
                    )
                else:
                    assert profile.open_source is False, (
                        f"{provider}/{profile.model} should not be open_source"
                    )

    def test_unique_model_ids_within_provider(self) -> None:
        for provider, profiles in MODEL_CATALOG.items():
            ids = [p.model for p in profiles]
            assert len(ids) == len(set(ids)), (
                f"{provider}: duplicate model ids {ids}"
            )

    def test_positive_token_limits(self) -> None:
        for provider, profiles in MODEL_CATALOG.items():
            for profile in profiles:
                assert profile.max_tokens > 0, (
                    f"{provider}/{profile.model}: max_tokens must be > 0"
                )
                assert profile.context_length > 0, (
                    f"{provider}/{profile.model}: context_length must be > 0"
                )
                assert profile.context_length >= profile.max_tokens, (
                    f"{provider}/{profile.model}: context_length < max_tokens"
                )


# ===================================================================
# DEFAULT_MODELS tests
# ===================================================================


class TestDefaultModels:
    """Tests for DEFAULT_MODELS derived dict."""

    def test_keys_match_catalog(self) -> None:
        assert set(DEFAULT_MODELS.keys()) == set(MODEL_CATALOG.keys())

    def test_values_are_model_id_strings(self) -> None:
        for _provider, model_id in DEFAULT_MODELS.items():
            assert isinstance(model_id, str)
            assert len(model_id) > 0


# ===================================================================
# NARRATION_MODEL_STACK tests
# ===================================================================


class TestNarrationModelStack:
    """Tests for NARRATION_MODEL_STACK role-to-model mapping."""

    def test_has_expected_roles(self) -> None:
        expected_roles = MODEL_ROLES | {"tts", "voice_clone", "asr"}
        assert set(NARRATION_MODEL_STACK.keys()) == expected_roles

    def test_model_roles_map_to_valid_provider_defaults(self) -> None:
        for role in MODEL_ROLES:
            model_id = NARRATION_MODEL_STACK[role]
            # The model id must appear somewhere in DEFAULT_MODELS
            assert model_id in DEFAULT_MODELS.values(), (
                f"role '{role}': model '{model_id}' not found in DEFAULT_MODELS"
            )

    def test_tts_engine_is_edge_tts(self) -> None:
        assert NARRATION_MODEL_STACK["tts"] == "edge-tts"

    def test_voice_clone_engine(self) -> None:
        assert NARRATION_MODEL_STACK["voice_clone"] == "f5-tts"

    def test_asr_engine(self) -> None:
        assert NARRATION_MODEL_STACK["asr"] == "sensevoice"

    def test_specific_role_defaults(self) -> None:
        assert NARRATION_MODEL_STACK["video_understanding"] == "qwen3.7-max"
        assert NARRATION_MODEL_STACK["script_generation"] == "deepseek-v4-pro"
        assert NARRATION_MODEL_STACK["quality_review"] == "qwen3.7-max"
        assert NARRATION_MODEL_STACK["global_review"] == "claude-opus-4-6"
        assert NARRATION_MODEL_STACK["local_private"] == "qwen3:32b"


# ===================================================================
# provider_models() tests
# ===================================================================


class TestProviderModels:
    """Tests for the provider_models() helper."""

    def test_returns_correct_models_for_known_provider(self) -> None:
        result = provider_models("deepseek")
        assert "deepseek-v4-pro" in result
        assert "deepseek-v4-flash" in result
        assert len(result) == 2

    def test_returns_all_catalog_models_for_provider(self) -> None:
        for provider in EXPECTED_PROVIDERS:
            result = provider_models(provider)
            expected_count = len(MODEL_CATALOG[provider])
            assert len(result) == expected_count, (
                f"{provider}: expected {expected_count} models, got {len(result)}"
            )

    def test_each_value_is_provider_dict(self) -> None:
        result = provider_models("qwen")
        for _model_id, meta in result.items():
            assert isinstance(meta, dict)
            assert "name" in meta
            assert "description" in meta
            assert "max_tokens" in meta
            assert "context_length" in meta

    def test_unknown_provider_returns_empty_dict(self) -> None:
        result = provider_models("nonexistent")
        assert result == {}

    def test_qwen_models_have_vision_flag(self) -> None:
        result = provider_models("qwen")
        for meta in result.values():
            assert meta.get("vision") is True

    def test_local_models_have_open_source_flag(self) -> None:
        result = provider_models("local")
        for meta in result.values():
            assert meta.get("open_source") is True


# ===================================================================
# settings_model_options() tests
# ===================================================================


class TestSettingsModelOptions:
    """Tests for the settings_model_options() helper."""

    def test_returns_list_of_strings(self) -> None:
        options = settings_model_options()
        assert isinstance(options, list)
        assert all(isinstance(o, str) for o in options)

    def test_contains_expected_providers_models(self) -> None:
        options = settings_model_options()
        # The function hard-codes this provider order:
        # deepseek, qwen, openai, claude, gemini, local
        ordered_providers = ("deepseek", "qwen", "openai", "claude", "gemini", "local")
        for provider in ordered_providers:
            for profile in MODEL_CATALOG[provider]:
                assert profile.model in options, (
                    f"{profile.model} from {provider} missing from settings options"
                )

    def test_excludes_non_ordered_providers(self) -> None:
        options = settings_model_options()
        # kimi, glm5, doubao, hunyuan are not in the settings order
        excluded_providers = ("kimi", "glm5", "doubao", "hunyuan")
        for provider in excluded_providers:
            for profile in MODEL_CATALOG[provider]:
                assert profile.model not in options, (
                    f"{profile.model} from {provider} should not be in settings options"
                )

    def test_order_matches_provider_declaration_order(self) -> None:
        options = settings_model_options()
        expected_order = [
            profile.model
            for provider in ("deepseek", "qwen", "openai", "claude", "gemini", "local")
            for profile in MODEL_CATALOG[provider]
        ]
        assert options == expected_order

    def test_no_duplicates(self) -> None:
        options = settings_model_options()
        assert len(options) == len(set(options))

    def test_total_count(self) -> None:
        options = settings_model_options()
        expected = sum(
            len(MODEL_CATALOG[p])
            for p in ("deepseek", "qwen", "openai", "claude", "gemini", "local")
        )
        assert len(options) == expected
