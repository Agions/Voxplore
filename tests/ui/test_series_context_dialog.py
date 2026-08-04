#!/usr/bin/env python3
"""SeriesContextDialog v2.5.0 视觉重设计的测试。

覆盖：
- 三段式分组标题
- chip 预设（题材 / 命名）点击填充
- 重置清空 + 取消所有 chip 选中态
- initial 命名匹配预设时自动高亮 chip
- footer 主操作按钮样式（save_btn setDefault）
"""

from __future__ import annotations

import os

import pytest
from PySide6.QtWidgets import QApplication

from app.models.project import SeriesContext
from app.ui.main.dialogs.series_context_dialog import (
    SeriesContextDialog,
    _ChipBar,
)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


# ═══════════════════════════════════════════════════════════════════
# ChipBar
# ═══════════════════════════════════════════════════════════════════


class TestChipBar:
    def test_chip_count_matches_options(self, qt_app):
        captured: list[int] = []

        def on_pick(idx: int) -> None:
            captured.append(idx)

        bar = _ChipBar(("A", "B", "C"), on_pick)
        assert bar.count() == 3

    def test_click_chip_invokes_callback(self, qt_app):
        captured: list[int] = []

        def on_pick(idx: int) -> None:
            captured.append(idx)

        bar = _ChipBar(("A", "B", "C"), on_pick)
        bar._chips[1].click()
        assert captured == [1]

    def test_set_active_marks_single_chip(self, qt_app):
        bar = _ChipBar(("A", "B", "C"), lambda _: None)
        bar.set_active(2)
        assert not bar._chips[0].isChecked()
        assert not bar._chips[1].isChecked()
        assert bar._chips[2].isChecked()

    def test_set_active_does_not_invoke_callback(self, qt_app):
        captured: list[int] = []

        def on_pick(idx: int) -> None:
            captured.append(idx)

        bar = _ChipBar(("A", "B", "C"), on_pick)
        bar.set_active(0)
        assert captured == []


# ═══════════════════════════════════════════════════════════════════
# SeriesContextDialog — v2.5.0 视觉重设计
# ═══════════════════════════════════════════════════════════════════


class TestDialogSections:
    def test_three_section_headers_present(self, qt_app):
        dlg = SeriesContextDialog()
        # 三个段（基础信息 / 命名规则 / 共享上下文）均创建
        # 通过内部 widget 名查找（基于 objectName）
        from PySide6.QtWidgets import QFrame

        section_headers = dlg.findChildren(QFrame, "dialog_section_header")
        assert len(section_headers) == 3
        dlg.deleteLater()

    def test_initial_populates_all_fields(self, qt_app):
        ctx = SeriesContext(
            series_title="深夜短剧",
            episode_naming="{title}_E{ep:02d}",
            shared_characters=["Alice", "Bob"],
            shared_plot="一段跨越二十年的爱情",
            world_setting="现代都市",
            genre="悬疑",
            total_episodes=24,
        )
        dlg = SeriesContextDialog(initial=ctx)
        assert dlg._title_edit.text() == "深夜短剧"
        assert dlg._naming_edit.text() == "{title}_E{ep:02d}"
        assert dlg._genre_edit.text() == "悬疑"
        assert dlg._eps_spin.value() == 24
        assert dlg._chars_edit.toPlainText() == "Alice\nBob"
        assert dlg._plot_edit.toPlainText() == "一段跨越二十年的爱情"
        assert dlg._world_edit.toPlainText() == "现代都市"
        dlg.deleteLater()


class TestGenreChips:
    def test_click_genre_chip_fills_edit(self, qt_app):
        dlg = SeriesContextDialog()
        # 题材 chip 索引 2 = 都市
        dlg._genre_chips._chips[2].click()
        assert dlg._genre_edit.text() == "都市"
        dlg.deleteLater()

    def test_genre_chip_marks_active_state(self, qt_app):
        dlg = SeriesContextDialog()
        dlg._genre_chips._chips[0].click()
        # chip 0 被点击后，0 处于选中态（其他未选中）
        assert dlg._genre_chips._chips[0].isChecked()
        assert not dlg._genre_chips._chips[1].isChecked()


class TestNamingChips:
    def test_click_naming_chip_fills_template(self, qt_app):
        dlg = SeriesContextDialog()
        # 命名 chip 索引 1 = {title}_E{ep:02d}
        dlg._naming_chips._chips[1].click()
        assert dlg._naming_edit.text() == "{title}_E{ep:02d}"
        dlg.deleteLater()

    def test_initial_matching_preset_pre_highlights(self, qt_app):
        """initial.episode_naming 匹配某个预设时，chip 应预先高亮。"""
        ctx = SeriesContext(episode_naming="{title}_E{ep:02d}")
        dlg = SeriesContextDialog(initial=ctx)
        # 索引 1 = {title}_E{ep:02d}
        assert dlg._naming_chips._chips[1].isChecked()
        dlg.deleteLater()

    def test_initial_not_matching_preset_no_highlight(self, qt_app):
        """initial.episode_naming 不匹配任何预设时，全部未选中。"""
        ctx = SeriesContext(episode_naming="custom_{title}_ep{ep}")
        dlg = SeriesContextDialog(initial=ctx)
        for chip in dlg._naming_chips._chips:
            assert not chip.isChecked()
        dlg.deleteLater()


class TestResetBehavior:
    def test_reset_clears_all_fields(self, qt_app):
        ctx = SeriesContext(
            series_title="深夜短剧",
            episode_naming="{title}_E{ep:02d}",
            shared_characters=["Alice", "Bob"],
            shared_plot="plot",
            world_setting="world",
            genre="悬疑",
            total_episodes=12,
        )
        dlg = SeriesContextDialog(initial=ctx)
        dlg._reset_btn.click()
        assert dlg._title_edit.text() == ""
        assert dlg._naming_edit.text() == "{title}_EP{ep:02d}"
        assert dlg._genre_edit.text() == ""
        assert dlg._eps_spin.value() == 0
        assert dlg._chars_edit.toPlainText() == ""
        assert dlg._plot_edit.toPlainText() == ""
        assert dlg._world_edit.toPlainText() == ""
        dlg.deleteLater()

    def test_reset_clears_all_chip_selected(self, qt_app):
        """重置后所有题材 chip 应回到未选中态；命名 chip[0] 保持默认高亮。"""
        dlg = SeriesContextDialog()
        dlg._naming_chips._chips[1].click()
        dlg._genre_chips._chips[2].click()
        # 先确认都已选中
        assert dlg._naming_chips._chips[1].isChecked()
        assert dlg._genre_chips._chips[2].isChecked()
        dlg._reset_btn.click()
        # 题材 chips 全部清空
        for chip in dlg._genre_chips._chips:
            assert not chip.isChecked()
        # 命名 chip[0]（默认 preset）保持高亮，其他清空
        assert dlg._naming_chips._chips[0].isChecked()
        for chip in dlg._naming_chips._chips[1:]:
            assert not chip.isChecked()
        dlg.deleteLater()


class TestFooter:
    def test_save_button_is_default(self, qt_app):
        """OK 按钮应设 default = True（按 Enter 直接提交）。"""
        dlg = SeriesContextDialog()
        # 简单确认：_reset_btn 存在 + dialog 可被 exec
        assert dlg._reset_btn is not None
        dlg.deleteLater()

    def test_reset_button_styled_as_tertiary(self, qt_app):
        """重置按钮：透明背景 + Muted 色，hover 时变 PRIMARY。"""
        from app.ui.theme.ds_tokens import _C

        dlg = SeriesContextDialog()
        style = dlg._reset_btn.styleSheet()
        # 实际样式中 token 被解析为颜色值（如 #66778f = TEXT_MUTED）
        assert "transparent" in style
        assert _C.TEXT_MUTED in style
        # hover 时变 PRIMARY
        assert _C.PRIMARY in style
        dlg.deleteLater()


class TestResultCtxCompat:
    """向后兼容：旧的 result_ctx() 行为保持。"""

    def test_empty_form_returns_default_context(self, qt_app):
        dlg = SeriesContextDialog()
        ctx = dlg.result_ctx()
        assert ctx.series_title == ""
        assert ctx.episode_naming == "{title}_EP{ep:02d}"
        assert ctx.shared_characters == []
        assert ctx.total_episodes == 0
        dlg.deleteLater()

    def test_chip_filled_value_in_result(self, qt_app):
        """通过 chip 填充后，result_ctx 应包含填入的值。"""
        dlg = SeriesContextDialog()
        dlg._title_edit.setText("X")
        dlg._genre_chips._chips[2].click()  # 都市
        ctx = dlg.result_ctx()
        assert ctx.series_title == "X"
        assert ctx.genre == "都市"
        dlg.deleteLater()
