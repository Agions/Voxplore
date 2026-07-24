#!/usr/bin/env python3
"""
回归测试: HTTPClientMixin._call_api narrow 化 (audit 报告 C1-C4 抽取)

诚实性核心:
- 改前: except Exception (宽 catch, 吞 RuntimeError/TypeError)
- 改后: 异常分两段 catch:
  - httpx.HTTPStatusError → _handle_http_error (401/429/500 等)
  - httpx.HTTPError (其他网络错误) → ProviderError("网络错误")
  - json.JSONDecodeError/ValueError (响应解析) → ProviderError("响应解析")
  - RuntimeError/TypeError 等真 bug 不再被吞

覆盖:
- _call_api 网络错误包装 (ConnectError, TimeoutException, ReadError 等)
- _call_api 响应解析错误 (JSONDecodeError, ValueError) 单独 catch
- _call_api RuntimeError 不再被吞
- _call_api HTTPStatusError 走 _handle_http_error 路径
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

pytestmark = pytest.mark.anyio

from scenefab.exceptions import ProviderError

# =============================================================================
# 1. _call_api 异常路径分类
# =============================================================================


@pytest.fixture
def mixin():
    """构造一个最小 HTTPClientMixin 实例用于测试"""
    from scenefab.services.ai.base_llm_provider import HTTPClientMixin

    m = HTTPClientMixin.__new__(HTTPClientMixin)
    m.api_key = "test-key"
    m.base_url = "https://example.com"
    m.timeout = 30.0
    m._default_headers = {}
    m._retry_handler = MagicMock()
    return m


@pytest.mark.asyncio
async def test_call_api_http_status_error_uses_handle_http_error(mixin):
    """HTTPStatusError → 走 _handle_http_error (统一 401/429/500 处理)"""
    # Mock http_client
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "401 Unauthorized",
        request=MagicMock(),
        response=MagicMock(status_code=401, json=MagicMock(return_value={"error": {"message": "Invalid API key"}})),
    )
    mixin.http_client = MagicMock()
    mixin.http_client.request = AsyncMock(return_value=mock_response)

    with patch.object(mixin, "_handle_http_error", return_value=ProviderError("401 mock")):
        with pytest.raises(ProviderError, match="401 mock"):
            await mixin._call_api("POST", "/chat")


@pytest.mark.asyncio
async def test_call_api_http_error_other_wrapped_as_network_error(mixin):
    """非 StatusError 的 HTTPError (连接超时/DNS失败) → ProviderError("网络错误")"""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx.ConnectError("Connection refused")
    mixin.http_client = MagicMock()
    mixin.http_client.request = AsyncMock(return_value=mock_response)

    with pytest.raises(ProviderError, match="网络错误"):
        await mixin._call_api("POST", "/chat")


@pytest.mark.asyncio
async def test_call_api_json_decode_error_wrapped_as_parse_error(mixin):
    """响应 JSON 解析失败 → ProviderError("响应解析")"""
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None  # 200 OK
    mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)
    mixin.http_client = MagicMock()
    mixin.http_client.request = AsyncMock(return_value=mock_response)

    with pytest.raises(ProviderError, match="响应解析"):
        await mixin._call_api("POST", "/chat")


@pytest.mark.asyncio
async def test_call_api_value_error_wrapped_as_parse_error(mixin):
    """响应 .json() 抛 ValueError (httpx 对空 body 抛 ValueError) → ProviderError("响应解析")"""
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.side_effect = ValueError("Response is None")
    mixin.http_client = MagicMock()
    mixin.http_client.request = AsyncMock(return_value=mock_response)

    with pytest.raises(ProviderError, match="响应解析"):
        await mixin._call_api("POST", "/chat")


@pytest.mark.asyncio
async def test_call_api_runtime_error_propagates(mixin):
    """★ 诚实性: RuntimeError 不再被吞 (真 bug 应暴露)"""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = RuntimeError("Code bug: unexpected state")
    mixin.http_client = MagicMock()
    mixin.http_client.request = AsyncMock(return_value=mock_response)

    # 改前: except Exception 包装成 ProviderError("API 调用失败: ...")
    # 改后: RuntimeError 不在 except 列表, 直接 propagate
    with pytest.raises(RuntimeError, match="Code bug"):
        await mixin._call_api("POST", "/chat")


@pytest.mark.asyncio
async def test_call_api_type_error_propagates(mixin):
    """★ 诚实性: TypeError 不再被吞"""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = TypeError("Code bug: bad type")
    mixin.http_client = MagicMock()
    mixin.http_client.request = AsyncMock(return_value=mock_response)

    with pytest.raises(TypeError, match="Code bug"):
        await mixin._call_api("POST", "/chat")


@pytest.mark.asyncio
async def test_call_api_success_returns_json(mixin):
    """Happy path: 返回 parsed JSON dict"""
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"choices": [{"message": {"content": "hi"}}]}
    mixin.http_client = MagicMock()
    mixin.http_client.request = AsyncMock(return_value=mock_response)

    result = await mixin._call_api("POST", "/chat", json={"foo": "bar"})
    assert result == {"choices": [{"message": {"content": "hi"}}]}


# =============================================================================
# 2. _call_api 与 _handle_http_error 协作
# =============================================================================


@pytest.mark.asyncio
async def test_call_api_delegates_to_handle_http_error(mixin):
    """HTTPStatusError 必须调用 _handle_http_error 一次 (不重复 raise)"""
    mock_response = MagicMock()
    err_response = MagicMock()
    err_response.status_code = 429
    err_response.json.return_value = {"error": {"message": "Rate limit"}}
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "429 Too Many Requests",
        request=MagicMock(),
        response=err_response,
    )
    mixin.http_client = MagicMock()
    mixin.http_client.request = AsyncMock(return_value=mock_response)

    with patch.object(mixin, "_handle_http_error", wraps=mixin._handle_http_error) as spy:
        with pytest.raises(ProviderError, match="429"):
            await mixin._call_api("POST", "/chat")

    # 验证: _handle_http_error 被调用一次
    assert spy.call_count == 1
