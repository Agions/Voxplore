#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""视频预览播放器组件

从 step_upload.py 提取 VideoPreviewWidget
"""

import os
from pathlib import Path

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtGui import QFont
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtCore import Qt, QUrl


# ── OKLCH Design Tokens ──────────────────────────────────────
_T = {
    "border":      "oklch(0.24 0.01 250)",
    "text_muted":  "oklch(0.55 0.01 250)",
}


# ── 视频预览播放器（小窗）────────────────────────────────────
class VideoPreviewWidget(QFrame):
    """小尺寸视频预览（用于选择文件后预览）"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._player = QMediaPlayer()
        self._audio = QAudioOutput()
        self._player.setAudioOutput(self._audio)
        self._setup_ui()

    def _setup_ui(self):
        self.setFixedSize(320, 180)
        self.setStyleSheet(f"""
            QFrame {{
                background: #000;
                border-radius: 12px;
                border: 1px solid {_T['border']};
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._video_widget = QVideoWidget()
        self._video_widget.setMinimumSize(320, 180)
        self._player.setVideoOutput(self._video_widget)
        layout.addWidget(self._video_widget)

        # 底部信息栏
        self._info_label = QLabel("未选择视频")
        self._info_label.setFont(QFont("", 10))
        self._info_label.setStyleSheet(f"""
            color: {_T['text_muted']};
            background: rgba(0,0,0,0.7);
            padding: 4px 8px;
        """)
        self._info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._info_label.setFixedHeight(24)

    def load(self, path: str):
        """加载视频预览"""
        if os.path.exists(path):
            self._player.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
            self._info_label.setText(Path(path).name)
            self._player.play()

    def stop(self):
        self._player.stop()
