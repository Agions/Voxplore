"""Main content area with stacked page views and animated transitions.

Supports four transition modes (set via :py:meth:`set_transition_mode`):

- ``"none"``     : no animation (instant swap, useful for tests / a11y).
- ``"fade"``     : 180ms opacity-only fade — the historical behavior.
- ``"cross-fade"``: 220ms opacity-only fade — the macOS HIG default.
- ``"slide"``    : 220ms opacity + 8px upward translateY, ease-out.

All modes share the same ``use-after-free``-safe animation lifecycle:
the per-widget ``QGraphicsOpacityEffect`` is reused, prior animations
have their ``finished`` signal disconnected + ``deleteLater()``-ed
before a new one starts, and the cleanup closure only clears the
effect it actually owns.
"""

from __future__ import annotations

from typing import Literal

from PySide6.QtCore import QEasingCurve, QPropertyAnimation
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsEffect,
    QGraphicsOpacityEffect,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.theme.ds_tokens import _C


TransitionMode = Literal["none", "fade", "cross-fade", "slide"]


# Per-mode timing constants (ms). Keep in one place so the macOS HIG
# numbers (200–300ms) stay consistent across callers.
_TRANSITION_DURATION_MS: dict[str, int] = {
    "fade": 180,
    "cross-fade": 220,
    "slide": 220,
}


class _VerticalSlideEffect(QGraphicsEffect):
    """Lightweight QGraphicsEffect that translates a widget by ``offset`` px.

    Positive ``offset`` shifts the rendered output downward; the
    entrance animation drives it from +8 → 0, producing the small
    upward "rise" specified in the macOS HIG. A simple custom effect
    avoids the complexity of animating widget geometry inside a
    QStackedWidget while still rendering correctly for both opaque
    and translucent content.
    """

    def __init__(self, offset: float = 0.0, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._offset = float(offset)

    def set_offset(self, offset: float) -> None:
        if offset != self._offset:
            self._offset = float(offset)
            self.update()

    def offset(self) -> float:
        return self._offset

    def draw(self, painter) -> None:  # type: ignore[override]
        if painter is None:
            return
        offset = self._offset
        if offset == 0.0:
            self.drawSource(painter)
            return
        # Translate the painter origin before delegating to the source.
        painter.translate(0.0, offset)
        self.drawSource(painter)
        painter.translate(0.0, -offset)


class ContentArea(QFrame):
    """主内容区域"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("content_area")
        self._setup_style()
        self._stack = QStackedWidget()
        self._page_map: dict[str, QWidget] = {}
        self._transition_mode: TransitionMode = "cross-fade"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._stack)

    def _setup_style(self):
        self.setStyleSheet(f"""
            #content_area {{
                background: {_C.BG_BASE};
            }}
        """)

    # ──────────────────────────────────────────────────────────
    # 公开 API
    # ──────────────────────────────────────────────────────────

    def add_page(self, page_id: str, widget: QWidget) -> None:
        widget.setObjectName(f"page_{page_id}")
        self._page_map[page_id] = widget
        self._stack.addWidget(widget)

    def set_page(self, page_id: str, animated: bool = True) -> None:
        if page_id not in self._page_map:
            return
        w = self._page_map[page_id]
        if self._stack.currentWidget() == w:
            return
        self._stack.setCurrentWidget(w)

        if not animated or self._transition_mode == "none":
            return
        self._animate_in(w, self._transition_mode)

    def set_transition_mode(self, mode: TransitionMode) -> None:
        if mode not in _TRANSITION_DURATION_MS and mode != "none":
            raise ValueError(
                f"Unknown transition mode: {mode!r}; "
                f"expected one of {sorted(_TRANSITION_DURATION_MS) + ['none']}"
            )
        self._transition_mode = mode

    def transition_mode(self) -> TransitionMode:
        return self._transition_mode

    # ──────────────────────────────────────────────────────────
    # 动画核心（use-after-free safe）
    # ──────────────────────────────────────────────────────────

    def _animate_in(self, widget: QWidget, mode: TransitionMode) -> None:
        """Run the configured entrance animation on ``widget``.

        The previous implementation created a new effect + animation on
        every call. Rapid sidebar clicks caused the *previous*
        animation's finished lambda to fire after a newer animation
        had replaced its effect — the lambda then cleared the effect
        the new animation was driving, which crashed the next opacity
        tick. The fix reuses the effect, disconnects the previous
        animation's signals, and only clears the effect from its own
        cleanup closure.
        """
        duration = _TRANSITION_DURATION_MS[mode]

        # Reuse or attach the opacity effect.
        eff = widget.graphicsEffect()
        if isinstance(eff, _VerticalSlideEffect):
            # If a slide effect is already attached, leave it in place
            # and just create a fresh opacity effect on top — the
            # painter chain still renders correctly because the slide
            # effect defers to its source.
            opacity_eff: QGraphicsEffect = eff
            # type: ignore[assignment]
            slide_eff: _VerticalSlideEffect | None = eff
        elif isinstance(eff, QGraphicsOpacityEffect):
            opacity_eff = eff
            slide_eff = None
        else:
            opacity_eff = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(opacity_eff)
            slide_eff = None

        # Cancel any in-flight opacity animation on this widget.
        prev_anim = getattr(widget, "_fade_anim", None)
        if prev_anim is not None:
            try:
                prev_anim.finished.disconnect()
            except (RuntimeError, TypeError):
                pass
            try:
                prev_anim.stop()
            except RuntimeError:
                pass
            prev_anim.deleteLater()

        # Cancel any in-flight slide (offset) animation.
        prev_slide = getattr(widget, "_slide_anim", None)
        if prev_slide is not None:
            try:
                prev_slide.finished.disconnect()
            except (RuntimeError, TypeError):
                pass
            try:
                prev_slide.stop()
            except RuntimeError:
                pass
            prev_slide.deleteLater()

        # Set up slide effect if mode requires it.
        if mode == "slide":
            if slide_eff is None:
                slide_eff = _VerticalSlideEffect(offset=8.0, parent=widget)
                # Stack: opacity effect → slide effect → widget
                opacity_eff.setParent(slide_eff)
                slide_eff.setParent(widget)
                widget.setGraphicsEffect(slide_eff)
            else:
                slide_eff.set_offset(8.0)
            assert slide_eff is not None  # for type-checker
            slide_anim = QPropertyAnimation(slide_eff, b"offset")
            slide_anim.setDuration(duration)
            slide_anim.setStartValue(8.0)
            slide_anim.setEndValue(0.0)
            slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        else:
            slide_anim = None

        # Make sure the opacity effect is the topmost in the chain.
        # If slide is active, opacity is its child and slide is the
        # widget's effect — so just animate the opacity effect.
        if isinstance(opacity_eff, QGraphicsOpacityEffect):
            opacity_eff.setOpacity(0.0)
        opacity_anim = QPropertyAnimation(opacity_eff, b"opacity")
        opacity_anim.setDuration(duration)
        opacity_anim.setStartValue(0.0)
        opacity_anim.setEndValue(1.0)
        opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        def _cleanup(
            _opacity=opacity_anim,
            _slide_anim=slide_anim,
            _opacity_eff=opacity_eff,
            _slide_eff=slide_eff,
            _w=widget,
        ):
            if getattr(_w, "_fade_anim", None) is _opacity:
                _w._fade_anim = None
            if _slide_anim is not None and getattr(_w, "_slide_anim", None) is _slide_anim:
                _w._slide_anim = None

        opacity_anim.finished.connect(_cleanup)
        opacity_anim.start()
        widget._fade_anim = opacity_anim
        if slide_anim is not None:
            slide_anim.start()
            widget._slide_anim = slide_anim


__all__ = ["ContentArea", "TransitionMode"]
