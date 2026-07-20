#!/usr/bin/env python3
"""测试 LLM 提供商基类和混入"""

import httpx
import pytest

from scenefab.services.ai.base_llm_provider import (
    HTTPClientMixin,
    LLMRequest,
    LLMResponse,
    ModelManagerMixin,
    ProviderError,
    ProviderType,
)


@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


class TestLLMDataClasses:
    """测试 LLM 数据类"""

    def test_llm_request_defaults(self):
        """测试请求默认值为"""
        req = LLMRequest(prompt="test prompt")

        assert req.prompt == "test prompt"
        assert req.system_prompt == ""
        assert req.model == "default"
        assert req.max_tokens == 2000
        assert req.temperature == 0.7
        assert req.top_p == 0.9

    def test_llm_request_to_dict(self):
        """测试请求转字典"""
        req = LLMRequest(
            prompt="test",
            system_prompt="You are a helpful assistant",
            model="gpt-4",
            max_tokens=1000,
            temperature=0.5,
        )

        # LLMRequest 不是 dataclass，手动转换
        d = {
            "prompt": req.prompt,
            "system_prompt": req.system_prompt,
            "model": req.model,
            "max_tokens": req.max_tokens,
        }
        assert d["prompt"] == "test"
        assert d["system_prompt"] == "You are a helpful assistant"
        assert d["model"] == "gpt-4"
        assert d["max_tokens"] == 1000

    def test_llm_response_defaults(self):
        """测试响应默认值"""
        resp = LLMResponse(content="Hello", model="gpt-4")

        assert resp.content == "Hello"
        assert resp.model == "gpt-4"
        assert resp.tokens_used == 0
        assert resp.finish_reason == "stop"
        assert resp.raw_response is None


class TestProviderType:
    """测试提供商类型枚举"""

    def test_enum_values(self):
        """测试枚举值"""
        assert ProviderType.OPENAI.value == "openai"
        assert ProviderType.KIMI.value == "kimi"
        assert ProviderType.DEEPSEEK.value == "deepseek"
        assert ProviderType.QWEN.value == "qwen"

    def test_enum_members(self):
        """测试枚举成员"""
        members = list(ProviderType)
        assert len(members) >= 7
        assert ProviderType.OPENAI in members


class TestProviderError:
    """测试提供商错误"""

    def test_error_creation(self):
        """测试错误创建"""
        err = ProviderError("Test error message")
        assert "Test error message" in str(err)  # 包含原始消息

    def test_error_inheritance(self):
        """测试错误继承"""
        err = ProviderError("Test")
        assert isinstance(err, Exception)


class MockHTTPClient:
    """模拟 HTTP 客户端"""

    pass


class MockStreamResponse:
    """模拟流式响应"""

    def __init__(self, lines):
        self._lines = lines

    async def aiter_lines(self):
        for line in self._lines:
            yield line


class MockRetryHandler:
    """记录调用次数的重试处理器"""

    def __init__(self):
        self.calls = 0

    async def execute(self, func, *args, **kwargs):
        self.calls += 1
        return await func(*args, **kwargs)


class TestProviderWithMixins:
    """测试带有混入的提供商"""

    def test_http_client_mixin_init(self):
        """测试 HTTP 客户端混入初始化"""

        class TestProvider(HTTPClientMixin):
            pass

        provider = TestProvider(
            api_key="test-key", base_url="https://api.example.com", timeout=30.0
        )

        assert provider.api_key == "test-key"
        assert provider.base_url == "https://api.example.com"
        assert provider.timeout == 30.0

    def test_model_manager_mixin(self):
        """测试模型管理混入"""

        class TestProvider(ModelManagerMixin):
            MODELS = {
                "gpt-4": {"name": "GPT-4", "max_tokens": 8000},
                "gpt-3.5": {"name": "GPT-3.5", "max_tokens": 4000},
            }
            DEFAULT_MODEL = "gpt-4"

        provider = TestProvider()

        assert "gpt-4" in provider.MODELS
        assert provider.DEFAULT_MODEL == "gpt-4"
        assert provider.get_model_info("gpt-4") == {"name": "GPT-4", "max_tokens": 8000}

    def test_model_manager_get_model_info_not_found(self):
        """测试获取不存在的模型信息"""

        class TestProvider(ModelManagerMixin):
            MODELS = {}
            DEFAULT_MODEL = "default"

        provider = TestProvider()
        result = provider.get_model_info("nonexistent")

        assert result == {}

    @pytest.mark.anyio
    async def test_parse_sse_stream(self):
        """测试 OpenAI SSE 流解析"""

        class TestProvider(HTTPClientMixin):
            pass

        provider = TestProvider(api_key="key", base_url="https://api.example.com")
        response = MockStreamResponse(
            [
                ": keepalive",
                "data: {bad json}",
                'data: {"choices":[{"delta":{"content":"你"}}]}',
                'data: {"choices":[{"delta":{"content":"好"}}]}',
                "data: [DONE]",
                'data: {"choices":[{"delta":{"content":"忽略"}}]}',
            ]
        )

        chunks = [chunk async for chunk in provider._parse_sse_stream(response)]

        assert chunks == ["你", "好"]

    @pytest.mark.anyio
    async def test_iter_json_stream_payloads_plain_json(self):
        """测试裸 JSON 行流解析"""

        class TestProvider(HTTPClientMixin):
            pass

        provider = TestProvider(api_key="key", base_url="https://api.example.com")
        response = MockStreamResponse(
            [
                "",
                "{bad json}",
                '{"Choices":[{"Delta":{"Content":"混"}}]}',
                '{"Choices":[{"Delta":{"Content":"元"}}]}',
            ]
        )

        payloads = [
            payload
            async for payload in provider._iter_json_stream_payloads(
                response,
                sse=False,
            )
        ]

        assert [p["Choices"][0]["Delta"]["Content"] for p in payloads] == ["混", "元"]

    @pytest.mark.anyio
    async def test_generate_openai_compatible_uses_retry_and_latency(self):
        """测试 OpenAI 兼容生成统一使用重试并记录延迟"""

        class TestProvider(HTTPClientMixin):
            pass

        provider = TestProvider(api_key="key", base_url="https://api.example.com")
        retry_handler = MockRetryHandler()
        provider._retry_handler = retry_handler

        async def fake_call_api(method, endpoint, **kwargs):
            assert method == "POST"
            assert endpoint == "https://api.example.com/chat/completions"
            assert kwargs["json"]["model"] == "test-model"
            return {
                "choices": [
                    {
                        "message": {"content": "ok"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"total_tokens": 7},
            }

        provider._call_api = fake_call_api

        response = await provider._generate_openai_compatible(
            request=LLMRequest(prompt="hello"),
            model="test-model",
            messages=[{"role": "user", "content": "hello"}],
        )

        assert response.content == "ok"
        assert response.tokens_used == 7
        assert response.latency_ms >= 0
        assert retry_handler.calls == 1

    def test_provider_error_preserves_existing_provider_error(self):
        """测试统一错误包装不会重复包裹 ProviderError"""

        class TestProvider(HTTPClientMixin):
            pass

        provider = TestProvider(api_key="key", base_url="https://api.example.com")
        error = ProviderError("认证失败")

        assert provider._provider_error("生成", error) is error

    def test_stream_provider_error_wraps_regular_exception(self):
        """测试流式错误包装普通异常"""

        class TestProvider(HTTPClientMixin):
            pass

        provider = TestProvider(api_key="key", base_url="https://api.example.com")
        error = provider._stream_provider_error(RuntimeError("boom"))

        assert isinstance(error, ProviderError)
        assert "流式生成失败: boom" in str(error)

    def test_provider_error_handles_http_status_error(self):
        """测试统一错误包装 HTTP 状态异常"""

        class TestProvider(HTTPClientMixin):
            pass

        provider = TestProvider(api_key="key", base_url="https://api.example.com")
        request = httpx.Request("POST", "https://api.example.com")
        response = httpx.Response(
            401,
            request=request,
            json={"error": {"message": "bad key"}},
        )
        error = httpx.HTTPStatusError("bad", request=request, response=response)

        wrapped = provider._stream_provider_error(error)

        assert isinstance(wrapped, ProviderError)
        assert "认证失败" in str(wrapped)
        assert "bad key" in str(wrapped)
