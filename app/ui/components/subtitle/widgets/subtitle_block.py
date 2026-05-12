#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal

from ..subtitle_core import SubtitleBlock, SubtitleStylePreset

class SubtitleBlockWidget(QWidget):
    """
    字幕块编辑组件

    显示单个字幕块，支持拖拽和调整大小。

    Signals:
        block_changed(str block_id): 字幕块改变信号
        block_selected(str block_id): 字幕块选中信号
    """

    block_changed = Signal(str)
    block_selected = Signal(str)

    def __init__(
        self,
        block: SubtitleBlock,
        style: SubtitleStylePreset,
        scale: float = 50.0,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        self._block = block
        self._style = style
        self._scale = scale
        self._is_selected = False
        self._is_dragging = False
        self._is_resizing = False
        self._drag_start_x = 0
        self._original_start = 0.0
        self._original_end = 0.0

        self.setMinimumHeight(36)
        self.setCursor(Qt.SizeHorCursor)
        self.setMouseTracking(True)

    def set_scale(self, scale: float) -> None:
        """设置缩放比例"""
        self._scale = scale
        self.update()

    def set_selected(self, selected: bool) -> None:
        """设置选中状态"""
        self._is_selected = selected
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # 颜色
        bg_color = QColor(self._style.font_color)
        bg_color.setAlpha(40)

        border_color = QColor("#6366F1") if self._is_selected else QColor("#475569")

        # 背景
        painter.fillRect(self.rect(), bg_color)

        # 边框
        painter.setPen(QPen(border_color, 2 if self._is_selected else 1))
        painter.drawRoundedRect(0, 2, w - 1, h - 4, 4, 4)

        # 左侧调整手柄
        painter.setPen(QPen(QColor("#6366F1"), 3))
        painter.drawLine(4, 8, 4, h - 8)

        # 右侧调整手柄
        painter.drawLine(w - 4, 8, w - 4, h - 8)

        # 文本
        text = self._block.text
        if len(text) > 20:
            text = text[:20] + "..."

        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        painter.setPen(QPen(QColor(self._style.font_color), 1))
        painter.drawText(8, h // 2 + 4, text)

        # 时间显示
        time_str = f"{self._block.start_time:.1f}s - {self._block.end_time:.1f}s"
        painter.setPen(QPen(QColor("#94A3B8"), 1))
        painter.drawText(w - 80, h // 2 + 4, time_str)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._is_dragging = True
            self._drag_start_x = event.position().x()
            self._original_start = self._block.start_time
            self._original_end = self._block.end_time
            self.block_selected.emit(self._block.id)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._is_dragging:
            delta_x = event.position().x() - self._drag_start_x
            delta_time = delta_x / self._scale

            new_start = self._original_start + delta_time
            new_end = self._original_end + delta_time

            if new_start >= 0 and new_end > new_start:
                self._block.start_time = new_start
                self._block.end_time = new_end
                self.block_changed.emit(self._block.id)
                self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._is_dragging = False


__all__ = ["SubtitleBlockWidget"]
