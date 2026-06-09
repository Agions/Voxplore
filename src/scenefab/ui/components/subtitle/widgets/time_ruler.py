#!/usr/bin/env python3

"""
字幕时间尺组件

在字幕编辑时间线上显示时间刻度，支持缩放和拖拽定位。
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QMouseEvent, QPainter, QPen, QPoint
from PySide6.QtWidgets import QWidget


class TimeRulerWidget(QWidget):
    """
    时间标尺组件

    显示时间刻度和当前位置。

    Signals:
        position_changed(float): 位置改变信号（秒）
    """

    position_changed = Signal(float)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self._duration: float = 0.0
        self._position: float = 0.0
        self._scale: float = 50.0  # px/sec
        self._markers: list[tuple[float, str]] = []

        self.setMinimumHeight(30)
        self.setMaximumHeight(30)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)

    def set_duration(self, duration: float) -> None:
        """设置总时长（秒）"""
        self._duration = duration
        self.update()

    def set_position(self, pos: float) -> None:
        """设置当前播放位置"""
        self._position = max(0, min(pos, self._duration)) if self._duration > 0 else 0
        self.update()

    def set_scale(self, scale: float) -> None:
        """设置缩放比例"""
        self._scale = scale
        self.update()

    def set_markers(self, markers: list[tuple[float, str]]) -> None:
        """设置标记点"""
        self._markers = markers
        self.update()

    def paintEvent(self, event) -> None:
        """绘制时间标尺"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 背景
        painter.fillRect(self.rect(), QColor("#0D1117"))

        if self._duration <= 0:
            return

        # 绘制刻度
        width = self.width()
        sec_per_px = self._duration / width

        # 主刻度（每秒）
        major_step = 1.0
        if sec_per_px < 0.1:
            major_step = 10.0
        elif sec_per_px < 0.5:
            major_step = 5.0
        elif sec_per_px > 2.0:
            major_step = 0.5

        for t in range(int(self._duration) + 1):
            if t % major_step != 0:
                continue
            x = int(t / sec_per_px)
            if x > width:
                break
            painter.setPen(QPen(QColor("#334155"), 1))
            painter.drawLine(x, 0, x, 8)

        # 绘制当前位置
        if self._position > 0:
            pos_x = self._position / sec_per_px
            if 0 <= pos_x <= width:
                # 绘制三角形标记
                painter.setPen(QPen(QColor("#22D3EE"), 2))
                painter.setBrush(QBrush(QColor("#22D3EE")))
                painter.drawPolygon(
                    QPoint(int(pos_x) - 6, 0),
                    QPoint(int(pos_x) + 6, 0),
                    QPoint(int(pos_x), 8),
                )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """鼠标按下"""
        if event.button() == Qt.LeftButton:
            self._update_position(event.position().x())

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """鼠标移动"""
        if event.buttons() & Qt.LeftButton:
            self._update_position(event.position().x())

    def _update_position(self, x: float) -> None:
        """更新位置"""
        if self._duration <= 0:
            return
        sec_per_px = self._duration / self.width()
        pos = max(0, min(x * sec_per_px, self._duration))
        self.set_position(pos)
        self.position_changed.emit(pos)


__all__ = ["TimeRulerWidget"]
