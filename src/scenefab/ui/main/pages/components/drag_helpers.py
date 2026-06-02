#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
视频拖拽辅助组件
从 step_group.py 提取的拖拽相关类
"""

import json
import os
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDrag, QFont, QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout

# ── Design Tokens ─────────────────────────────────────────
_T = {
    "bg_card":    "oklch(0.16 0.01 250)",
    "bg_input":   "oklch(0.13 0.01 250)",
    "border":     "oklch(0.24 0.01 250)",
    "border_h":   "oklch(0.30 0.02 250)",
    "primary":    "oklch(0.65 0.20 250)",
    "text":       "oklch(0.93 0.01 250)",
    "text_muted": "oklch(0.55 0.01 250)",
    "error":      "oklch(0.63 0.24 25)",
}

MIME_TYPE = "application/x-scenefab-video"


class _VideoMimeData(QFrame):
    """自定义拖拽数据（用于跨分组拖拽）"""
    def __init__(self, video_path: str, group_id, parent=None):
        super().__init__(parent)
        self._data = json.dumps({
            "path": video_path,
            "group_id": str(group_id)
        }).encode("utf-8")

    def data(self, mime_type: str) -> bytes:
        if mime_type == MIME_TYPE:
            return self._data
        return b""


class _GroupThumbItem(QFrame):
    """分组内的视频缩略图项"""
    remove_requested = Signal(str)
    drag_started = Signal(str)

    def __init__(self, video_path: str, thumb_path: str = "", parent=None):
        super().__init__(parent)
        self._path = video_path
        self._thumb = thumb_path
        self.video_path = video_path
        self._setup_ui()
        self.setAcceptDrops(True)
        self.setFixedSize(100, 80)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def _setup_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background: {_T['bg_input']};
                border: 1px solid {_T['border']};
                border-radius: 8px;
            }}
            QFrame:hover {{
                border-color: {_T['primary']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # 缩略图
        self._thumb_label = QLabel()
        self._thumb_label.setFixedSize(92, 52)
        self._thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumb_label.setStyleSheet("border-radius: 4px; background: #000;")
        self._thumb_label.setText("🎬")
        self._thumb_label.setFont(QFont("", 20))

        if self._thumb and os.path.exists(self._thumb):
            pixmap = QPixmap(self._thumb)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    92, 52,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self._thumb_label.setPixmap(scaled)
                self._thumb_label.setText("")

        layout.addWidget(self._thumb_label)

        # 文件名
        name = Path(self._path).name
        if len(name) > 12:
            name = name[:10] + "…"
        self._name_label = QLabel(name)
        self._name_label.setFont(QFont("", 8))
        self._name_label.setStyleSheet(f"color: {_T['text_muted']};")
        self._name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._name_label)

        # 移除按钮
        self._remove_btn = QPushButton("✕")
        self._remove_btn.setFont(QFont("", 8))
        self._remove_btn.setFixedSize(16, 16)
        self._remove_btn.setStyleSheet(f"""
            QPushButton {{
                background: {_T['error']};
                color: white;
                border-radius: 8px;
                padding: 0px;
            }}
        """)
        self._remove_btn.clicked.connect(
            lambda: self.remove_requested.emit(self._path)
        )
        self._remove_btn.setVisible(False)
        layout.addWidget(self._remove_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self._name_label.mousePressEvent = self._on_mouse_press

    def _on_mouse_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_started.emit(self._path)

    def enterEvent(self, event):
        self._remove_btn.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._remove_btn.setVisible(False)
        super().leaveEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.drag_started.emit(self._path)
            drag = QDrag(self)
            mime = _VideoMimeData(self._path, None)
            drag.setMimeData(mime)
            drag.exec(Qt.DropAction.MoveAction)


__all__ = ["_GroupThumbItem", "_VideoMimeData", "MIME_TYPE"]
