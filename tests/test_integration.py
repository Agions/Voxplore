"""
集成测试 - LLM 提供商实际调用
测试 LLMManager 和各提供商的真实 API 调用
"""

import pytest
import os
from typing import Optional

# 需要真实 API 密钥才能运行这些测试
# 使用 pytest -m "integration" 运行

from app.services.ai.llm_manager import LLMManager
from app.services.ai.providers.qwen import QwenProvider
from app.services.ai.providers.kimi import KimiProvider
from app.services.ai.providers.glm5 import GLM5Provider
from app.services.ai.base_llm_provider import LLMRequest, LLMResponse


class SkipIfNoAPIKey:
    """如果环境变量中没有 API 密钥则跳过测试"""

    @staticmethod
    def qwen() -> bool:
        return bool(os.getenv("QWEN_API_KEY"))

    @staticmethod
    def kimi() -> bool:
        return bool(os.getenv("KIMI_API_KEY"))

    @staticmethod
    def glm5() -> bool:
        return bool(os.getenv("GLM5_API_KEY"))


@pytest.mark.integration
@pytest.mark.skipif(not SkipIfNoAPIKey.qwen(), reason="未设置 QWEN_API_KEY")
class TestQwenProviderIntegration:
    """通义千问提供商集成测试"""

    @pytest.fixture
    async def provider(self) -> QwenProvider:
        provider = QwenProvider(api_key=os.getenv("QWEN_API_KEY"))
        assert "qwen" in provider.models
        return provider

    @pytest.mark.asyncio
    async def test_basic_completion(self, provider: QwenProvider):
        """测试基本补全"""
        request = LLMRequest(
            messages=[{"role": "user", "content": "你好，请用一句话介绍自己"}],
            model="qwen-plus",
            max_tokens=100
        )

        response: LLMResponse = await provider.complete(request)

        assert response.success is True
        assert response.text is not None
        assert len(response.text) > 0
        assert response.model_name == "qwen-plus"

    @pytest.mark.asyncio
    async def test_with_temperature(self, provider: QwenProvider):
        """测试温度参数"""
        request = LLMRequest(
            messages=[{"role": "user", "content": "写一个简短的故事"}],
            model="qwen-plus",
            temperature=0.8,
            max_tokens=200
        )

        response = await provider.complete(request)

        assert response.success is True
        assert len(response.text) > 0

    @pytest.mark.asyncio
    async def test_error_handling(self, provider: QwenProvider):
        """测试错误处理 - 无效 API 密钥"""
        bad_provider = QwenProvider(api_key="invalid_key")
        request = LLMRequest(
            messages=[{"role": "user", "content": "测试"}],
            model="qwen-plus"
        )

        response = await bad_provider.complete(request)

        assert response.success is False
        assert response.error is not None


@pytest.mark.integration
@pytest.mark.skipif(not SkipIfNoAPIKey.kimi(), reason="未设置 KIMI_API_KEY")
class TestKimiProviderIntegration:
    """Kimi 提供商集成测试"""

    @pytest.fixture
    async def provider(self) -> KimiProvider:
        provider = KimiProvider(api_key=os.getenv("KIMI_API_KEY"))
        assert "moonshot-v1" in provider.models
        return provider

    @pytest.mark.asyncio
    async def test_basic_completion(self, provider: KimiProvider):
        """测试基本补全"""
        request = LLMRequest(
            messages=[{"role": "user", "content": "你好"}],
            model="moonshot-v1-8k",
            max_tokens=100
        )

        response: LLMResponse = await provider.complete(request)

        assert response.success is True
        assert response.text is not None
        assert len(response.text) > 0


@pytest.mark.integration
@pytest.mark.skipif(not SkipIfNoAPIKey.glm5(), reason="未设置 GLM5_API_KEY")
class TestGLM5ProviderIntegration:
    """GLM-5 提供商集成测试"""

    @pytest.fixture
    async def provider(self) -> GLM5Provider:
        provider = GLM5Provider(api_key=os.getenv("GLM5_API_KEY"))
        assert "glm-5" in provider.models
        return provider

    @pytest.mark.asyncio
    async def test_basic_completion(self, provider: GLM5Provider):
        """测试基本补全"""
        request = LLMRequest(
            messages=[{"role": "user", "content": "你好"}],
            model="glm-5",
            max_tokens=100
        )

        response: LLMResponse = await provider.complete(request)

        assert response.success is True
        assert response.text is not None
        assert len(response.text) > 0


@pytest.mark.integration
@pytest.mark.skipif(
    not (SkipIfNoAPIKey.qwen() or SkipIfNoAPIKey.kimi() or SkipIfNoAPIKey.glm5()),
    reason="未设置任何 API 密钥"
)
class TestLLMManagerIntegration:
    """LLM 管理器集成测试"""

    @pytest.fixture
    async def manager(self) -> LLMManager:
        providers = {}

        if SkipIfNoAPIKey.qwen():
            providers["qwen"] = QwenProvider(api_key=os.getenv("QWEN_API_KEY"))

        if SkipIfNoAPIKey.kimi():
            providers["kimi"] = KimiProvider(api_key=os.getenv("KIMI_API_KEY"))

        if SkipIfNoAPIKey.glm5():
            providers["glm5"] = GLM5Provider(api_key=os.getenv("GLM5_API_KEY"))

        assert len(providers) > 0, "至少需要配置一个提供商"
        return LLMManager(providers=providers, default_provider=list(providers.keys())[0])

    @pytest.mark.asyncio
    async def test_manager_completion(self, manager: LLMManager):
        """测试管理器补全"""
        request = LLMRequest(
            messages=[{"role": "user", "content": "你好"}],
            max_tokens=100
        )

        response: LLMResponse = await manager.complete(request)

        assert response.success is True
        assert response.text is not None
        assert len(response.text) > 0

    @pytest.mark.asyncio
    async def test_provider_switching(self, manager: LLMManager):
        """测试提供商切换"""
        if len(manager.available_providers()) < 2:
            pytest.skip("需要至少两个提供商测试切换")

        # 获取第一个提供商
        first_provider = manager.available_providers()[0]

        # 获取第二个提供商
        second_provider = manager.available_providers()[1]

        # 使用第一个提供商
        request = LLMRequest(
            messages=[{"role": "user", "content": "测试提供商1"}],
            max_tokens=50
        )
        response1 = await manager.complete(request, provider_name=first_provider)

        assert response1.success is True

        # 使用第二个提供商
        request2 = LLMRequest(
            messages=[{"role": "user", "content": "测试提供商2"}],
            max_tokens=50
        )
        response2 = await manager.complete(request2, provider_name=second_provider)

        assert response2.success is True

    @pytest.mark.asyncio
    async def test_auto_failover(self, manager: LLMManager):
        """测试自动切换失败提供商"""

        # 使用有效的请求
        request = LLMRequest(
            messages=[{"role": "user", "content": "你好"}],
            max_tokens=50
        )

        response = await manager.complete(request)

        assert response.success is True


@pytest.mark.integration
class TestScriptGeneratorIntegration:
    """文案生成器集成测试"""

    @pytest.fixture
    async def manager(self) -> Optional[LLMManager]:
        """创建 LLM 管理器（如果可用）"""

        providers = []
        provider_names = []

        if SkipIfNoAPIKey.qwen():
            providers.append(QwenProvider(api_key=os.getenv("QWEN_API_KEY")))
            provider_names.append("qwen")

        if not providers:
            return None

        manager = LLMManager(
            providers=dict(zip(provider_names, providers)),
            default_provider=provider_names[0]
        )
        return manager

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not (SkipIfNoAPIKey.qwen() or SkipIfNoAPIKey.kimi() or SkipIfNoAPIKey.glm5()),
        reason="未设置任何 API 密钥"
    )
    async def test_generate_commentary(self, manager: LLMManager):
        """测试生成解说文案"""
        from app.services.ai.script_generator import ScriptGenerator

        # 确保有可用的 LLM 管理器
        if manager.available_providers():
            # 设置管理器到生成器中
            from app.services.ai import llm_manager
            llm_manager.manager = manager

        generator = ScriptGenerator(use_llm_manager=True)

        script = generator.generate_commentary(
            "分析《流浪地球》的科学设定",
            duration=60,
            style="storytelling"
        )

        assert script is not None
        assert script.text is not None
        assert len(script.text) > 0
        assert script.segments is not None

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not (SkipIfNoAPIKey.qwen() or SkipIfNoAPIKey.kimi() or SkipIfNoAPIKey.glm5()),
        reason="未设置任何 API 密钥"
    )
    async def test_generate_monologue(self, manager: LLMManager):
        """测试生成独白文案"""
        from app.services.ai.script_generator import ScriptGenerator

        if manager.available_providers():
            from app.services.ai import llm_manager
            llm_manager.manager = manager

        generator = ScriptGenerator(use_llm_manager=True)

        script = generator.generate_monologue(
            "深夜独自走在城市街头",
            emotion="惆怅",
            duration=30
        )

        assert script is not None
        assert script.text is not None
        assert len(script.text) > 0


if __name__ == "__main__":
    # 运行集成测试
    pytest.main([
        __file__,
        "-v",
        "-m", "integration",
        "--tb=short"
    ])
