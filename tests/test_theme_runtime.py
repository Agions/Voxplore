#!/usr/bin/env python3
"""Tests for runtime theme helpers (Phase 3+ P1).

Covers:
- restyle_app returns 0 when no QApplication exists (headless test path)
- restyle_app accepts an explicit app argument (multi-app tests)
- ThemeAwareMixin.apply_theme re-evaluates the bound builder and
  reflects the latest _C values
- ThemeAwareMixin is independent of Qt (mixin only)
- The unified :mod:`scenefab.ui.theme` package re-exports both runtimes
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

# PySide6.QtWidgets import links against libEGL on Linux headless runners
# (GitHub Actions ubuntu-latest). When the shared library is missing the
# whole test module is uncollectible — gate the import at module load and
# mark every test in this module as ``skip`` so CI sees a clean exit code
# instead of an ``ERROR`` that fails the suite.
import pytest as _pytest_import_gate

try:
    from PySide6.QtWidgets import QApplication as _QApplication
except (ImportError, OSError) as _exc:  # noqa: BLE001 — gate all import paths
    _pytest_import_gate.skip(allow_module_level=True, reason=f"PySide6.QtWidgets unavailable: {_exc}")
QApplication = _QApplication

from scenefab.ui.theme import (  # noqa: E402  (after importorskip)
    _C,
    Colors,
    DarkColors,
    get_theme_mode,
    set_theme_mode,
)
from scenefab.ui.theme.runtime import ThemeAwareMixin, restyle_app  # noqa: E402


@pytest.fixture(autouse=True)
def reset_theme_mode():
    """Reset global theme between tests — restyle_app must not pollute others."""
    set_theme_mode("light")
    yield
    set_theme_mode("light")


@pytest.fixture
def no_qapp(monkeypatch):
    """Force :func:`QApplication.instance` to return ``None`` for the test.

    Phase 3 callers may already have constructed a ``QApplication`` in the
    same process (other tests in the suite). The headless branch of
    :func:`restyle_app` must be exercised in isolation — otherwise we
    silently iterate over every live widget some prior test left behind
    and the test asserts "0 restyled" against reality's "140 restyled".

    We patch the ``PySide6.QtWidgets.QApplication.instance`` class method
    directly rather than the symbol inside :mod:`runtime` because the
    runtime module imports Qt *lazily* inside :func:`restyle_app` — the
    ``scenefab.ui.theme.runtime.QApplication`` namespace has no attribute
    to monkeypatch.
    """
    monkeypatch.setattr(QApplication, "instance", staticmethod(lambda *a, **kw: None))
    return monkeypatch


# ── runtime.restyle_app ────────────────────────────────────────────────


def test_restyle_app_returns_zero_without_qapplication(no_qapp):
    """No QApplication.instance() → 0, no exception (headless safety)."""
    # No QApplication has been constructed in this test session.
    # ``no_qapp`` fixture monkey-patches ``QApplication.instance`` to
    # return ``None`` so this branch is exercised in isolation even when
    # earlier tests in the same process already spun up a QApplication.
    count = restyle_app()
    assert count == 0


def test_restyle_app_returns_int(no_qapp):
    """The return type is always ``int`` for predictable signature contracts."""
    result = restyle_app()
    assert isinstance(result, int)


def test_restyle_app_accepts_explicit_app_argument(no_qapp) -> None:
    """The ``app`` parameter is reserved for tests with multiple QApplications."""
    # Even with no app, the explicit arg path should not crash.
    assert restyle_app(app=None) == 0


# ── runtime.ThemeAwareMixin ────────────────────────────────────────────


class _FakeWidget(ThemeAwareMixin):
    """Stand-in for a QWidget that satisfies the mixin's contract.

    ThemeAwareMixin only relies on ``_build_stylesheet`` and
    ``setStyleSheet`` — both trivially implemented here without Qt.
    """

    def __init__(self, builder: Callable[[], str]) -> None:
        self._calls: list[str] = []
        self._build_stylesheet = builder  # type: ignore[assignment]

    def setStyleSheet(self, qss: str) -> None:  # noqa: N802 - Qt naming
        self._calls.append(qss)


def test_theme_aware_mixin_apply_theme_runs_builder():
    """``apply_theme`` invokes ``_build_stylesheet`` once and stores the body."""
    calls = {"n": 0}

    def builder() -> str:
        calls["n"] += 1
        return f"BG={_C.BG_BASE}"

    widget = _FakeWidget(builder)
    out = widget.apply_theme()

    assert calls["n"] == 1
    assert out == "BG=#f6f8fb"  # light mode token value
    assert widget._calls == ["BG=#f6f8fb"]


def test_theme_aware_mixin_picks_up_token_changes():
    """Switching the theme and re-applying rebuilds with new values."""
    widget = _FakeWidget(lambda: f"BG={_C.BG_BASE}")

    widget.apply_theme()
    assert widget._calls[-1] == "BG=#f6f8fb"

    set_theme_mode("dark")
    widget.apply_theme()
    assert widget._calls[-1] == "BG=#0f172a"

    set_theme_mode("light")
    widget.apply_theme()
    assert widget._calls[-1] == "BG=#f6f8fb"


def test_theme_aware_mixin_does_not_require_qt():
    """Mixin itself is importable + usable with no QApplication running."""
    # ThemeAwareMixin has no Qt-derived methods we inherit, only the
    # apply_theme shim. This is mostly a regression guard against
    # accidentally depending on QWidget base class.
    assert "apply_theme" in dir(ThemeAwareMixin)
    # No Qt objects leaked into the MRO
    assert "QWidget" not in str(ThemeAwareMixin.__mro__)


# ── theme package public surface ───────────────────────────────────────


def test_theme_package_exports_runtimes():
    """The unified :mod:`scenefab.ui.theme` package re-exports both runtimes."""
    from scenefab.ui import theme as theme_pkg

    assert theme_pkg.restyle_app is restyle_app
    assert theme_pkg.ThemeAwareMixin is ThemeAwareMixin
    assert theme_pkg.set_theme_mode is set_theme_mode
    assert theme_pkg.get_theme_mode is get_theme_mode
    assert theme_pkg.Colors is Colors
    assert theme_pkg.DarkColors is DarkColors
