#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QSlider, QScrollArea,
)
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QMouseEvent, QFont
)

from .subtitle_core import (
    SubtitleTrack, SubtitleBlock, MultiTrackSubtitleEditor,
    SubtitleStylePreset,
)

class TimeRulerWidget(QWidget):
    """
    时间标尺组件

    显示时间刻度和当前位置。

    Signals:
        position_changed(float): 位置改变信号（秒）
    """

    position_changed = Signal(float)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._duration: float = 0.0
        self._position: float = 0.0
        self._scale: float = 50.0  # px/sec
        self._markers: List[Tuple[float, str]] = []

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
        self._scale = max(10, min(scale, 200))
        self.update()

    def add_marker(self, time: float, label: str = "") -> None:
        """添加标记点"""
        self._markers.append((time, label))
        self.update()

    def clear_markers(self) -> None:
        """清空标记点"""
        self._markers.clear()
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # 背景
        painter.fillRect(self.rect(), QColor("#0D1117"))

        if self._duration <= 0:
            return

        # 绘制刻度
        painter.setPen(QPen(QColor("#334155"), 1))

        # 计算主刻度间隔
        sec_per_mark = 1
        if self._scale < 20:
            sec_per_mark = 10
        elif self._scale < 40:
            sec_per_mark = 5

        # 绘制刻度
        for sec in range(0, int(self._duration) + 1):
            x = sec * self._scale
            if x > w:
                break

            if sec % sec_per_mark == 0:
                if sec % 10 == 0:
                    # 长刻度 + 标签
                    painter.drawLine(int(x), h - 15, int(x), h)
                    painter.setPen(QPen(QColor("#94A3B8"), 10, Qt.AlignCenter))
                    painter.drawText(int(x) - 15, h - 18, 30, 14, Qt.AlignCenter, f"{sec}s")
                    painter.setPen(QPen(QColor("#334155"), 1))
                elif sec % 5 == 0:
                    # 中刻度
                    painter.drawLine(int(x), h - 10, int(x), h)
                else:
                    # 短刻度
                    painter.drawLine(int(x), h - 6, int(x), h)

        # 绘制标记点
        painter.setBrush(QBrush(QColor("#6366F1")))
        for marker_time, label in self._markers:
            x = marker_time * self._scale
            if 0 <= x <= w:
                painter.drawEllipse(int(x) - 4, h - 24, 8, 8)
                if label:
                    painter.drawText(int(x) + 6, h - 20, label)

        # 当前位置指示器
        pos_x = self._position * self._scale
        if 0 <= pos_x <= w:
            painter.setPen(QPen(QColor("#22D3EE"), 2))
            painter.drawLine(int(pos_x), 0, int(pos_x), h)

            # 三角形指示器
            painter.setBrush(QBrush(QColor("#22D3EE")))
            painter.drawPolygon([
                QPoint(int(pos_x) - 6, 0),
                QPoint(int(pos_x) + 6, 0),
                QPoint(int(pos_x), 8)
            ])

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._update_position(event.position().x())

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.LeftButton:
            self._update_position(event.position().x())

    def _update_position(self, x: float) -> None:
        if self._duration <= 0:
            return
        pos = x / self._scale
        pos = max(0, min(pos, self._duration))
        self._position = pos
        self.position_changed.emit(pos)
        self.update()


__all__ = ["TimeRulerWidget"]
