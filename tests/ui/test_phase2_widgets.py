"""Tests for Phase 2 widgets (GlassCard / RingChart / LineChart)."""

from __future__ import annotations

import os

import pytest

PySide6 = pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from app.ui.theme import ds_tokens  # noqa: E402
from app.ui.theme.ds_tokens import set_theme_mode  # noqa: E402


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


# ────────────────────────────────────────────────────────────────
#  GlassCard
# ────────────────────────────────────────────────────────────────


def test_glass_card_light_qss_contains_light_tokens(qt_app: QApplication) -> None:
    """Light mode stays with ``rgba(255,255,255,0.7)`` (translucent white)."""
    from app.ui.widgets.glass_card import GlassCard

    set_theme_mode("light")
    card = GlassCard(title="CPU")
    qt_app.processEvents()
    qss = card.styleSheet()
    assert "rgba(255,255,255,0.7)" in qss, qss
    assert "QFrame#glass_card" in qss


def test_glass_card_theme_switch_refreshes_qss(qt_app: QApplication) -> None:
    """After ``set_theme_mode('dark')`` + ``apply_palette()``, BG_GLASS
    becomes the dark translucent surface."""
    from app.ui.widgets.glass_card import GlassCard

    set_theme_mode("light")
    card = GlassCard(title="MEM")
    qt_app.processEvents()
    assert "rgba(255,255,255,0.7)" in card.styleSheet()

    set_theme_mode("dark")
    card.apply_palette()
    qt_app.processEvents()
    qss = card.styleSheet()
    assert "rgba(17,24,39,0.6)" in qss, qss
    # hover border becomes dark neon-cyan
    assert "#22d3ee" in qss


def test_glass_card_glow_adds_extra_hover_rule(qt_app: QApplication) -> None:
    from app.ui.widgets.glass_card import GlassCard

    set_theme_mode("dark")
    plain = GlassCard(title="CPU")
    glowing = GlassCard(title="CPU", glow=True)
    qt_app.processEvents()

    assert glowing.styleSheet().count("#22d3ee") >= plain.styleSheet().count("#22d3ee")


def test_glass_card_set_title_updates_label(qt_app: QApplication) -> None:
    from app.ui.widgets.glass_card import GlassCard

    card = GlassCard(title="Original")
    assert card._title_lbl.text() == "Original"
    card.set_title("Updated")
    assert card._title_lbl.text() == "Updated"


# ────────────────────────────────────────────────────────────────
#  RingChart
# ────────────────────────────────────────────────────────────────


def test_ring_chart_set_value_updates_target(qt_app: QApplication) -> None:
    from app.ui.widgets import RingChart

    rc = RingChart(label="CPU", minimum=0, maximum=100)
    rc.set_value(42.0)
    assert rc._target == 42.0


def test_ring_chart_clamps_out_of_range(qt_app: QApplication) -> None:
    from app.ui.widgets import RingChart

    rc = RingChart(label="X", minimum=0, maximum=100)
    rc.set_value(200)
    assert rc._target == 100.0
    rc.set_value(-50)
    assert rc._target == 0.0


def test_ring_chart_label_and_unit_settable(qt_app: QApplication) -> None:
    from app.ui.widgets import RingChart

    rc = RingChart(label="CPU")
    rc.set_label("GPU")
    rc.set_unit("°C")
    assert rc._label == "GPU"
    assert rc._unit == "°C"


# ────────────────────────────────────────────────────────────────
#  LineChart
# ────────────────────────────────────────────────────────────────


def test_line_chart_capacity_honored(qt_app: QApplication) -> None:
    from app.ui.widgets import LineChart

    lc = LineChart(capacity=10)
    for v in range(100):
        lc.add_sample(float(v))
    assert len(lc.samples) == 10
    assert lc.samples[-1] == 99.0


def test_line_chart_extend_batch_appends(qt_app: QApplication) -> None:
    from app.ui.widgets import LineChart

    lc = LineChart(capacity=20)
    lc.extend_samples([1, 2, 3])
    assert len(lc.samples) == 3
    lc.extend_samples([4, 5])
    assert list(lc.samples) == [1, 2, 3, 4, 5]


def test_line_chart_clear_resets(qt_app: QApplication) -> None:
    from app.ui.widgets import LineChart

    lc = LineChart(capacity=5)
    lc.add_sample(1.0)
    lc.clear()
    assert len(lc.samples) == 0


def test_line_chart_theme_aware_brushes(qt_app: QApplication) -> None:
    from app.ui.widgets import LineChart

    set_theme_mode("light")
    lc = LineChart(capacity=5, stroke_color_token="NEON_CYAN")
    lc.add_sample(50.0)
    assert lc._stroke_color.name() == "#0891b2"

    set_theme_mode("dark")
    lc.apply_palette()
    assert lc._stroke_color.name() == "#22d3ee"
