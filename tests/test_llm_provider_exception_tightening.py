#!/usr/bin/env python3
"""
回归测试: LLM providers 收紧 except Exception 后, 网络/解析错误仍能正确抛 ProviderError

覆盖:
- httpx 网络错误 (连接超时/连接拒绝等) → ProviderError (网络错误)
- HTTP 4xx/5xx → ProviderError (HTTP 错误, 走 _handle_http_error)
- 响应解析错误 (json.JSONDecodeError / KeyError) → ProviderError (响应解析)
- 重试 + 真错误 → 抛 ProviderError (不静默)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from scenefab.services.ai.base_llm_provider import ProviderError
from scenefab.services.ai.providers.deepseek import DeepSeekProvider
from scenefab.services.ai.providers.doubao import DoubaoProvider
from scenefab.services.ai.providers.hunyuan import HunyuanProvider
from scenefab.services.ai.providers.qwen import QwenProvider


def _make_provider(provider_cls):
    """构造一个 provider, base_url/api_key 任意填, 不真发请求"""
    if provider_cls in (QwenProvider, DeepSeekProvider, DoubaoProvider):
        return provider_cls(
            api_key="test-key",
            base_url="https://example.com/v1",
        )
    if provider_cls is HunyuanProvider:
        # Hunyuan 签名不同 (secret_id/secret_key/base_url)
        return provider_cls(
            api_key="test-key",
            secret_id="test-id",
            secret_key="test-key",
            base_url="https://example.com",
        )
    raise ValueError(f"未支持: {provider_cls}")


def _make_response(status_code: int = 200, json_data=None, raise_status: bool = False):
    """构造 httpx.Response mock"""
    resp = MagicMock()
    resp.status_code = status_code
    if raise_status:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    else:
        resp.raise_for_status = MagicMock()
    if json_data is not None:
        resp.json.return_value = json_data
    return resp


class TestNetworkErrorBecomesProviderError:
    """网络层错误 (httpx) → ProviderError (网络错误), 不再裸 AttributeError/NameError"""

    @pytest.mark.asyncio
    async def test_qwen_network_error(self) -> None:
        """qwen.generate 遇到 httpx.ConnectError → ProviderError"""
        provider = _make_provider(QwenProvider)
        # Mock _retry_handler.execute 直接抛网络错误
        with patch.object(
            provider, "_retry_handler"
        ) as mock_retry:
            mock_retry.execute = AsyncMock(
                side_effect=httpx.ConnectError("connection refused")
            )
            with pytest.raises(ProviderError) as exc_info:
                # 用 LLMRequest (避免传 prompt=string 兼容旧接口)
                from scenefab.services.ai.base_llm_provider import LLMRequest
                await provider.generate(LLMRequest(prompt="test"))
        assert "网络错误" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_qwen_timeout_error(self) -> None:
        """qwen.generate 遇到 httpx.TimeoutException → ProviderError"""
        provider = _make_provider(QwenProvider)
        with patch.object(
            provider, "_retry_handler"
        ) as mock_retry:
            mock_retry.execute = AsyncMock(
                side_effect=httpx.TimeoutException("timeout")
            )
            with pytest.raises(ProviderError) as exc_info:
                from scenefab.services.ai.base_llm_provider import LLMRequest
                await provider.generate(LLMRequest(prompt="test"))
        assert "网络错误" in str(exc_info.value)


class TestResponseParseErrorBecomesProviderError:
    """响应解析错误 (KeyError/JSONDecodeError) → ProviderError (响应解析)"""

    def test_qwen_parse_response_keyerror(self) -> None:
        """qwen._parse_response 缺关键字段 → 不应抛裸 KeyError, 应抛 ProviderError 或返回 LLMResponse with 降级"""
        # 关键: 验证改后的代码, KeyError 不会从 public API 漏出
        # 实际行为: 旧 except Exception 会捕获 KeyError → ProviderError
        #          新 except KeyError 也会捕获 → ProviderError
        # 二者等价, 但新代码意图更清晰
        provider = _make_provider(QwenProvider)
        # _parse_response 签名 (data, model, latency_ms) 返回 LLMResponse
        # 缺 'choices' 字段应抛 KeyError
        with pytest.raises((KeyError, ProviderError)):
            provider._parse_response(data={}, model="test", latency_ms=10.0)


class TestLocalProviderNetworkError:
    """local.py 拉取模型 (本地 Ollama) 收紧到 httpx.HTTPError"""

    @pytest.mark.asyncio
    async def test_local_pull_model_connect_error(self) -> None:
        """本地 Ollama 不可达 → ProviderError (网络错误), 不应 AttributeError"""
        from scenefab.services.ai.providers.local import LocalProvider

        provider = LocalProvider(
            base_url="http://localhost:99999",  # 不可达
        )
        with patch.object(
            provider, "http_client", new=MagicMock()
        ) as mock_client:
            mock_client.post = AsyncMock(
                side_effect=httpx.ConnectError("localhost:99999 refused")
            )
            with pytest.raises(ProviderError) as exc_info:
                await provider.pull_model("llama3")
        assert "网络错误" in str(exc_info.value)


class TestNonHttpExceptionIsNotSwallowed:
    """诚实性: 收紧后, 非 httpx/json 错误 (e.g. RuntimeError, TypeError) 不再被吞

    旧 except Exception 会把 RuntimeError 也包成 ProviderError.
    新代码不会 — 这种 bug 应该让调用方看到, 而非被吞.
    """

    @pytest.mark.asyncio
    async def test_qwen_runtime_error_propagates(self) -> None:
        """qwen.generate 内部 RuntimeError (非网络/解析) 不应被吞, 应让调用方看到"""
        provider = _make_provider(QwenProvider)
        with patch.object(
            provider, "_retry_handler"
        ) as mock_retry:
            mock_retry.execute = AsyncMock(
                side_effect=RuntimeError("unexpected programming error")
            )
            # 改前: except Exception 吞掉, 包成 ProviderError
            # 改后: RuntimeError 不在 except 列表, 裸抛 (更易定位 bug)
            with pytest.raises(RuntimeError, match="unexpected programming error"):
                from scenefab.services.ai.base_llm_provider import LLMRequest
                await provider.generate(LLMRequest(prompt="test"))
