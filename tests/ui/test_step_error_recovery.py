#!/usr/bin/env python3
"""StepErrorRecovery 错误降级单元测试（v2.5.0 端到端流程优化 Phase 5）。

覆盖：
- is_network_error / is_config_error 关键字匹配
- classify_error 决策矩阵
- StepErrorBanner widget 渲染 + 信号
- banner_text / action_button_label i18n 渲染
- StepFailureContext 工厂方法
"""

from __future__ import annotations

import os

import pytest
from PySide6.QtWidgets import QApplication, QPushButton

from app.ui.main.widgets.step_error_recovery import (
    STEP_CRITICAL,
    RecoveryAction,
    StepErrorBanner,
    StepFailureContext,
    action_button_label,
    banner_text,
    classify_error,
    is_config_error,
    is_network_error,
)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


# ═══════════════════════════════════════════════════════════════════
# 错误分类纯函数
# ═══════════════════════════════════════════════════════════════════


class TestErrorClassifiers:
    @pytest.mark.parametrize(
        "msg",
        [
            "Connection timeout after 30s",
            "Network unreachable",
            "Rate limit exceeded",
            "服务暂时不可用",
            "网络连接断开",
        ],
    )
    def test_network_errors_detected(self, msg: str):
        assert is_network_error(Exception(msg)) is True

    def test_unrelated_error_not_network(self):
        assert is_network_error(ValueError("bad input")) is False

    @pytest.mark.parametrize(
        "msg",
        [
            "Missing API key",
            "Unauthorized (401)",
            "未配置 TTS_KEY",
            "invalid key",
        ],
    )
    def test_config_errors_detected(self, msg: str):
        assert is_config_error(Exception(msg)) is True

    def test_unrelated_error_not_config(self):
        assert is_config_error(ValueError("bad input")) is False


class TestClassifyErrorMatrix:
    def test_network_error_on_any_step_is_retry(self):
        for step_idx in range(5):
            exc = Exception("Network timeout")
            assert classify_error(exc, step_idx) == RecoveryAction.RETRY

    def test_config_error_is_always_fail(self):
        for step_idx in range(5):
            exc = Exception("API key not configured")
            assert classify_error(exc, step_idx) == RecoveryAction.FAIL

    def test_generic_error_on_critical_step_is_fail(self):
        # 步骤 0 (导入)、3 (配音)、4 (导出) 都是关键
        for step_idx in (0, 3, 4):
            exc = ValueError("something went wrong")
            assert classify_error(exc, step_idx) == RecoveryAction.FAIL

    def test_generic_error_on_optional_step_is_skip(self):
        # 步骤 1 (场景拆分)、2 (脚本生成) 是可选
        for step_idx in (1, 2):
            exc = ValueError("something went wrong")
            assert classify_error(exc, step_idx) == RecoveryAction.SKIP

    def test_step_critical_flags_match_design(self):
        """关键性标记: 0/3/4 关键;1/2 可选。"""
        assert STEP_CRITICAL == (True, False, False, True, True)

    def test_out_of_range_step_index_does_not_crash(self):
        exc = ValueError("x")
        # 防御:异常 step_index 不抛错
        assert classify_error(exc, -1) in RecoveryAction
        assert classify_error(exc, 99) in RecoveryAction


# ═══════════════════════════════════════════════════════════════════
# i18n 渲染
# ═══════════════════════════════════════════════════════════════════


class TestBannerText:
    def test_retry_banner_includes_error(self):
        text = banner_text(RecoveryAction.RETRY, "Network timeout")
        assert "Network timeout" in text

    def test_skip_banner_includes_error(self):
        text = banner_text(RecoveryAction.SKIP, "Script gen failed")
        assert "Script gen failed" in text

    def test_fail_banner_includes_error(self):
        text = banner_text(RecoveryAction.FAIL, "Config missing")
        assert "Config missing" in text

    def test_action_button_labels_differ(self):
        retry_label = action_button_label(RecoveryAction.RETRY)
        skip_label = action_button_label(RecoveryAction.SKIP)
        fail_label = action_button_label(RecoveryAction.FAIL)
        assert retry_label != skip_label != fail_label


# ═══════════════════════════════════════════════════════════════════
# StepFailureContext 工厂
# ═══════════════════════════════════════════════════════════════════


class TestStepFailureContext:
    def test_from_network_error(self):
        ctx = StepFailureContext.from_exception(
            2, Exception("Network timeout"))
        assert ctx.step_index == 2
        assert ctx.action == RecoveryAction.RETRY
        assert "Network timeout" in ctx.error_message

    def test_from_config_error(self):
        ctx = StepFailureContext.from_exception(
            3, Exception("Missing API key"))
        assert ctx.action == RecoveryAction.FAIL

    def test_from_generic_on_optional_step(self):
        ctx = StepFailureContext.from_exception(1, ValueError("oops"))
        assert ctx.action == RecoveryAction.SKIP

    def test_empty_error_message_falls_back_to_class_name(self):
        class CustomError(Exception):
            pass

        ctx = StepFailureContext.from_exception(2, CustomError(""))
        # 异常消息为空时,error_message 至少有类名兜底
        assert ctx.error_message  # truthy
        assert "CustomError" in ctx.error_message


# ═══════════════════════════════════════════════════════════════════
# StepErrorBanner widget
# ═══════════════════════════════════════════════════════════════════


class TestStepErrorBanner:
    def test_retry_banner_has_button(self, qapp):
        banner = StepErrorBanner(2, RecoveryAction.RETRY, "Network timeout")
        btn = banner.findChild(QPushButton)
        assert btn is not None
        banner.deleteLater()

    def test_skip_banner_has_button(self, qapp):
        banner = StepErrorBanner(1, RecoveryAction.SKIP, "Script gen failed")
        btn = banner.findChild(QPushButton)
        assert btn is not None
        banner.deleteLater()

    def test_fail_banner_has_button(self, qapp):
        banner = StepErrorBanner(0, RecoveryAction.FAIL, "Config missing")
        btn = banner.findChild(QPushButton)
        assert btn is not None
        banner.deleteLater()

    def test_retry_emits_signal(self, qapp):
        banner = StepErrorBanner(2, RecoveryAction.RETRY, "Network timeout")
        captured: list[int] = []
        banner.retry_requested.connect(lambda i: captured.append(i))
        banner._on_retry()
        assert captured == [2]
        assert not banner.isVisible()
        banner.deleteLater()

    def test_skip_emits_signal(self, qapp):
        banner = StepErrorBanner(1, RecoveryAction.SKIP, "Script failed")
        captured: list[int] = []
        banner.skip_requested.connect(lambda i: captured.append(i))
        banner._on_skip()
        assert captured == [1]
        assert not banner.isVisible()
        banner.deleteLater()

    def test_fail_dismiss_emits_signal(self, qapp):
        banner = StepErrorBanner(0, RecoveryAction.FAIL, "Config missing")
        captured: list[int] = []
        banner.fail_dismissed.connect(lambda i: captured.append(i))
        banner._on_dismiss()
        assert captured == [0]
        banner.deleteLater()

    def test_object_name_includes_step_index(self, qapp):
        banner = StepErrorBanner(3, RecoveryAction.RETRY, "x")
        assert banner.objectName() == "step_error_banner_3"
        banner.deleteLater()
