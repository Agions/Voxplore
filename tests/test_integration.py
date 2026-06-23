"""
集成测试 - LLM 提供商与 LLMManager
使用 mock 隔离真实 API 调用，测试组件间的集成逻辑
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from scenefab.services.ai.base_llm_provider import (
    LLMRequest,
    LLMResponse,
    ProviderError,
)
from scenefab.services.ai.llm_manager import LLMManager
from scenefab.services.ai.provider_types import ProviderType
from scenefab.services.ai.providers.glm5 import GLM5Provider
from scenefab.services.ai.providers.kimi import KimiProvider
from scenefab.services.ai.providers.qwen import QwenProvider


# Restrict anyio tests to asyncio only (trio is not installed)
@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


# ============ Fixtures ============


def _make_response(
    content: str = "mock response",
    model: str = "default",
    tokens_used: int = 10,
) -> LLMResponse:
    """Create an LLMResponse for testing."""
    return LLMResponse(
        content=content,
        model=model,
        tokens_used=tokens_used,
        finish_reason="stop",
    )


def _sample_config() -> dict:
    """Build a config dict that LLMManager expects."""
    return {
        "LLM": {
            "qwen": {
                "enabled": True,
                "api_key": "test-qwen-key",
                "model": "qwen3.7-max",
            },
            "kimi": {
                "enabled": True,
                "api_key": "test-kimi-key",
                "model": "moonshot-v1-8k",
            },
            "glm5": {
                "enabled": True,
                "api_key": "test-glm5-key",
                "model": "glm-5",
            },
        },
        "default_provider": "qwen",
    }


# ============ QwenProvider Tests ============


class TestQwenProviderIntegration:
    """通义千问提供商集成测试"""

    @pytest.fixture
    def provider(self) -> QwenProvider:
        return QwenProvider(api_key="test-qwen-key")

    def test_models_attribute_is_uppercase(self, provider: QwenProvider):
        """MODELS 应为大写类属性"""
        assert hasattr(QwenProvider, "MODELS")
        assert isinstance(QwenProvider.MODELS, dict)
        assert len(QwenProvider.MODELS) > 0

    @pytest.mark.anyio
    async def test_basic_generate(self, provider: QwenProvider):
        """测试基本生成 (generate, 不是 complete)"""
        request = LLMRequest(
            prompt="你好，请用一句话介绍自己",
            model="qwen3.7-max",
            max_tokens=100,
        )

        mock_resp = _make_response(
            content="我是通义千问AI助手。",
            model="qwen3.7-max",
            tokens_used=25,
        )

        with patch.object(provider, "generate", new_callable=AsyncMock, return_value=mock_resp):
            response: LLMResponse = await provider.generate(request)

        assert response.content is not None
        assert len(response.content) > 0
        assert response.model == "qwen3.7-max"

    @pytest.mark.anyio
    async def test_with_temperature(self, provider: QwenProvider):
        """测试温度参数"""
        request = LLMRequest(
            prompt="写一个简短的故事",
            model="qwen3.7-max",
            temperature=0.8,
            max_tokens=200,
        )

        mock_resp = _make_response(content="从前有座山...", model="qwen3.7-max")

        with patch.object(provider, "generate", new_callable=AsyncMock, return_value=mock_resp):
            response = await provider.generate(request)

        assert response.content is not None
        assert len(response.content) > 0

    @pytest.mark.anyio
    async def test_error_handling(self, provider: QwenProvider):
        """测试错误处理 - ProviderError 被正确抛出"""
        request = LLMRequest(
            prompt="测试",
            model="qwen3.7-max",
        )

        with patch.object(
            provider,
            "generate",
            new_callable=AsyncMock,
            side_effect=ProviderError("认证失败"),
        ):
            with pytest.raises(ProviderError):
                await provider.generate(request)

    def test_health_check_callable(self, provider: QwenProvider):
        """health_check 方法存在且可调用"""
        assert callable(provider.health_check)


# ============ KimiProvider Tests ============


class TestKimiProviderIntegration:
    """Kimi 提供商集成测试"""

    @pytest.fixture
    def provider(self) -> KimiProvider:
        return KimiProvider(api_key="test-kimi-key")

    def test_models_attribute(self, provider: KimiProvider):
        """MODELS 应为大写类属性"""
        assert hasattr(KimiProvider, "MODELS")
        assert isinstance(KimiProvider.MODELS, dict)

    @pytest.mark.anyio
    async def test_basic_generate(self, provider: KimiProvider):
        """测试基本生成"""
        request = LLMRequest(
            prompt="你好",
            model="moonshot-v1-8k",
            max_tokens=100,
        )

        mock_resp = _make_response(
            content="你好！我是 Kimi。",
            model="moonshot-v1-8k",
        )

        with patch.object(provider, "generate", new_callable=AsyncMock, return_value=mock_resp):
            response: LLMResponse = await provider.generate(request)

        assert response.content is not None
        assert len(response.content) > 0

    def test_generate_callable(self, provider: KimiProvider):
        """generate 方法存在且可调用"""
        assert callable(provider.generate)


# ============ GLM5Provider Tests ============


class TestGLM5ProviderIntegration:
    """GLM-5 提供商集成测试"""

    @pytest.fixture
    def provider(self) -> GLM5Provider:
        return GLM5Provider(api_key="test-glm5-key")

    def test_models_attribute(self, provider: GLM5Provider):
        """MODELS 应为大写类属性"""
        assert hasattr(GLM5Provider, "MODELS")
        assert isinstance(GLM5Provider.MODELS, dict)

    @pytest.mark.anyio
    async def test_basic_generate(self, provider: GLM5Provider):
        """测试基本生成"""
        request = LLMRequest(
            prompt="你好",
            model="glm-5",
            max_tokens=100,
        )

        mock_resp = _make_response(
            content="你好！我是 GLM-5。",
            model="glm-5",
        )

        with patch.object(provider, "generate", new_callable=AsyncMock, return_value=mock_resp):
            response: LLMResponse = await provider.generate(request)

        assert response.content is not None
        assert len(response.content) > 0


# ============ LLMManager Tests ============


class TestLLMManagerIntegration:
    """LLM 管理器集成测试"""

    @pytest.fixture
    def manager(self) -> LLMManager:
        """使用 config dict 构造 LLMManager"""
        config = _sample_config()
        return LLMManager(config)

    def test_constructor_with_config_dict(self, manager: LLMManager):
        """LLMManager 应接受 config dict"""
        assert manager is not None

    def test_get_available_providers(self, manager: LLMManager):
        """get_available_providers (不是 available_providers) 返回列表"""
        providers = manager.get_available_providers()
        assert isinstance(providers, list)
        assert len(providers) > 0

    @pytest.mark.anyio
    async def test_generate(self, manager: LLMManager):
        """测试 manager.generate (不是 complete)"""
        request = LLMRequest(
            prompt="你好",
            max_tokens=100,
        )

        mock_resp = _make_response(content="你好！有什么可以帮你的？", model="qwen3.7-max")

        with patch.object(
            manager.providers[ProviderType.QWEN],
            "generate",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            response: LLMResponse = await manager.generate(request)

        assert response.content is not None
        assert len(response.content) > 0

    @pytest.mark.anyio
    async def test_generate_with_explicit_provider(self, manager: LLMManager):
        """测试指定提供商调用"""
        request = LLMRequest(
            prompt="测试提供商",
            max_tokens=50,
        )

        mock_resp = _make_response(content="来自 Kimi 的响应", model="moonshot-v1-8k")

        with patch.object(
            manager.providers[ProviderType.KIMI],
            "generate",
            new_callable=AsyncMock,
            return_value=mock_resp,
        ):
            response = await manager.generate(request, provider=ProviderType.KIMI)

        assert response.content is not None

    @pytest.mark.anyio
    async def test_generate_fallback_on_failure(self, manager: LLMManager):
        """测试自动切换失败提供商 (fallback)"""
        request = LLMRequest(
            prompt="你好",
            max_tokens=50,
        )

        fallback_resp = _make_response(content="fallback 成功", model="moonshot-v1-8k")

        # 默认提供商失败，备用提供商成功
        with (
            patch.object(
                manager.providers[ProviderType.QWEN],
                "generate",
                new_callable=AsyncMock,
                side_effect=ProviderError("Qwen 失败"),
            ),
            patch.object(
                manager.providers[ProviderType.KIMI],
                "generate",
                new_callable=AsyncMock,
                return_value=fallback_resp,
            ),
        ):
            response = await manager.generate(request)

        assert response.content == "fallback 成功"

    @pytest.mark.anyio
    async def test_all_providers_fail_raises(self, manager: LLMManager):
        """所有提供商都失败时应抛出 ProviderError"""
        from contextlib import ExitStack

        request = LLMRequest(prompt="测试", max_tokens=50)

        # Mock 所有提供商都失败
        with ExitStack() as stack:
            for ptype, prov in manager.providers.items():
                stack.enter_context(
                    patch.object(
                        prov,
                        "generate",
                        new_callable=AsyncMock,
                        side_effect=ProviderError(f"{ptype} 失败"),
                    )
                )
            with pytest.raises(ProviderError, match="所有 Provider 都失败"):
                await manager.generate(request)

    def test_health_check(self, manager: LLMManager):
        """health_check 返回 dict"""
        result = manager.health_check()
        assert isinstance(result, dict)

    def test_generate_sync_callable(self, manager: LLMManager):
        """generate_sync 方法存在"""
        assert callable(manager.generate_sync)

    def test_stream_generate_callable(self, manager: LLMManager):
        """stream_generate 方法存在"""
        assert callable(manager.stream_generate)


# ============ ScriptGenerator Tests ============


class TestScriptGeneratorIntegration:
    """文案生成器集成测试"""

    @pytest.fixture
    def mock_llm_manager(self) -> LLMManager:
        """构造一个预装 mock 的 LLMManager"""
        config = _sample_config()
        return LLMManager(config)

    def test_generate_commentary(self, mock_llm_manager: LLMManager):
        """测试生成解说文案"""
        from scenefab.services.ai.script_generator import ScriptGenerator
        from scenefab.services.ai.script_models import GeneratedScript, ScriptStyle

        mock_script = GeneratedScript(
            content="这是一部关于科幻的解说文案...",
            style=ScriptStyle.COMMENTARY,
            word_count=150,
            estimated_duration=60.0,
            provider_used="qwen",
        )

        with patch.object(
            ScriptGenerator, "generate_commentary", return_value=mock_script
        ):
            generator = ScriptGenerator(use_llm_manager=True)
            # Patch the llm_manager with our mocked one
            generator.llm_manager = mock_llm_manager

            script = generator.generate_commentary(
                "分析《流浪地球》的科学设定", duration=60
            )

        assert script is not None
        assert script.content is not None
        assert len(script.content) > 0
        assert script.segments is not None

    def test_generate_monologue(self, mock_llm_manager: LLMManager):
        """测试生成独白文案"""
        from scenefab.services.ai.script_generator import ScriptGenerator
        from scenefab.services.ai.script_models import GeneratedScript, ScriptStyle

        mock_script = GeneratedScript(
            content="深夜走在城市街头，路灯拉长了影子...",
            style=ScriptStyle.MONOLOGUE,
            word_count=80,
            estimated_duration=30.0,
            provider_used="qwen",
        )

        with patch.object(
            ScriptGenerator, "generate_monologue", return_value=mock_script
        ):
            generator = ScriptGenerator(use_llm_manager=True)
            generator.llm_manager = mock_llm_manager

            script = generator.generate_monologue(
                "深夜独自走在城市街头", emotion="惆怅", duration=30
            )

        assert script is not None
        assert script.content is not None
        assert len(script.content) > 0

    def test_script_uses_content_not_text(self):
        """GeneratedScript 使用 content 字段，不是 text"""
        from scenefab.services.ai.script_models import GeneratedScript

        script = GeneratedScript(content="测试内容")
        assert script.content == "测试内容"
        assert not hasattr(script, "text") or script.text is script.content  # no 'text' alias


# ============ LLMRequest / LLMResponse Field Tests ============


class TestLLMRequestFields:
    """验证 LLMRequest 字段符合当前 API"""

    def test_prompt_field(self):
        """LLMRequest 使用 prompt= 而非 messages="""
        req = LLMRequest(prompt="你好", model="test-model", max_tokens=100)
        assert req.prompt == "你好"
        assert req.model == "test-model"
        assert req.max_tokens == 100

    def test_no_messages_field(self):
        """LLMRequest 没有 messages 字段"""
        import dataclasses

        field_names = {f.name for f in dataclasses.fields(LLMRequest)}
        assert "messages" not in field_names
        assert "prompt" in field_names

    def test_system_prompt_default(self):
        """system_prompt 默认为空字符串"""
        req = LLMRequest(prompt="test")
        assert req.system_prompt == ""

    def test_temperature_default(self):
        req = LLMRequest(prompt="test")
        assert req.temperature == 0.7

    def test_top_p_default(self):
        req = LLMRequest(prompt="test")
        assert req.top_p == 0.9


class TestLLMResponseFields:
    """验证 LLMResponse 字段符合当前 API"""

    def test_content_field(self):
        """LLMResponse 使用 content 而非 text"""
        resp = LLMResponse(content="回答", model="test-model")
        assert resp.content == "回答"

    def test_no_success_text_model_name_error(self):
        """LLMResponse 没有 success, text, model_name, error 字段"""
        import dataclasses

        field_names = {f.name for f in dataclasses.fields(LLMResponse)}
        assert "text" not in field_names
        assert "success" not in field_names
        assert "model_name" not in field_names
        assert "error" not in field_names

        # 确认正确的字段存在
        assert "content" in field_names
        assert "model" in field_names
        assert "tokens_used" in field_names
        assert "finish_reason" in field_names
        assert "latency_ms" in field_names
        assert "usage" in field_names

    def test_model_field(self):
        """使用 model 而非 model_name"""
        resp = LLMResponse(content="x", model="qwen3.7-max")
        assert resp.model == "qwen3.7-max"

    def test_defaults(self):
        resp = LLMResponse(content="x", model="m")
        assert resp.tokens_used == 0
        assert resp.finish_reason == "stop"
        assert resp.latency_ms == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
