#!/usr/bin/env python3
"""Toast 通知系统的单元测试（v2.5.0 端到端流程优化）。

覆盖：
- ToastSpec / ToastAction 数据类不可变
- _ToastItem 类型图标 / 自动消失 / action 触发
- ToastManager 静态入口 + 跨线程投递
- _ToastHost 队列与堆叠
- open_in_os / reveal_in_finder 平台分支
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from app.ui.main.widgets.toast import (
    ToastAction,
    ToastManager,
    ToastSpec,
    _ToastHost,
    _ToastItem,
    open_in_os,
    reveal_in_finder,
)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


# ═══════════════════════════════════════════════════════════════════
# ToastSpec / ToastAction
# ═══════════════════════════════════════════════════════════════════


class TestDataClasses:
    def test_toast_spec_is_frozen(self):
        spec = ToastSpec(level="info", title="t", message="m")
        with pytest.raises((AttributeError, TypeError)):
            spec.title = "changed"  # type: ignore[misc]

    def test_toast_action_callback_invokable(self):
        cb = MagicMock()
        action = ToastAction(label="L", callback=cb)
        action.callback()
        cb.assert_called_once_with()


# ═══════════════════════════════════════════════════════════════════
# _ToastItem
# ═══════════════════════════════════════════════════════════════════


class TestToastItem:
    def _make(self, spec, qt_app) -> _ToastItem:
        item = _ToastItem(spec)
        return item

    def test_action_button_triggers_callback(self, qt_app):
        from PySide6.QtWidgets import QPushButton

        cb = MagicMock()
        spec = ToastSpec(
            level="info",
            title="t",
            actions=(ToastAction(label="Click me", callback=cb),),
        )
        item = self._make(spec, qt_app)
        # 找到 label 为 "Click me" 的 QPushButton 并 click
        target = None
        for child in item.findChildren(QPushButton):
            if child.text() == "Click me":
                target = child
                break
        assert target is not None, "action button not found"
        target.click()
        cb.assert_called_once()

    def test_close_emits_signal(self, qt_app):
        spec = ToastSpec(level="info", title="t")
        item = self._make(spec, qt_app)
        captured: list[object] = []
        item.closed.connect(lambda x: captured.append(x))
        item._close()
        assert len(captured) == 1

    def test_auto_close_timer_default(self, qt_app):
        """info 类默认 4000ms 自动消失。"""
        spec = ToastSpec(level="info", title="t")
        item = self._make(spec, qt_app)
        assert item._timer is not None
        assert item._timer.interval() == 4000

    def test_auto_close_timer_error(self, qt_app):
        """error 类默认 6000ms 自动消失。"""
        spec = ToastSpec(level="error", title="t")
        item = self._make(spec, qt_app)
        assert item._timer is not None
        assert item._timer.interval() == 6000

    def test_auto_close_timer_custom(self, qt_app):
        """duration_ms 显式覆盖。"""
        spec = ToastSpec(level="info", title="t", duration_ms=1234)
        item = self._make(spec, qt_app)
        assert item._timer.interval() == 1234

    def test_action_callback_exception_isolated(self, qt_app):
        """action callback 抛异常不应导致 toast 崩溃。"""
        from PySide6.QtWidgets import QPushButton

        spec = ToastSpec(
            level="info",
            title="t",
            actions=(ToastAction(label="Boom", callback=lambda: 1 / 0),),
        )
        item = self._make(spec, qt_app)
        target = None
        for child in item.findChildren(QPushButton):
            if child.text() == "Boom":
                target = child
                break
        assert target is not None
        target.click()  # 防御性：应只 log 不 raise


# ═══════════════════════════════════════════════════════════════════
# ToastManager / _ToastHost
# ═══════════════════════════════════════════════════════════════════


class TestToastManager:
    def test_instance_is_singleton(self, qt_app):
        a = ToastManager.instance()
        b = ToastManager.instance()
        assert a is b

    def test_info_does_not_raise(self, qt_app):
        ToastManager.info("title")
        # 处理事件队列
        QCoreApplication.processEvents()
        QCoreApplication.processEvents()

    def test_success_with_message(self, qt_app):
        ToastManager.success("title", "message body")
        QCoreApplication.processEvents()
        QCoreApplication.processEvents()

    def test_warning_with_action(self, qt_app):
        cb = MagicMock()
        ToastManager.warning(
            "title", "msg", actions=(ToastAction("Act", cb),)
        )
        QCoreApplication.processEvents()
        QCoreApplication.processEvents()

    def test_error_with_custom_duration(self, qt_app):
        ToastManager.error("title", "msg", duration_ms=500)
        QCoreApplication.processEvents()
        QCoreApplication.processEvents()


class TestToastHost:
    def test_drain_renders_item(self, qt_app):
        host = _ToastHost()
        try:
            spec = ToastSpec(level="info", title="drained")
            host.enqueue(spec)
            host.drain_pending()
            # layout 应该多了一个 widget（_ToastItem）
            assert host.layout().count() >= 2  # toast + stretch
        finally:
            host.hide()

    def test_drain_empty_queue_is_noop(self, qt_app):
        host = _ToastHost()
        try:
            host.drain_pending()  # 不抛异常
        finally:
            host.hide()

    def test_multiple_toasts_stack_vertically(self, qt_app):
        host = _ToastHost()
        try:
            for i in range(3):
                host.enqueue(ToastSpec(level="info", title=f"t{i}"))
            host.drain_pending()
            # 3 个 toast + 1 个 stretch = 4 children
            assert host.layout().count() == 4
        finally:
            host.hide()


# ═══════════════════════════════════════════════════════════════════
# open_in_os / reveal_in_finder
# ═══════════════════════════════════════════════════════════════════


class TestPlatformOpeners:
    @patch("subprocess.Popen")
    def test_open_in_os_macos(self, mock_popen, qt_app):
        with patch("sys.platform", "darwin"):
            open_in_os("/tmp/test.mp4")
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert args[0] == "open"
        assert args[1] == "/tmp/test.mp4"

    @patch("subprocess.Popen")
    def test_reveal_in_finder_macos_file(self, mock_popen, qt_app):
        with patch("sys.platform", "darwin"):
            with patch("os.path.isdir", return_value=False):
                reveal_in_finder("/tmp/test.mp4")
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert args == ["open", "-R", "/tmp/test.mp4"]

    @patch("subprocess.Popen")
    def test_reveal_in_finder_macos_dir(self, mock_popen, qt_app):
        with patch("sys.platform", "darwin"):
            with patch("os.path.isdir", return_value=True):
                reveal_in_finder("/tmp/dir")
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert args == ["open", "/tmp/dir"]

    def test_open_in_os_empty_path_is_noop(self, qt_app):
        # 不抛异常即可
        open_in_os("")
        open_in_os("")  # 重复调用

    def test_reveal_in_finder_empty_path_is_noop(self, qt_app):
        reveal_in_finder("")

    @patch("subprocess.Popen", side_effect=FileNotFoundError)
    def test_open_failure_does_not_raise(self, mock_popen, qt_app):
        # 错误被 logger.warning 捕获，不应 raise
        open_in_os("/nonexistent")
