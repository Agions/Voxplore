#!/usr/bin/env python3
"""
回归测试: plugins/loader + streaming_llm_worker 收紧 except Exception 后,
JSON load / PyQt Signal emit 错误仍正确处理, 但 RuntimeError 不再被吞.

诚实性核心: 收紧后非预期异常 (RuntimeError 等真实编程 bug) 应该 raise,
而不再被 log 后吞掉 (掩盖 bug).
"""

import logging
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.anyio

# =============================================================================
# 1. plugins/loader.py:223 _discover_plugin_in_dir JSON load
# =============================================================================


def test_discover_plugin_json_decode_error_returns_none(tmp_path):
    """JSON 解析失败 → return None, 不 crash"""
    from scenefab.plugins.loader import PluginLoader

    loader = PluginLoader.__new__(PluginLoader)
    loader._registry = MagicMock()

    plugin_dir = tmp_path / "test_plugin"
    plugin_dir.mkdir()
    manifest_file = plugin_dir / "manifest.json"
    manifest_file.write_text("这不是 JSON, { 坏的格式")

    result = loader._discover_plugin_in_dir(plugin_dir)
    assert result is None


def test_discover_plugin_oserror_returns_none(tmp_path):
    """文件 IO 失败 (permission) → return None"""
    from scenefab.plugins.loader import PluginLoader

    loader = PluginLoader.__new__(PluginLoader)
    loader._registry = MagicMock()

    plugin_dir = tmp_path / "test_plugin"
    plugin_dir.mkdir()
    manifest_file = plugin_dir / "manifest.json"
    manifest_file.write_text('{"id": "test", "name": "test"}')

    with patch("builtins.open", side_effect=OSError("Permission denied")):
        result = loader._discover_plugin_in_dir(plugin_dir)
        assert result is None


def test_discover_plugin_runtime_error_propagates(tmp_path):
    """★诚实性: PluginManifest 构造中 RuntimeError 不再被吞"""
    from scenefab.plugins.loader import PluginLoader

    loader = PluginLoader.__new__(PluginLoader)
    loader._registry = MagicMock()

    plugin_dir = tmp_path / "test_plugin"
    plugin_dir.mkdir()
    manifest_file = plugin_dir / "manifest.json"
    manifest_file.write_text('{"id": "test", "name": "test"}')

    with patch("scenefab.plugins.loader.PluginManifest",
               side_effect=RuntimeError("Code bug: bad manifest schema")):
        with pytest.raises(RuntimeError, match="Code bug"):
            loader._discover_plugin_in_dir(plugin_dir)


# =============================================================================
# 2. stream_worker.py:169/184 PyQt Signal emit
# =============================================================================


def test_dispatch_token_signal_runtime_error_logs_debug(caplog):
    """_dispatch_token 中 signal.emit 抛 RuntimeError → log debug (UI 线程被销毁等)"""
    from scenefab.core.stream_worker import StreamingLLMWorker

    worker = StreamingLLMWorker.__new__(StreamingLLMWorker)
    worker.token_received = MagicMock()
    worker.token_received.emit.side_effect = RuntimeError("Signal destination destroyed")
    worker._on_token = None
    worker._on_sentence = None

    with caplog.at_level(logging.DEBUG, logger="scenefab.core.stream_worker"):
        worker._dispatch_token("hello")

    assert any("token_received.emit" in r.message.lower() for r in caplog.records)


def test_dispatch_token_callback_exception_logs_debug(caplog):
    """_dispatch_token 中 callback 抛 Exception → log debug"""
    from scenefab.core.stream_worker import StreamingLLMWorker

    worker = StreamingLLMWorker.__new__(StreamingLLMWorker)
    worker.token_received = MagicMock()
    worker._on_token = MagicMock(side_effect=ValueError("Callback error"))
    worker._on_sentence = None

    with caplog.at_level(logging.DEBUG, logger="scenefab.core.stream_worker"):
        worker._dispatch_token("hello")

    assert any("on_token callback" in r.message.lower() for r in caplog.records)


def test_dispatch_token_signal_type_error_propagates():
    """★诚实性: _dispatch_token 中 TypeError (e.g. signal 类型不符) 不再被吞"""
    from scenefab.core.stream_worker import StreamingLLMWorker

    worker = StreamingLLMWorker.__new__(StreamingLLMWorker)
    worker.token_received = MagicMock()
    worker.token_received.emit.side_effect = TypeError("Code bug: wrong signal arg type")
    worker._on_token = None
    worker._on_sentence = None

    with pytest.raises(TypeError, match="Code bug"):
        worker._dispatch_token("hello")


def test_dispatch_sentence_signal_runtime_error_logs_debug(caplog):
    """_dispatch_sentence 中 sentence_completed.emit 抛 RuntimeError → log debug"""
    from scenefab.core.stream_worker import StreamingLLMWorker

    worker = StreamingLLMWorker.__new__(StreamingLLMWorker)
    worker.token_received = MagicMock()
    worker.sentence_completed = MagicMock()
    worker.sentence_completed.emit.side_effect = RuntimeError("Signal destroyed")
    worker._on_token = None
    worker._on_sentence = None
    worker._accumulated = "一句话。"

    with caplog.at_level(logging.DEBUG, logger="scenefab.core.stream_worker"):
        worker._dispatch_token("。")

    assert any("sentence_completed.emit" in r.message.lower() for r in caplog.records)


def test_dispatch_sentence_callback_runtime_error_logs_debug(caplog):
    """_dispatch_sentence 中 sentence callback 抛 Exception → log debug"""
    from scenefab.core.stream_worker import StreamingLLMWorker

    worker = StreamingLLMWorker.__new__(StreamingLLMWorker)
    worker.token_received = MagicMock()
    worker.sentence_completed = MagicMock()
    worker._on_token = None
    worker._on_sentence = MagicMock(side_effect=RuntimeError("Callback crashed"))
    worker._accumulated = "一句话。"

    with caplog.at_level(logging.DEBUG, logger="scenefab.core.stream_worker"):
        worker._dispatch_token("。")

    assert any("on_sentence callback" in r.message.lower() for r in caplog.records)