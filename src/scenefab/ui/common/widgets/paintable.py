"""
PaintableWidget - 消除 UI 组件中重复的 QPainter paintEvent 模板

提供:
- 统一的 paintEvent 实现 (QPainter + Antialiasing)
- 模板方法 _paint(painter) 供子类覆写
- 可选 SmoothPixmapTransform 支持
"""

from __future__ import annotations

from PySide6.QtGui import QPainter, QPaintEvent
from PySide6.QtWidgets import QWidget


class PaintableWidget(QWidget):
    """
    可绘制 Widget 基类 — 消除 15+ 文件的 paintEvent 重复代码.

    子类只需覆写 _paint(painter) 方法即可, 无需手动创建 QPainter.

    使用示例::

        class MyWidget(PaintableWidget):
            def _paint(self, painter: QPainter) -> None:
                painter.drawEllipse(self.rect().center(), 20, 20)
    """

    # 子类可覆盖: 是否启用 SmoothPixmapTransform
    _smooth_pixmap: bool = False

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802
        """统一 paintEvent 模板: 创建 QPainter → 调用 _paint → 清理."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._smooth_pixmap:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        try:
            self._paint(painter)
        finally:
            painter.end()

    def _paint(self, painter: QPainter) -> None:
        """子类覆写此方法实现自定义绘制逻辑."""
