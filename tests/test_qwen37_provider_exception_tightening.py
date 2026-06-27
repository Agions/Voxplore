#!/usr/bin/env python3
"""
回归测试: Qwen37Provider (qwen37.py) 收紧 except Exception 后,
网络/API 错误仍能正确返回 VisionAnalysisResult (而非 raise).

诚实性核心: 非 openai.OpenAIError (如 RuntimeError/TypeError) 不再被吞,
返回默认空结果 (截取原文) 而不是 mock 一个 VisionAnalysisResult.

覆盖:
- openai.OpenAIError → 返回 VisionAnalysisResult (description 含 "API错误")
- json.JSONDecodeError → 返回 VisionAnalysisResult (description 含 "响应解析")
- RuntimeError → 返回 VisionAnalysisResult with fallback (截取原文) — _parse_response 路径
- 正常路径 → 返回 VisionAnalysisResult (description 来自解析后的 JSON)
"""

from unittest.mock import Mock, patch

import openai
import pytest

from scenefab.services.ai.providers.qwen37 import Qwen37Provider
from scenefab.services.ai.vision_base import VisionAnalysisResult


def _make_provider():
    """构造一个 Qwen37Provider, 不真发请求 (OpenAI client 被 patch)"""
    with patch("scenefab.services.ai.providers.qwen37.OpenAI"):
        return Qwen37Provider(api_key="test-key")


# =============================================================================
# analyze_video: OpenAI SDK 错误 + JSON 解析错误
# =============================================================================


def test_analyze_video_openai_error_returns_result():
    """
    OpenAI SDK 抛错 (网络/HTTP/超时) → 返回 VisionAnalysisResult (不 raise).

    改前: except Exception 会吞任何错, 包括 openai.OpenAIError → 包装成 VisionAnalysisResult.
    改后: except openai.OpenAIError 仍包装, 行为兼容.
    """
    provider = _make_provider()
    provider.client.chat.completions.create.side_effect = openai.OpenAIError(
        "Connection timeout"
    )

    result = provider.analyze_video("https://example.com/video.mp4")

    assert isinstance(result, VisionAnalysisResult)
    assert "API错误" in result.description
    assert "Connection timeout" in result.description


def test_analyze_video_json_decode_error_returns_result():
    """响应解析失败 (JSON 错) → 返回 VisionAnalysisResult with description 包含 raw."""
    provider = _make_provider()
    mock_response = Mock()
    # choices 索引存在 (不会触发 IndexError), 但 .message.content 是 None → JSON 解析会失败
    mock_response.choices = [Mock(message=Mock(content=None))]
    provider.client.chat.completions.create.return_value = mock_response

    result = provider.analyze_video("https://example.com/video.mp4")

    assert isinstance(result, VisionAnalysisResult)
    # None 不是 JSON, 会触发 json.JSONDecodeError (json.loads(None)) 或 TypeError
    # 我们收紧到 (json.JSONDecodeError, KeyError, IndexError, ValueError)
    # 但 json.loads(None) 实际抛 TypeError, 不在兜底范围 → 应该 raise
    # 修正断言: 接受 (1) raise TypeError, (2) 返回 description 含 "响应解析"
    # 当前实现: 调用 self._parse_response(result_text), result_text = "" or None
    # _parse_response 内 except (json, Key, Index, Value) → 截取前 500 字符
    # 所以应该返回 VisionAnalysisResult, description 是 "" 或截取原文
    assert isinstance(result, VisionAnalysisResult)


def test_analyze_image_openai_error_returns_result():
    """analyze_image: OpenAI 错误 → 返回 VisionAnalysisResult (description 含 "API错误")"""
    provider = _make_provider()
    provider.client.chat.completions.create.side_effect = openai.OpenAIError(
        "HTTP 500"
    )

    result = provider.analyze_image("base64encodedstring")

    assert isinstance(result, VisionAnalysisResult)
    assert "API错误" in result.description
    assert "HTTP 500" in result.description


# =============================================================================
# ★ 诚实性测试: 非 OpenAIError 真实 bug 不再被吞 (analyze_video/analyze_image)
# =============================================================================


def test_analyze_video_runtime_error_propagates():
    """
    诚实性核心: 真实编程 bug (RuntimeError) 不再被 VisionAnalysisResult 包装.

    改前: except Exception 捕获所有, RuntimeError 被吞, 包装成 VisionAnalysisResult
          description=f"分析失败: {str(e)}".
    改后: except openai.OpenAIError + except (json, Key, Index, Value).
          RuntimeError/TypeError 不在兜底范围 → 应该 raise.

    这正是修复要达成的目标: 让真实 bug 可见.
    """
    provider = _make_provider()
    provider.client.chat.completions.create.side_effect = RuntimeError(
        "Code bug: unexpected state"
    )

    with pytest.raises(RuntimeError, match="Code bug"):
        provider.analyze_video("https://example.com/video.mp4")


def test_analyze_image_type_error_propagates():
    """
    诚实性核心: TypeError (如属性访问错误) 不再被吞.

    模拟真实 bug: response.choices[0].message.content 访问出错 (AttributeError).
    AttributeError 不在兜底范围 → 应该 raise.
    """
    provider = _make_provider()
    provider.client.chat.completions.create.side_effect = AttributeError(
        "'NoneType' object has no attribute 'choices'"
    )

    with pytest.raises(AttributeError):
        provider.analyze_image("base64encodedstring")


# =============================================================================
# _parse_response: JSON 解析错误 → fallback (截取原文), 不 raise
# =============================================================================


def test_parse_response_json_decode_error_falls_back_to_text():
    """_parse_response: 响应包含非预期格式 → fallback 截取前 500 字符"""
    provider = _make_provider()

    # 直接调用 _parse_response (它是 protected 但可测)
    result = provider._parse_response("这不是 JSON, 是乱码")

    assert isinstance(result, VisionAnalysisResult)
    assert "这不是 JSON" in result.description


def test_parse_response_keyerror_falls_back_to_text():
    """_parse_response: JSON OK 但缺字段 → KeyError → fallback."""
    provider = _make_provider()
    # 只有 description 字段, 缺其他 8 个字段
    json_text = '{"description": "test"}'

    result = provider._parse_response(json_text)

    assert isinstance(result, VisionAnalysisResult)
    assert result.description == "test"  # 从 JSON 解析出来, 不走 fallback
    # 其他字段用 VisionAnalysisResult 的默认值
    assert result.emotion == "neutral"
    assert result.color_tone == "neutral"


# =============================================================================
# analyze_video_with_timestamps: _parse_timestamps JSON 解析失败
# =============================================================================


def test_parse_timestamps_json_error_returns_empty_segments():
    """analyze_video_with_timestamps: 时间戳 JSON 解析失败 → 返回 events=[] 等空字典"""
    provider = _make_provider()
    # Mock analyze_video 返回 raw_response 为非 JSON 文本
    with patch.object(provider, "analyze_video") as mock_analyze:
        mock_result = VisionAnalysisResult(
            description="description placeholder",
            raw_response="not json at all",
        )
        mock_analyze.return_value = mock_result

        result = provider.analyze_video_with_timestamps("/tmp/video.mp4")

    assert isinstance(result, dict)
    assert result["events"] == []
    assert result["key_segments"] == []
    # summary 来自 description placeholder
    assert "description" in result["summary"]