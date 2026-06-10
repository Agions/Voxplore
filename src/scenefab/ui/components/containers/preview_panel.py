#!/usr/bin/env python3

"""
视频编辑器 - 预览面板组件
"""

import logging

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QFont
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from scenefab.ui.theme.ds_tokens import _C

logger = logging.getLogger(__name__)


class PreviewPanel(QWidget):
    """视频预览面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._media_player = None
        self._video_widget = None
        self._is_playing = False
        self._setup_ui()

    def _setup_ui(self):
        self.setMinimumSize(400, 300)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 视频显示区域
        video_container = QFrame()
        video_container.setStyleSheet("""
            QFrame {
                background: #0A0A0F;
                border-radius: 12px;
            }
        """)

        video_layout = QVBoxLayout(video_container)
        video_layout.setContentsMargins(0, 0, 0, 0)

        # 视频占位符
        self._placeholder = QLabel("🎬\n\n拖拽视频到此处预览")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setFont(QFont("", 14))
        self._placeholder.setStyleSheet("""
            color: #52525B;
            background: #0A0A0F;
            border-radius: 12px;
        """)
        video_layout.addWidget(self._placeholder)

        layout.addWidget(video_container, 1)

        # 播放控制栏
        controls = self._create_controls()
        layout.addWidget(controls)

    def _create_controls(self) -> QWidget:
        """播放控制栏"""
        widget = QWidget()
        widget.setStyleSheet(f"background: {_C.BG_ELEVATED}; border-radius: 8px;")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)
        layout.addLayout(self._create_progress_bar())
        layout.addLayout(self._create_buttons_bar())
        return widget

    def _create_progress_bar(self) -> QHBoxLayout:
        """进度条行"""
        layout = QHBoxLayout()
        layout.setSpacing(8)

        self._time_label = QLabel("00:00")
        self.time_label.setFont(QFont("", 11))
        self._time_label.setStyleSheet(f"color: {_C.TEXT_MUTED};")
        layout.addWidget(self._time_label)

        self._progress_slider = QSlider(Qt.Orientation.Horizontal)
        self._progress_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 4px;
                background: {_C.BORDER_DEFAULT};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                width: 12px;
                margin: -4px 0;
                background: {_C.INFO};
                border-radius: 6px;
            }}
        """)
        layout.addWidget(self._progress_slider)

        self._duration_label = QLabel("00:00")
        self._duration_label.setFont(QFont("", 11))
        self._duration_label.setStyleSheet(f"color: {_C.TEXT_MUTED};")
        layout.addWidget(self._duration_label)

        return layout

    def _create_buttons_bar(self) -> QHBoxLayout:
        """播放按钮行"""
        layout = QHBoxLayout()

        self._play_btn = QPushButton("▶")
        self._play_btn.setFixedSize(36, 36)
        self._play_btn.setStyleSheet(
            f"QPushButton {{ background: {_C.INFO}; border: none; border-radius: 18px; color: white; font-size: 14px; }}"
            f" QPushButton:hover {{ background: {_C.PRIMARY}; }}"
        )
        layout.addWidget(self._play_btn)

        self._volume_btn = QPushButton("🔊")
        self._volume_btn.setFixedSize(36, 36)
        self._volume_btn.setStyleSheet("QPushButton { background: transparent; border: none; font-size: 14px; }")
        layout.addWidget(self._volume_btn)

        self._volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._volume_slider.setFixedWidth(80)
        self._volume_slider.setValue(80)
        self._volume_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 3px;
                background: {_C.BORDER_DEFAULT};
            }}
            QSlider::handle:horizontal {{
                width: 10px;
                background: {_C.TEXT_MUTED};
                border-radius: 5px;
            }}
        """)
        layout.addWidget(self._volume_slider)
        layout.addStretch()
        fullscreen_btn = QPushButton("⛶")
        fullscreen_btn.setFixedSize(36, 36)
        fullscreen_btn.setStyleSheet("QPushButton { background: transparent; border: none; font-size: 14px; }")
        layout.addWidget(fullscreen_btn)

        return layout

    @property
    def time_label(self):
        return self._time_label

    @property
    def duration_label(self):
        return self._duration_label

    @property
    def play_btn(self):
        return self._play_btn

    @property
    def volume_btn(self):
        return self._volume_btn

    @property
    def progress_slider(self):
        return self._progress_slider

    @property
    def volume_slider(self):
        return self._volume_slider

    def load_video(self, path: str) -> bool:
        """加载视频"""
        if not self._media_player:
            self._init_media_player()

        try:
            self._media_player.setSource(QUrl.fromLocalFile(path))  # type: ignore[union-attr]
            self._placeholder.hide()
            return True
        except Exception as e:
            logger.error(f"加载视频失败: {e}")
            return False

    def _init_media_player(self):
        """初始化媒体播放器"""
        self._media_player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._media_player.setAudioOutput(self._audio_output)

    def play(self):
        if self._media_player:
            self._media_player.play()
            self._is_playing = True

    def pause(self):
        if self._media_player:
            self._media_player.pause()
            self._is_playing = False

    def toggle_playback(self):
        if self._is_playing:
            self.pause()
        else:
            self.play()
