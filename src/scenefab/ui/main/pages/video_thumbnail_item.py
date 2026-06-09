#!/usr/bin/env python3
"""视频缩略图列表项组件

从 step_upload.py 提取 VideoThumbnailItem
"""

import os
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

# ── OKLCH Design Tokens ──────────────────────────────────────
_T = {
    "bg_card": "oklch(0.16 0.01 250)",
    "border": "oklch(0.24 0.01 250)",
    "primary": "oklch(0.65 0.20 250)",
    "text_muted": "oklch(0.55 0.01 250)",
}


# ── 视频缩略图列表项 ────────────────────────────────────────
class VideoThumbnailItem(QWidget):
    """单个视频缩略图卡片（用于列表展示）"""

    clicked = Signal(str)
    selection_changed = Signal(str, bool)  # path, selected

    _CHECKED_FILES = set()  # type: ignore[var-annotated]  # 类级别已选中文件集合

    def __init__(self, video_path: str, parent=None):
        super().__init__(parent)
        self._path = video_path
        self._thumb_path = ""
        self._selected = False
        self._setup_ui()

    def _setup_ui(self):
        self.setFixedSize(160, 140)
        self.setStyleSheet(f"""
            QWidget {{
                background: {_T["bg_card"]};
                border: 1px solid {_T["border"]};
                border-radius: 10px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # 复选框行
        cb_layout = QHBoxLayout()
        cb_layout.addStretch()
        self._cb = QCheckBox()
        self._cb.setFixedSize(18, 18)
        self._cb.stateChanged.connect(self._on_check)
        self._cb_layout = QVBoxLayout()
        self._cb_layout.addWidget(self._cb)
        self._cb_layout.addStretch()
        cb_layout.addLayout(self._cb_layout)
        layout.addLayout(cb_layout)

        # 缩略图
        self._thumb_label = QLabel()
        self._thumb_label.setFixedSize(148, 84)
        self._thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumb_label.setStyleSheet("border-radius: 6px; background: #0a0a0a;")
        self._thumb_label.setText("🎬")
        self._thumb_label.setFont(QFont("", 28))
        layout.addWidget(self._thumb_label)

        # 文件名
        self._name_label = QLabel(Path(self._path).name)
        self._name_label.setFont(QFont("", 9))
        self._name_label.setStyleSheet(f"color: {_T['text_muted']};")
        self._name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._name_label.setWordWrap(True)
        self._name_label.setFixedHeight(24)
        layout.addWidget(self._name_label)

    def set_thumbnail(self, thumb_path: str):
        """设置缩略图路径"""
        self._thumb_path = thumb_path
        if thumb_path and os.path.exists(thumb_path):
            pixmap = QPixmap(thumb_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    148,
                    84,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self._thumb_label.setPixmap(scaled)
                self._thumb_label.setText("")

    def _on_check(self, state):
        self._selected = state == Qt.CheckState.Checked.value
        if self._selected:
            VideoThumbnailItem._CHECKED_FILES.add(self._path)
        else:
            VideoThumbnailItem._CHECKED_FILES.discard(self._path)
        self.selection_changed.emit(self._path, self._selected)
        self._update_border()

    def _update_border(self):
        color = _T["primary"] if self._selected else _T["border"]
        self.setStyleSheet(f"""
            QWidget {{
                background: {_T["bg_card"]};
                border: 2px solid {color};
                border-radius: 10px;
            }}
        """)

    @property
    def video_path(self) -> str:
        return self._path

    @classmethod
    def get_checked_files(cls) -> set:
        return cls._CHECKED_FILES.copy()

    @classmethod
    def clear_checked(cls):
        cls._CHECKED_FILES.clear()
