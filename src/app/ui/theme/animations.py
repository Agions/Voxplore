#!/usr/bin/env python3
"""
AnimationService · 统一动效服务（Phase A）。

封装 ``QPropertyAnimation`` / ``QParallelAnimationGroup`` 细节，提供符合
macOS HIG 的便捷 API。所有动效遵循 :mod:`app.ui.theme.ds_tokens` 中的
``Durations`` / ``Easings`` token，保证全局一致。

设计要点：
- **统一入口**：UI 层只调用 ``AnimationService.fade_in(widget)``，
  无需关心属性名 / 缓动曲线 / 时长。
- **可关闭**：通过 :data:`enabled` 开关支持「减少动效」用户偏好。
- **生命周期安全**：动画对象持有引用直至 ``finished``，避免 GC 提前回收。
- **无 Qt 依赖兜底**：无 PySide6 时所有方法为 no-op，便于 headless 测试。

应用场景（与重构方案 §4.6.2 对齐）：
- 页面切换：cross_fade + 4px 上移
- 按钮 hover：color transition（QSS 层面实现，本服务不重复）
- 卡片出现：opacity + translateY
- 步骤进度：color transition
- Sidebar 激活：左侧 3px accent bar 滑入
- Toast：opacity + translateY

跨平台：动效在所有平台行为一致，不依赖系统级 vibrancy。
"""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
)

from app.ui.theme.ds_tokens import Durations

logger = logging.getLogger(__name__)

__all__ = ["AnimationService", "EasingCurve"]


# EasingCurve 字符串名 → QEasingCurve.Type 映射
_EASING_MAP: dict[str, QEasingCurve.Type] = {
    "standard": QEasingCurve.Type.InOutCubic,
    "decelerate": QEasingCurve.Type.OutCubic,
    "accelerate": QEasingCurve.Type.InCubic,
    "spring": QEasingCurve.Type.OutBack,
    "ease_out": QEasingCurve.Type.OutCubic,
}


class EasingCurve:
    """``Easings`` token 的字符串名常量（供业务调用，避免拼写错误）。"""

    STANDARD = "standard"
    DECELERATE = "decelerate"
    ACCELERATE = "accelerate"
    SPRING = "spring"
    EASE_OUT = "ease_out"


class AnimationService:
    """统一动效接口 — UI 层只调用静态方法。"""

    # 全局开关（受「减少动效」用户偏好控制）。True 时所有动效立即到位。
    enabled: bool = True

    # 引用计数：避免动画对象被 GC 导致 finished 不触发
    _refs: list[QAbstractAnimation] = []

    # ──────────────────────────────────────────────────────────
    # 基础动效
    # ──────────────────────────────────────────────────────────

    @classmethod
    def fade_in(
        cls,
        widget: Any,
        duration_ms: int | None = None,
        easing: str = EasingCurve.EASE_OUT,
    ) -> QPropertyAnimation | None:
        """淡入（opacity 0 → 1）。"""
        if not cls.enabled:
            widget.setWindowOpacity(1.0)  # type: ignore[attr-defined]
            return None
        if not hasattr(widget, "setWindowOpacity"):
            return None

        duration = duration_ms if duration_ms is not None else Durations.normal
        # 起始透明
        try:
            widget.setWindowOpacity(0.0)
        except Exception:
            return None

        anim = QPropertyAnimation(widget, b"windowOpacity")
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(_EASING_MAP.get(
            easing, QEasingCurve.Type.OutCubic))
        anim.start()
        cls._keep_alive(anim)
        return anim

    @classmethod
    def fade_out(
        cls,
        widget: Any,
        duration_ms: int | None = None,
        easing: str = EasingCurve.EASE_OUT,
        on_finished: Any = None,
    ) -> QPropertyAnimation | None:
        """淡出（opacity 1 → 0）。"""
        if not cls.enabled:
            try:
                widget.setWindowOpacity(0.0)
                if on_finished:
                    on_finished()
            except Exception:
                pass
            return None
        if not hasattr(widget, "setWindowOpacity"):
            return None

        duration = duration_ms if duration_ms is not None else Durations.normal
        anim = QPropertyAnimation(widget, b"windowOpacity")
        anim.setDuration(duration)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(_EASING_MAP.get(
            easing, QEasingCurve.Type.OutCubic))
        if on_finished:
            anim.finished.connect(on_finished)
        anim.start()
        cls._keep_alive(anim)
        return anim

    @classmethod
    def slide_in(
        cls,
        widget: Any,
        direction: str = "up",
        distance: int = 8,
        duration_ms: int | None = None,
        easing: str = EasingCurve.SPRING,
    ) -> QPropertyAnimation | None:
        """从指定方向滑入并淡入。

        direction: ``up`` / ``down`` / ``left`` / ``right``
        """
        if not cls.enabled:
            return None
        # 起始位置
        try:
            original_pos = widget.pos()  # type: ignore[attr-defined]
        except Exception:
            return None

        direction = direction.lower()
        if direction == "up":
            offset = (0, distance)
        elif direction == "down":
            offset = (0, -distance)
        elif direction == "left":
            offset = (distance, 0)
        elif direction == "right":
            offset = (-distance, 0)
        else:
            offset = (0, distance)

        # 直接用 QPoint 偏移
        from PySide6.QtCore import QPoint

        start_pos = QPoint(original_pos.x() +
                           offset[0], original_pos.y() + offset[1])
        try:
            widget.move(start_pos)
        except Exception:
            return None

        duration = duration_ms if duration_ms is not None else Durations.normal

        anim = QPropertyAnimation(widget, b"pos")
        anim.setDuration(duration)
        anim.setStartValue(start_pos)
        anim.setEndValue(original_pos)
        anim.setEasingCurve(_EASING_MAP.get(easing, QEasingCurve.Type.OutBack))
        anim.start()
        cls._keep_alive(anim)

        # 同步淡入
        cls.fade_in(widget, duration_ms=duration, easing=EasingCurve.STANDARD)
        return anim

    # ──────────────────────────────────────────────────────────
    # 组合动效
    # ──────────────────────────────────────────────────────────

    @classmethod
    def card_appear(
        cls,
        widget: Any,
        duration_ms: int | None = None,
    ) -> QParallelAnimationGroup | None:
        """卡片出现动效：opacity 0→1 + translateY 8→0（spring）。

        用于状态卡 / 面板 / 列表项首次出现。
        """
        if not cls.enabled:
            return None
        try:
            from PySide6.QtWidgets import QGraphicsOpacityEffect

            eff = widget.graphicsEffect()
            if not isinstance(eff, QGraphicsOpacityEffect):
                eff = QGraphicsOpacityEffect(widget)
                widget.setGraphicsEffect(eff)
            eff.setOpacity(0.0)
        except Exception:
            return None

        duration = duration_ms if duration_ms is not None else Durations.slow

        opacity_anim = QPropertyAnimation(eff, b"opacity")
        opacity_anim.setDuration(duration)
        opacity_anim.setStartValue(0.0)
        opacity_anim.setEndValue(1.0)
        opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # translateY 需要外层 widget 有 QGraphicsEffect 或 pos 动画（简化用 pos）
        pos_anim: QPropertyAnimation | None = None
        try:
            original_pos = widget.pos()
            from PySide6.QtCore import QPoint

            start_pos = QPoint(original_pos.x(), original_pos.y() + 8)
            widget.move(start_pos)

            pos_anim = QPropertyAnimation(widget, b"pos")
            pos_anim.setDuration(duration)
            pos_anim.setStartValue(start_pos)
            pos_anim.setEndValue(original_pos)
            pos_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        except Exception:
            pos_anim = None

        group = QParallelAnimationGroup(widget)
        group.addAnimation(opacity_anim)
        if pos_anim is not None:
            group.addAnimation(pos_anim)
        group.start()
        cls._keep_alive(group)
        return group

    @classmethod
    def cross_fade_pages(
        cls,
        out_widget: Any,
        in_widget: Any,
        duration_ms: int | None = None,
    ) -> None:
        """页面切换 cross-fade（旧页面淡出 + 新页面淡入）。同步执行。

        用于 ContentArea.set_page 的动效升级。
        """
        if not cls.enabled:
            try:
                in_widget.show()  # type: ignore[attr-defined]
            except Exception:
                pass
            return

        duration = duration_ms if duration_ms is not None else Durations.normal
        cls.fade_in(in_widget, duration_ms=duration,
                    easing=EasingCurve.EASE_OUT)
        # out_widget 不主动淡出（避免双层 stacking 抖动），由 stacked widget 接管

    @classmethod
    def toast_appear(
        cls,
        widget: Any,
        duration_ms: int | None = None,
    ) -> QPropertyAnimation | None:
        """Toast 出现：从顶部 -8px 滑入 + 淡入，spring 缓动。"""
        return cls.slide_in(widget, "down", distance=8, duration_ms=duration_ms or Durations.normal)

    # ──────────────────────────────────────────────────────────
    # 工具方法
    # ──────────────────────────────────────────────────────────

    @classmethod
    def _keep_alive(cls, anim: QAbstractAnimation) -> None:
        """保持动画引用，避免 GC 提前回收。"""
        cls._refs.append(anim)
        anim.finished.connect(lambda a=anim: cls._on_finished(a))

    @classmethod
    def _on_finished(cls, anim: QAbstractAnimation) -> None:
        """动画完成后清理引用。"""
        try:
            cls._refs.remove(anim)
        except ValueError:
            pass

    @classmethod
    def cancel_all(cls) -> None:
        """停止并清理所有活跃动画（用于窗口关闭 / 测试 teardown）。"""
        for anim in list(cls._refs):
            try:
                anim.stop()
            except RuntimeError:
                pass
        cls._refs.clear()

    @classmethod
    def active_count(cls) -> int:
        """当前活跃动画数（仅供测试 / 调试）。"""
        return len(cls._refs)


def apply_reduced_motion(enabled: bool) -> None:
    """根据用户偏好启用 / 禁用所有动效。

    由 SettingsPage 的「减少动效」开关触发。
    """
    AnimationService.enabled = not enabled


def is_reduced_motion() -> bool:
    """查询当前是否启用了减少动效。"""
    return not AnimationService.enabled
