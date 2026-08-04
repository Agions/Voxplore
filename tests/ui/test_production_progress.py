#!/usr/bin/env python3
"""5 步流水线 ETA 估算 + 进度文案单元测试（v2.5.0 端到端流程优化 Phase 3）。

覆盖：
- cap_step_duration 边界值
- format_seconds 边界值
- ProgressETA 算法（无数据 / 完成 / 滑动窗口 / 重置）
- ProductionPageViewModel.eta_seconds 行为
- _render_active_label 三种文案分支
"""

from __future__ import annotations

import os

import pytest
from PySide6.QtWidgets import QApplication

from app.ui.main.pages.production_page import _render_active_label
from app.ui.main.widgets.production_progress import (
    _STEP_DURATION_CAP_SECONDS,
    ProgressETA,
    cap_step_duration,
    format_seconds,
)
from app.ui.viewmodels.production_viewmodel import ProductionPageViewModel

PySide6 = pytest.importorskip("PySide6")


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def vm(qapp):
    return ProductionPageViewModel()


# ═══════════════════════════════════════════════════════════════════
# Pure helpers (no Qt)
# ═══════════════════════════════════════════════════════════════════


class TestCapStepDuration:
    def test_negative_clamps_to_zero(self):
        assert cap_step_duration(-1.0) == 0.0
        assert cap_step_duration(-100.0) == 0.0

    def test_zero_unchanged(self):
        assert cap_step_duration(0.0) == 0.0

    def test_within_cap_unchanged(self):
        assert cap_step_duration(5.0) == 5.0
        assert cap_step_duration(
            _STEP_DURATION_CAP_SECONDS) == _STEP_DURATION_CAP_SECONDS

    def test_above_cap_clamped(self):
        above = _STEP_DURATION_CAP_SECONDS + 10
        assert cap_step_duration(above) == _STEP_DURATION_CAP_SECONDS
        # 极端值（如 1 小时）也被裁剪
        assert cap_step_duration(3600.0) == _STEP_DURATION_CAP_SECONDS


class TestFormatSeconds:
    def test_negative_or_zero(self):
        assert format_seconds(0) == "0.0s"
        assert format_seconds(-1.0) == "0.0s"

    def test_sub_minute(self):
        assert format_seconds(5.0) == "5.0s"
        assert format_seconds(59.9) == "59.9s"

    def test_minute_range(self):
        # 60 → 1m00.0s, 125.3 → 2m05.3s
        assert format_seconds(60) == "1m00.0s"
        assert format_seconds(125.3) == "2m05.3s"

    def test_long_duration_simplified(self):
        # 1 小时 5 分 = 3900s → 简化显示 65m
        assert format_seconds(3900) == "65m"


# ═══════════════════════════════════════════════════════════════════
# ProgressETA
# ═══════════════════════════════════════════════════════════════════


class TestProgressETA:
    def test_invalid_construction(self):
        with pytest.raises(ValueError):
            ProgressETA(total_steps=0)
        with pytest.raises(ValueError):
            ProgressETA(total_steps=5, window=0)

    def test_initial_state_no_data(self):
        eta = ProgressETA(total_steps=5)
        assert eta.total_steps == 5
        assert eta.completed_steps == 0
        assert not eta.has_data
        # 任何 completed 输入都返回 None（数据不足）
        assert eta.estimate_remaining(0) is None
        assert eta.estimate_remaining(3) is None

    def test_all_done_returns_zero(self):
        eta = ProgressETA(total_steps=5)
        # 边界：completed >= total 总是返回 0
        assert eta.estimate_remaining(5) == 0.0
        assert eta.estimate_remaining(10) == 0.0

    def test_single_step_records(self):
        eta = ProgressETA(total_steps=5, window=3)
        eta.record_step(10.0)
        assert eta.completed_steps == 1
        assert eta.has_data
        # 完成 1 步、剩 4 步：预测 = 10 × 4 = 40
        assert eta.estimate_remaining(1) == 40.0

    def test_sliding_window_average(self):
        eta = ProgressETA(total_steps=5, window=3)
        # 前 3 步耗时不同：8, 12, 10 → 平均 10
        eta.record_step(8.0)
        eta.record_step(12.0)
        eta.record_step(10.0)
        # 完成 3 步、剩 2 步：预测 = avg(8,12,10) × 2 = 20
        assert eta.estimate_remaining(3) == pytest.approx(20.0)

    def test_sliding_window_drops_oldest(self):
        """window=3 时，第 4 个数据应该替换第 1 个，而不是扩容到 4。"""
        eta = ProgressETA(total_steps=5, window=3)
        eta.record_step(100.0)  # 极端值，会被窗口"忘记"
        eta.record_step(10.0)
        eta.record_step(10.0)
        eta.record_step(10.0)
        # 窗口只看最近 3 步：(10, 10, 10) → 平均 10
        # 5 - 4 = 1 步剩余
        assert eta.estimate_remaining(4) == pytest.approx(10.0)

    def test_completed_clamps_to_total(self):
        eta = ProgressETA(total_steps=5)
        eta.record_step(5.0)
        # completed > total 也安全（UI 可能在边界条件下多调）
        assert eta.estimate_remaining(99) == 0.0

    def test_negative_completed_clamped_to_zero(self):
        eta = ProgressETA(total_steps=5)
        eta.record_step(10.0)
        # 负值容错为 0；剩余 = max(0, 5 - 0) = 5
        # 预测 = avg(10) * 5 = 50.0
        assert eta.estimate_remaining(-1) == pytest.approx(50.0)

    def test_reset_clears_history(self):
        eta = ProgressETA(total_steps=5)
        eta.record_step(10.0)
        eta.record_step(20.0)
        assert eta.completed_steps == 2
        eta.reset()
        assert eta.completed_steps == 0
        assert not eta.has_data
        assert eta.estimate_remaining(2) is None

    def test_cap_prevents_pollution(self):
        """超长单步被裁剪到上限，避免污染后续预测。"""
        eta = ProgressETA(total_steps=5)
        eta.record_step(3600.0)  # 1 小时，应被 cap 到 60
        # 平均 = 60, 剩余 4 步
        assert eta.estimate_remaining(1) == pytest.approx(
            _STEP_DURATION_CAP_SECONDS * 4
        )


# ═══════════════════════════════════════════════════════════════════
# VM eta_seconds 集成
# ═══════════════════════════════════════════════════════════════════


class TestVmEtaSeconds:
    def test_initial_eta_is_none(self, vm: ProductionPageViewModel):
        """新 VM 尚未积累任何数据，eta 应为 None。"""
        assert vm.eta_seconds is None

    def test_eta_signal_emitted_on_reset(self, vm: ProductionPageViewModel, qapp):
        """reset_pipeline 触发 eta_changed.emit(None),清空历史。"""
        events: list[object] = []
        vm.eta_changed.connect(lambda e: events.append(e))
        vm.reset_pipeline()
        assert events == [None]
        assert vm.eta_seconds is None

    def test_eta_signal_emitted_on_step_done(self, vm: ProductionPageViewModel, qapp):
        """每完成一步触发 eta_changed，记录该步耗时。"""
        events: list[object] = []
        vm.eta_changed.connect(lambda e: events.append(e))
        vm.start_pipeline("/tmp/fake.mp4", "test context")
        # 等 worker thread
        qapp.processEvents()
        # 模拟：直接调用 VM 内部方法完成第 0 步（绕开 worker thread）
        vm._mark_step_done(0)  # noqa: SLF001 - 测试内部方法
        # 至少一次 eta_changed 事件，值不再是 None
        assert any(e is not None for e in events)
        # 完成后 eta 应为正向预测（1 步完成，剩 4 步）
        assert vm.eta_seconds is not None
        assert vm.eta_seconds > 0


# ═══════════════════════════════════════════════════════════════════
# _render_active_label 文案分支
# ═══════════════════════════════════════════════════════════════════


class TestRenderActiveLabel:
    def test_none_eta_shows_simple(self):
        result = _render_active_label(None)
        assert "进行中" in result

    def test_zero_eta_shows_finished(self):
        result = _render_active_label(0.0)
        assert "即将完成" in result or "完成" in result

    def test_positive_eta_with_eta_string(self):
        result = _render_active_label(12.5)
        # 形如「进行中(预计剩余 12.5s)」
        assert "进行中" in result
        assert "12.5s" in result

    def test_minute_eta_formats_minutes(self):
        result = _render_active_label(125.0)
        assert "2m05.0s" in result


# ═══════════════════════════════════════════════════════════════════
# ProductionPage 集成验证（轻量 smoke）
# ═══════════════════════════════════════════════════════════════════


class TestProductionPageEtaRender:
    def test_active_step_label_includes_eta(self, qapp):
        """构造带 VM 的 ProductionPage，手动设置 step 状态为 active，
        确认 step_status 文案包含 ETA 文本。
        """
        from app.ui.main.pages.production_page import ProductionPage

        page = ProductionPage(viewmodel=ProductionPageViewModel(), parent=None)
        # 强制设置第 2 步为 active，并喂一个 ETA
        # VM 的 eta_seconds 默认 None → 文案应为「进行中…」
        page._vm._step_status[2] = "active"  # noqa: SLF001
        page._refresh_step_status()
        lbl = page._step_rows[2][3]
        assert lbl is not None
        assert "进行中" in lbl.text()
        page.deleteLater()

    def test_active_step_label_with_eta_value(self, qapp):
        """设置 VM 的 ETA 历史 → 文案应包含秒数。"""
        from app.ui.main.pages.production_page import ProductionPage

        vm = ProductionPageViewModel()
        vm._eta.record_step(7.5)  # noqa: SLF001
        page = ProductionPage(viewmodel=vm, parent=None)
        page._vm._step_status[0] = "active"  # noqa: SLF001
        page._refresh_step_status()
        lbl = page._step_rows[0][3]
        assert lbl is not None
        # 1 步完成，剩 4 步：avg(7.5) * 4 = 30.0s
        assert "30.0s" in lbl.text()
        page.deleteLater()
