#!/usr/bin/env python3
"""Onboarding 引导单元测试（v2.5.0 端到端流程优化 Phase 4）。

覆盖：
- 5 个 hint 点的存在性 + 顺序
- 持久化: mark_hint_seen → get_pending_hints 反映
- reset_onboarding 清除所有已看 hint
- OnboardingTooltip widget 渲染 + 信号
"""

from __future__ import annotations

import os

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QPushButton

from app.ui.main.widgets.onboarding import (
    _HINTS,
    OnboardingTooltip,
    get_pending_hints,
    mark_hint_seen,
    reset_onboarding,
)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_ONBOARDING_KEY = "onboarding/done"


@pytest.fixture(autouse=True)
def _clean_qsettings(qapp):
    """每个测试前清空 onboarding QSettings,避免相互污染。"""
    settings = QSettings("SceneFab", "Application")
    settings.remove(_ONBOARDING_KEY)
    settings.sync()
    yield
    settings.remove(_ONBOARDING_KEY)
    settings.sync()


@pytest.fixture
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


# ═══════════════════════════════════════════════════════════════════
# Hint 列表
# ═══════════════════════════════════════════════════════════════════


class TestHintCatalog:
    def test_five_hints_in_order(self):
        assert len(_HINTS) == 5

    def test_hint_ids_unique(self):
        ids = [h.hint_id for h in _HINTS]
        assert len(set(ids)) == 5

    def test_hint_ids_match_anchors(self):
        """hint_ids 与端到端流程关键节点对应,顺序从导入→流水线→启动→成果卡→通知。"""
        expected = (
            "import_video",
            "pipeline_steps",
            "start_ai",
            "summary_card",
            "toast_notifications",
        )
        actual = tuple(h.hint_id for h in _HINTS)
        assert actual == expected

    def test_each_hint_has_translation_keys(self):
        for h in _HINTS:
            assert h.title_key.startswith("onboarding.")
            assert h.body_key.startswith("onboarding.")
            assert h.title_key != h.body_key


# ═══════════════════════════════════════════════════════════════════
# 持久化
# ═══════════════════════════════════════════════════════════════════


class TestPersistence:
    def test_initial_all_pending(self):
        """新用户(从未看过任何 hint)应看到全部 5 个。"""
        pending = get_pending_hints()
        assert len(pending) == 5
        assert [h.hint_id for h in pending] == [h.hint_id for h in _HINTS]

    def test_mark_one_hint_seen(self):
        mark_hint_seen("import_video")
        pending = get_pending_hints()
        assert len(pending) == 4
        assert all(h.hint_id != "import_video" for h in pending)

    def test_mark_all_hints_seen_returns_empty(self):
        for h in _HINTS:
            mark_hint_seen(h.hint_id)
        assert get_pending_hints() == []

    def test_mark_unknown_id_does_not_raise(self):
        """防御: 未知 hint_id 写入 QSettings 也不抛错。"""
        mark_hint_seen("nonexistent_hint")
        pending = get_pending_hints()
        # 仍然 5 个
        assert len(pending) == 5

    def test_reset_onboarding_clears_all(self):
        for h in _HINTS:
            mark_hint_seen(h.hint_id)
        assert get_pending_hints() == []
        reset_onboarding()
        assert len(get_pending_hints()) == 5

    def test_persistence_survives_qsettings_reload(self):
        """mark_hint_seen 写盘后,新 QSettings 实例应能读到。"""
        mark_hint_seen("start_ai")
        # 模拟跨进程:重新构造 QSettings
        settings = QSettings("SceneFab", "Application")
        raw = settings.value(_ONBOARDING_KEY, "", type=str)
        assert "start_ai" in raw.split(",")


# ═══════════════════════════════════════════════════════════════════
# OnboardingTooltip widget
# ═══════════════════════════════════════════════════════════════════


class TestOnboardingTooltip:
    def test_widget_constructs(self, qapp):
        tooltip = OnboardingTooltip(_HINTS[0])
        assert tooltip.objectName() == "onboarding_tooltip_import_video"
        tooltip.deleteLater()

    def test_widget_has_title_and_body(self, qapp):
        from PySide6.QtWidgets import QLabel

        tooltip = OnboardingTooltip(_HINTS[1])
        labels = tooltip.findChildren(QLabel)
        # 至少 2 个 label(title + body)
        assert len(labels) >= 2
        tooltip.deleteLater()

    def test_widget_has_acknowledge_button(self, qapp):
        tooltip = OnboardingTooltip(_HINTS[0])
        btn = tooltip.findChild(QPushButton)
        assert btn is not None
        tooltip.deleteLater()

    def test_acknowledge_emits_signal(self, qapp):
        tooltip = OnboardingTooltip(_HINTS[0])
        captured: list[str] = []
        tooltip.hint_acknowledged.connect(lambda hid: captured.append(hid))
        tooltip._on_acknowledge()
        assert captured == ["import_video"]
        # 同时标记为已看
        assert "import_video" not in [h.hint_id for h in get_pending_hints()]
        tooltip.deleteLater()

    def test_hide_after_acknowledge(self, qapp):
        tooltip = OnboardingTooltip(_HINTS[0])
        tooltip.show()
        qapp.processEvents()
        tooltip._on_acknowledge()
        assert not tooltip.isVisible()
        tooltip.deleteLater()

    def test_each_hint_renders_unique_object_name(self, qapp):
        names = {OnboardingTooltip(h).objectName() for h in _HINTS}
        assert len(names) == 5
