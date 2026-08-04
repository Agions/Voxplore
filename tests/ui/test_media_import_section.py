#!/usr/bin/env python3
"""素材导入 section 视觉重设计的测试（v2.5.0）。"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from app.models.project import SeriesContext
from app.ui.main.widgets.media_import_section import (
    MediaSummaryBar,
    SeriesContextPreview,
    StrategyChoiceCards,
    _format_duration,
    _format_size,
    compute_file_stats,
)

# v2.5.0: MediaSummaryBar / StrategyChoiceCards / SeriesContextPreview
# 是 Qt Widget，单元测试需要 QApplication。conftest.py 通常已经提供，
# 这里用 fixture 显式表达依赖。


@pytest.fixture
def qapp():
    """确保有 QApplication（与现有 UI 测试约定一致）。"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ═══════════════════════════════════════════════════════════════════
# MediaSummaryBar
# ═══════════════════════════════════════════════════════════════════


class TestMediaSummaryBar:
    def test_empty_state_is_hidden(self, qapp):
        bar = MediaSummaryBar()
        bar.update_stats(0, 0.0, 0)
        assert not bar.isVisible()

    def test_non_empty_is_visible(self, qapp):
        bar = MediaSummaryBar()
        bar.update_stats(3, 120.0, 1024 * 1024)
        assert bar.isVisible()

    def test_count_label_updates(self, qapp):
        bar = MediaSummaryBar()
        bar.update_stats(5, 0, 0)
        assert bar._count_label.text() == "5"

    def test_duration_format_seconds(self, qapp):
        bar = MediaSummaryBar()
        bar.update_stats(1, 90, 0)
        assert bar._duration_label.text() == "1:30"

    def test_duration_format_hours(self, qapp):
        bar = MediaSummaryBar()
        bar.update_stats(1, 3725, 0)  # 1h 2m 5s
        assert bar._duration_label.text() == "1:02:05"

    def test_size_format_kb(self, qapp):
        bar = MediaSummaryBar()
        bar.update_stats(1, 0, 2048)
        assert "KB" in bar._size_label.text()

    def test_add_more_emits_signal(self, qapp):
        bar = MediaSummaryBar()
        captured: list[int] = []

        def slot():
            captured.append(1)

        bar.add_more_clicked.connect(slot)
        bar._add_more_btn.click()
        assert captured == [1]

    def test_retranslate_refreshes_units(self, qapp):
        bar = MediaSummaryBar()
        bar.retranslate()
        # 至少单位标签有非空文本
        assert bar._count_unit.text() != ""
        assert bar._duration_unit.text() != ""
        assert bar._size_unit.text() != ""


# ═══════════════════════════════════════════════════════════════════
# StrategyChoiceCards
# ═══════════════════════════════════════════════════════════════════


class TestStrategyChoiceCards:
    def test_default_strategy_is_batch(self, qapp):
        cards = StrategyChoiceCards()
        assert cards.strategy() == "batch"

    def test_set_strategy_updates_value(self, qapp):
        cards = StrategyChoiceCards()
        cards.set_strategy("series")
        assert cards.strategy() == "series"

    def test_click_card_emits_strategy_changed(self, qapp):
        cards = StrategyChoiceCards()
        captured: list[str] = []

        def slot(value: str):
            captured.append(value)

        cards.strategy_changed.connect(slot)
        # 找到 single 卡片并 click
        single_card = cards._cards["single"]
        single_card.click()
        assert captured == ["single"]

    def test_only_one_card_checked(self, qapp):
        cards = StrategyChoiceCards()
        cards._cards["series"].click()
        cards._cards["single"].click()
        # QButtonGroup exclusive 保证只有最后一个选中
        assert cards.strategy() == "single"
        assert not cards._cards["series"].isChecked()
        assert cards._cards["single"].isChecked()

    def test_all_four_cards_present(self, qapp):
        cards = StrategyChoiceCards()
        assert set(cards._cards.keys()) == {
            "single", "concat", "batch", "series"}

    def test_retranslate_does_not_raise(self, qapp):
        cards = StrategyChoiceCards()
        cards.retranslate()
        # 每个卡片标题非空
        for card in cards._cards.values():
            assert card._title_lbl.text() != ""


# ═══════════════════════════════════════════════════════════════════
# SeriesContextPreview
# ═══════════════════════════════════════════════════════════════════


class TestSeriesContextPreview:
    def test_empty_context_shows_empty_state(self, qapp):
        preview = SeriesContextPreview()
        preview.set_context(None)
        assert "尚未" in preview._title_lbl.text(
        ) or "not set" in preview._title_lbl.text().lower()

    def test_context_without_title_shows_empty_state(self, qapp):
        preview = SeriesContextPreview()
        preview.set_context(SeriesContext())  # series_title 为空
        assert preview._title_lbl.text() != ""

    def test_full_context_shows_metadata(self, qapp):
        preview = SeriesContextPreview()
        ctx = SeriesContext(
            series_title="深夜短剧",
            total_episodes=12,
            genre="悬疑",
            shared_characters=["Alice", "Bob", "Carol", "Dave"],
        )
        preview.set_context(ctx)
        assert preview._title_lbl.text() == "深夜短剧"
        meta = preview._meta_lbl.text()
        assert "12" in meta or "集" in meta
        assert "Alice" in meta

    def test_edit_button_emits_signal(self, qapp):
        preview = SeriesContextPreview()
        captured: list[int] = []

        def slot():
            captured.append(1)

        preview.edit_clicked.connect(slot)
        preview._edit_btn.click()
        assert captured == [1]

    def test_more_than_three_characters_truncated(self, qapp):
        preview = SeriesContextPreview()
        ctx = SeriesContext(
            series_title="X",
            shared_characters=["A", "B", "C", "D", "E"],
        )
        preview.set_context(ctx)
        meta = preview._meta_lbl.text()
        # 前 3 个 + 等 N 人标记
        assert "A" in meta and "C" in meta


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════


class TestFormatHelpers:
    def test_format_duration_zero(self):
        assert _format_duration(0) == "0:00"

    def test_format_duration_minutes(self):
        assert _format_duration(125) == "2:05"

    def test_format_duration_negative_returns_zero(self):
        assert _format_duration(-5) == "0:00"

    def test_format_size_bytes(self):
        assert _format_size(512) == "512 B"

    def test_format_size_kb(self):
        assert "KB" in _format_size(2048)

    def test_format_size_gb(self):
        s = _format_size(2 * 1024 ** 3)
        assert "GB" in s


class TestComputeFileStats:
    def test_empty_list(self, tmp_path):
        assert compute_file_stats([]) == (0, 0.0, 0)

    def test_single_file(self, tmp_path):
        f = tmp_path / "a.mp4"
        f.write_bytes(b"x" * 1024)
        n, _dur, size = compute_file_stats([str(f)])
        assert n == 1
        assert size == 1024

    def test_missing_file_ignored(self, tmp_path):
        n, _dur, size = compute_file_stats([str(tmp_path / "missing.mp4")])
        assert n == 1
        assert size == 0

    def test_multiple_files_sum(self, tmp_path):
        f1 = tmp_path / "a.mp4"
        f2 = tmp_path / "b.mp4"
        f1.write_bytes(b"x" * 1024)
        f2.write_bytes(b"x" * 2048)
        n, _dur, size = compute_file_stats([str(f1), str(f2)])
        assert n == 2
        assert size == 3072
