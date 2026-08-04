#!/usr/bin/env python3
"""ProductionSummaryCard 单元测试（v2.5.0 端到端流程优化 Phase 2）。

覆盖：
- 助手函数 _humanize_size / _humanize_duration
- 默认隐藏 + 初始按钮状态
- show_result 展开 + 路径/指标填充 + 按钮启用态
- clear() 重置
- 4 个按钮信号（close / open_file / open_folder / save）
- set_project_path 动态更新
- retranslate 不破坏 value
"""

from __future__ import annotations

import os

import pytest
from PySide6.QtWidgets import QApplication, QPushButton

from app.ui.main.widgets.production_summary import (
    ProductionSummaryCard,
    _humanize_duration,
    _humanize_size,
)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


# ═══════════════════════════════════════════════════════════════════
# Helper functions
# ═══════════════════════════════════════════════════════════════════


class TestHumanizeSize:
    def test_bytes(self):
        assert _humanize_size(0) == "0 B"
        assert _humanize_size(500) == "500 B"
        assert _humanize_size(1023) == "1023 B"

    def test_kilobytes(self):
        assert _humanize_size(1024) == "1.0 KB"
        assert _humanize_size(2048) == "2.0 KB"
        assert _humanize_size(1536) == "1.5 KB"

    def test_megabytes(self):
        assert _humanize_size(1024 * 1024) == "1.0 MB"
        assert _humanize_size(1024 * 1024 * 3) == "3.0 MB"

    def test_gigabytes(self):
        assert _humanize_size(1024 * 1024 * 1024) == "1.00 GB"
        assert _humanize_size(1024 * 1024 * 1024 * 2) == "2.00 GB"


class TestHumanizeDuration:
    def test_zero_or_negative(self):
        assert _humanize_duration(0) == "0.0s"
        assert _humanize_duration(-5) == "0.0s"

    def test_seconds(self):
        assert _humanize_duration(15.5) == "15.5s"
        assert _humanize_duration(59.9) == "59.9s"

    def test_minutes(self):
        # 60s → 1m00.0s, 125.3s → 2m05.3s
        assert _humanize_duration(60) == "1m00.0s"
        assert _humanize_duration(125.3) == "2m05.3s"


# ═══════════════════════════════════════════════════════════════════
# ProductionSummaryCard
# ═══════════════════════════════════════════════════════════════════


class TestDefaults:
    def test_initially_hidden(self, qt_app):
        card = ProductionSummaryCard()
        assert not card.isVisible()
        card.deleteLater()

    def test_initial_buttons_disabled(self, qt_app):
        """没有路径时,open_* 按钮应禁用,save 始终可用。"""
        card = ProductionSummaryCard()
        open_file = card.findChild(QPushButton, "summary_open_file_btn")
        open_folder = card.findChild(QPushButton, "summary_open_folder_btn")
        save = card.findChild(QPushButton, "summary_save_btn")
        assert not open_file.isEnabled()
        assert not open_folder.isEnabled()
        assert save.isEnabled()
        card.deleteLater()


class TestShowResult:
    def test_show_result_makes_visible(self, qt_app, tmp_path):
        card = ProductionSummaryCard()
        project_path = str(tmp_path / "test.scene.json")
        card.show_result(
            project_path=project_path,
            elapsed_seconds=32.5,
            file_size_bytes=12400,
            steps_completed=5,
            steps_total=5,
        )
        assert card.isVisible()
        card.deleteLater()

    def test_show_result_populates_path_and_metrics(self, qt_app, tmp_path):
        card = ProductionSummaryCard()
        project_path = str(tmp_path / "深夜短剧_EP01.scene.json")
        card.show_result(
            project_path=project_path,
            elapsed_seconds=42.0,
            file_size_bytes=1024 * 1024 * 3,
            steps_completed=5,
            steps_total=5,
        )
        from PySide6.QtWidgets import QLabel

        path_lbl = card.findChild(QLabel, "summary_path")
        assert path_lbl is not None
        assert path_lbl.text() == project_path
        # 3 个 metric: elapsed / size / steps
        values = card.findChildren(QLabel, "summary_metric_value")
        assert len(values) == 3
        assert "s" in values[0].text()
        assert "MB" in values[1].text()
        assert "5" in values[2].text()  # 5/5
        card.deleteLater()

    def test_show_result_missing_file_disables_open_buttons(
        self, qt_app, tmp_path
    ):
        card = ProductionSummaryCard()
        nonexistent_path = str(tmp_path / "does_not_exist.scene.json")
        card.show_result(
            project_path=nonexistent_path,
            elapsed_seconds=10.0,
            file_size_bytes=0,
            steps_completed=5,
            steps_total=5,
        )
        open_file = card.findChild(QPushButton, "summary_open_file_btn")
        open_folder = card.findChild(QPushButton, "summary_open_folder_btn")
        assert not open_file.isEnabled()
        assert not open_folder.isEnabled()
        card.deleteLater()

    def test_show_result_existing_file_enables_buttons(
        self, qt_app, tmp_path
    ):
        card = ProductionSummaryCard()
        real_file = tmp_path / "real.scene.json"
        real_file.write_text("{}")
        card.show_result(
            project_path=str(real_file),
            elapsed_seconds=10.0,
            file_size_bytes=2,
            steps_completed=5,
            steps_total=5,
        )
        open_file = card.findChild(QPushButton, "summary_open_file_btn")
        open_folder = card.findChild(QPushButton, "summary_open_folder_btn")
        assert open_file.isEnabled()
        assert open_folder.isEnabled()
        card.deleteLater()


class TestClear:
    def test_clear_hides_card(self, qt_app, tmp_path):
        card = ProductionSummaryCard()
        project_path = str(tmp_path / "x.scene.json")
        card.show_result(project_path=project_path,
                         elapsed_seconds=10.0, file_size_bytes=0,
                         steps_completed=5, steps_total=5)
        assert card.isVisible()
        card.clear()
        assert not card.isVisible()
        card.deleteLater()

    def test_clear_resets_path(self, qt_app, tmp_path):
        card = ProductionSummaryCard()
        project_path = str(tmp_path / "x.scene.json")
        card.show_result(project_path=project_path,
                         elapsed_seconds=10.0, file_size_bytes=0,
                         steps_completed=5, steps_total=5)
        card.clear()
        from PySide6.QtWidgets import QLabel

        path_lbl = card.findChild(QLabel, "summary_path")
        assert path_lbl.text() == ""
        card.deleteLater()

    def test_clear_resets_metrics_to_dash(self, qt_app):
        card = ProductionSummaryCard()
        card.show_result(project_path="/tmp/x", elapsed_seconds=10.0,
                         file_size_bytes=1024, steps_completed=5, steps_total=5)
        card.clear()
        from PySide6.QtWidgets import QLabel

        values = card.findChildren(QLabel, "summary_metric_value")
        for v in values:
            assert v.text() == "—"
        card.deleteLater()


class TestSignals:
    def test_close_button_emits_dismissed(self, qt_app):
        card = ProductionSummaryCard()
        card.show_result(project_path="/tmp/x", elapsed_seconds=10.0,
                         file_size_bytes=0, steps_completed=5, steps_total=5)
        captured: list[int] = []
        card.dismissed.connect(lambda: captured.append(1))
        card._close_btn.click()
        assert captured == [1]
        assert not card.isVisible()
        card.deleteLater()

    def test_open_file_button_emits_with_path(self, qt_app, tmp_path):
        card = ProductionSummaryCard()
        real = tmp_path / "real.scene.json"
        real.write_text("{}")
        card.show_result(project_path=str(real), elapsed_seconds=10.0,
                         file_size_bytes=2, steps_completed=5, steps_total=5)
        captured: list[str] = []
        card.open_file_clicked.connect(lambda p: captured.append(p))
        card._open_file_btn.click()
        assert captured == [str(real)]
        card.deleteLater()

    def test_open_folder_button_emits_with_path(self, qt_app, tmp_path):
        card = ProductionSummaryCard()
        real = tmp_path / "real.scene.json"
        real.write_text("{}")
        card.show_result(project_path=str(real), elapsed_seconds=10.0,
                         file_size_bytes=2, steps_completed=5, steps_total=5)
        captured: list[str] = []
        card.open_folder_clicked.connect(lambda p: captured.append(p))
        card._open_folder_btn.click()
        assert captured == [str(real)]
        card.deleteLater()

    def test_save_button_emits_save_project(self, qt_app):
        card = ProductionSummaryCard()
        captured: list[int] = []
        card.save_project_clicked.connect(lambda: captured.append(1))
        card._save_btn.click()
        assert captured == [1]
        card.deleteLater()


class TestSetProjectPath:
    def test_update_path_after_show(self, qt_app, tmp_path):
        card = ProductionSummaryCard()
        card.show_result(project_path="/tmp/a", elapsed_seconds=10.0,
                         file_size_bytes=0, steps_completed=5, steps_total=5)
        new_path_obj = tmp_path / "new.scene.json"
        new_path_obj.write_text("{}")
        new_path = str(new_path_obj)
        card.set_project_path(new_path)
        from PySide6.QtWidgets import QLabel

        path_lbl = card.findChild(QLabel, "summary_path")
        assert path_lbl.text() == new_path
        # 路径已存在 → open_file 应启用
        open_file = card.findChild(QPushButton, "summary_open_file_btn")
        assert open_file.isEnabled()
        card.deleteLater()

    def test_update_path_with_empty(self, qt_app, tmp_path):
        card = ProductionSummaryCard()
        real = tmp_path / "real.scene.json"
        real.write_text("{}")
        card.show_result(project_path=str(real), elapsed_seconds=10.0,
                         file_size_bytes=2, steps_completed=5, steps_total=5)
        card.set_project_path("")
        from PySide6.QtWidgets import QLabel

        path_lbl = card.findChild(QLabel, "summary_path")
        assert path_lbl.text() == ""
        open_file = card.findChild(QPushButton, "summary_open_file_btn")
        assert not open_file.isEnabled()
        card.deleteLater()


class TestRetranslate:
    def test_retranslate_does_not_crash(self, qt_app):
        card = ProductionSummaryCard()
        card.show_result(project_path="/tmp/x", elapsed_seconds=10.0,
                         file_size_bytes=0, steps_completed=5, steps_total=5)
        # 切换语言前后调用 retranslate 不应抛错
        card.retranslate()
        card.deleteLater()

    def test_retranslate_preserves_metrics(self, qt_app):
        """retranslate 不会清空已有的指标 value。"""
        card = ProductionSummaryCard()
        card.show_result(project_path="/tmp/x", elapsed_seconds=42.0,
                         file_size_bytes=2048, steps_completed=5, steps_total=5)
        from PySide6.QtWidgets import QLabel

        values_before = card.findChildren(QLabel, "summary_metric_value")
        elapsed_before = values_before[0].text()
        size_before = values_before[1].text()
        steps_before = values_before[2].text()
        card.retranslate()
        values_after = card.findChildren(QLabel, "summary_metric_value")
        assert values_after[0].text() == elapsed_before
        assert values_after[1].text() == size_before
        assert values_after[2].text() == steps_before
        card.deleteLater()
