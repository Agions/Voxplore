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
# 2. streaming_llm_worker.py:169/184 PyQt Signal emit
# =============================================================================


def test_dispatch_token_signal_runtime_error_logs_debug():
    """PyQt Signal emit 抛 RuntimeError (C++ 对象已 delete) → log debug, 不 crash"""
    from scenefab.core.streaming_llm_worker import StreamingLLMWorker

    worker = StreamingLLMWorker.__new__(StreamingLLMWorker)
    worker.logger = logging.getLogger(__name__)
    worker.token_received = MagicMock()
    worker._on_token = None
    worker._on_sentence = None
    worker.token_received.emit.side_effect = RuntimeError("Signal: underlying C/C++ object deleted")

    # 不应抛错 (Signal 失败仅 log debug)
    worker._dispatch_token("test_token")


def test_dispatch_token_callback_exception_logs_debug():
    """callback 抛 Exception → log debug, 不 crash"""
    from scenefab.core.streaming_llm_worker import StreamingLLMWorker

    worker = StreamingLLMWorker.__new__(StreamingLLMWorker)
    worker.logger = logging.getLogger(__name__)
    worker.token_received = MagicMock()
    worker._on_token = MagicMock(side_effect=ValueError("Callback error"))
    worker._on_sentence = None

    # 不应抛错
    worker._dispatch_token("test_token")


def test_dispatch_token_signal_type_error_propagates():
    """★诚实性: emit 抛 TypeError 不再被 RuntimeError catch 包裹"""
    from scenefab.core.streaming_llm_worker import StreamingLLMWorker

    worker = StreamingLLMWorker.__new__(StreamingLLMWorker)
    worker.logger = logging.getLogger(__name__)
    worker.token_received = MagicMock()
    worker._on_token = None
    worker._on_sentence = None
    # TypeError 不在 except RuntimeError 范围, 应该 raise
    worker.token_received.emit.side_effect = TypeError("Code bug: bad emit arg")

    with pytest.raises(TypeError, match="Code bug"):
        worker._dispatch_token("test_token")


def test_dispatch_sentence_signal_runtime_error_logs_debug():
    """sentence_completed.emit RuntimeError → log debug, 不 crash"""
    from scenefab.core.streaming_llm_worker import StreamingLLMWorker

    worker = StreamingLLMWorker.__new__(StreamingLLMWorker)
    worker.logger = logging.getLogger(__name__)
    worker.sentence_completed = MagicMock()
    worker._on_token = None
    worker._on_sentence = None
    worker.sentence_completed.emit.side_effect = RuntimeError("Signal deleted")

    with patch.object(worker, "_extract_last_sentence", return_value="test sentence."):
        # 不应 raise (Signal RuntimeError → log debug, callback None)
        worker._dispatch_token("。")


def test_dispatch_sentence_callback_runtime_error_logs_debug():
    """sentence callback RuntimeError → log debug (保留 Exception 兜底)"""
    from scenefab.core.streaming_llm_worker import StreamingLLMWorker

    worker = StreamingLLMWorker.__new__(StreamingLLMWorker)
    worker.logger = logging.getLogger(__name__)
    worker.sentence_completed = MagicMock()
    worker._on_token = None
    worker._on_sentence = MagicMock(side_effect=RuntimeError("Code bug: bad callback"))

    with patch.object(worker, "_extract_last_sentence", return_value="test sentence."):
        # 不应 raise (callback except Exception 兜底, 设计意图)
        worker._dispatch_token("。")