#!/usr/bin/env python3
"""Unit tests for the shared UI animation service."""

from __future__ import annotations

import pytest

try:
    from PySide6.QtCore import Property, QObject

    from app.ui.theme.animations import (
        AnimationService,
        EasingCurve,
        apply_reduced_motion,
        is_reduced_motion,
    )
except (ImportError, OSError) as exc:
    pytest.skip(
        f"PySide6 animation runtime unavailable: {exc}", allow_module_level=True)


class _OpacityTarget(QObject):
    def __init__(self) -> None:
        super().__init__()
        self._opacity = 1.0

    def _get_opacity(self) -> float:
        return self._opacity

    def setWindowOpacity(self, value: float) -> None:  # noqa: N802
        self._opacity = value

    windowOpacity = Property(float, _get_opacity, setWindowOpacity)


@pytest.fixture(autouse=True)
def reset_animation_service():
    AnimationService.cancel_all()
    AnimationService.enabled = True
    yield
    AnimationService.cancel_all()
    AnimationService.enabled = True


def test_reduced_motion_switch_is_global():
    apply_reduced_motion(True)
    assert is_reduced_motion() is True
    assert AnimationService.enabled is False

    apply_reduced_motion(False)
    assert is_reduced_motion() is False


def test_disabled_fade_in_applies_final_value_immediately():
    target = _OpacityTarget()
    AnimationService.enabled = False

    animation = AnimationService.fade_in(target)

    assert animation is None
    assert target._opacity == 1.0
    assert AnimationService.active_count() == 0


def test_fade_in_uses_requested_duration_and_keeps_reference():
    target = _OpacityTarget()

    animation = AnimationService.fade_in(target, duration_ms=123)

    assert animation is not None
    assert animation.duration() == 123
    assert animation.endValue() == 1.0
    assert AnimationService.active_count() == 1


def test_cancel_all_stops_and_releases_animations():
    target = _OpacityTarget()
    AnimationService.fade_in(target, duration_ms=500)
    assert AnimationService.active_count() == 1

    AnimationService.cancel_all()

    assert AnimationService.active_count() == 0


def test_easing_names_are_stable_public_constants():
    assert EasingCurve.STANDARD == "standard"
    assert EasingCurve.DECELERATE == "decelerate"
    assert EasingCurve.ACCELERATE == "accelerate"
    assert EasingCurve.SPRING == "spring"
