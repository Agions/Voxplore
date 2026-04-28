#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
视频编辑器 - 预览面板组件
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSlider, QPushButton, QFrame
)

import logging
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QFont
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput


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
        widget.setStyleSheet("background: #1A1A24; border-radius: 8px;")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # 进度条
        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(8)

        self._time_label = QLabel("00:00")
        self.time_label.setFont(QFont("", 11))
        self._time_label.setStyleSheet("color: #A1A1AA;")
        progress_layout.addWidget(self._time_label)

        self._progress_slider = QSlider(Qt.Orientation.Horizontal)
        self._progress_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: #2A2A38;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 12px;
                margin: -4px 0;
                background: #6366F1;
                border-radius: 6px;
            }
        """)
        progress_layout.addWidget(self._progress_slider)

        self._duration_label = QLabel("00:00")
        self._duration_label.setFont(QFont("", 11))
        self._duration_label.setStyleSheet("color: #A1A1AA;")
        progress_layout.addWidget(self._duration_label)

        layout.addLayout(progress_layout)

        # 播放按钮
        buttons_layout = QHBoxLayout()

        # 播放/暂停
        self._play_btn = QPushButton("▶")
        self._play_btn.setFixedSize(36, 36)
        self._play_btn.setStyleSheet("""
            QPushButton {
                background: #6366F1;
                border: none;
                border-radius: 18px;
                color: white;
                font-size: 14px;
            }
            QPushButton:hover { background: #818CF8; }
        """)
        buttons_layout.addWidget(self._play_btn)

        # 音量
        self._volume_btn = QPushButton("🔊")
        self._volume_btn.setFixedSize(36, 36)
        self._volume_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                font-size: 14px;
            }
        """)
        buttons_layout.addWidget(self._volume_btn)

        # 音量滑块
        self._volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._volume_slider.setFixedWidth(80)
        self._volume_slider.setValue(80)
        self._volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 3px;
                background: #2A2A38;
            }
            QSlider::handle:horizontal {
                width: 10px;
                background: #A1A1AA;
                border-radius: 5px;
            }
        """)
        buttons_layout.addWidget(self._volume_slider)

        buttons_layout.addStretch()

        # 全屏
        fullscreen_btn = QPushButton("⛶")
        fullscreen_btn.setFixedSize(36, 36)
        fullscreen_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                font-size: 14px;
            }
        """)
        buttons_layout.addWidget(fullscreen_btn)

        layout.addLayout(buttons_layout)

        return widget

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
            self._media_player.setSource(QUrl.fromLocalFile(path))
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
