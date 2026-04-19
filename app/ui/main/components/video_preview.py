#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Voxplore 视频预览组件
基于 QMediaPlayer 的视频播放 + 帧预览
"""

import os
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QFrame
)
from PySide6.QtCore import Qt, Signal, QUrl

from app.ui.components.design_system import Colors


try:
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PySide6.QtMultimediaWidgets import QVideoWidget
    HAS_MULTIMEDIA = True
except ImportError:
    HAS_MULTIMEDIA = False


class VideoPreview(QWidget):
    """视频预览播放器"""

    playback_position_changed = Signal(int)  # ms
    playback_state_changed = Signal(bool)     # is_playing

    def __init__(self, application=None):
        super().__init__(application)
        self.application = application
        self.current_video: Optional[str] = None
        self._is_playing = False
        self._duration_ms = 0

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 视频显示区
        if HAS_MULTIMEDIA:
            self._player = QMediaPlayer()
            self._audio = QAudioOutput()
            self._player.setAudioOutput(self._audio)
            self._video_widget = QVideoWidget()
            self._video_widget.setMinimumHeight(200)
            self._player.setVideoOutput(self._video_widget)
            self._player.positionChanged.connect(self._on_position_changed)
            self._player.durationChanged.connect(self._on_duration_changed)
            self._player.playbackStateChanged.connect(self._on_state_changed)
            layout.addWidget(self._video_widget, 1)
        else:
            self._player = None
            placeholder = QLabel("🎬 视频预览\n(需要 PyQt6-Multimedia)")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet(f"""
                QLabel {{
                    color: {Colors.TextMuted}; font-size: 16px;
                    background-color: {Colors.BgSurface};
                    border: 2px dashed {Colors.BorderDefault};
                    border-radius: 8px;
                    padding: 40px;
                }}
            """)
            placeholder.setMinimumHeight(200)
            layout.addWidget(placeholder, 1)

        # 控制栏
        controls = QFrame()
        controls.setStyleSheet(f"background-color: {Colors.BgOverlay}; border-top: 1px solid {Colors.BorderDefault};")
        ctrl_layout = QVBoxLayout(controls)
        ctrl_layout.setContentsMargins(8, 4, 8, 4)
        ctrl_layout.setSpacing(4)

        # 进度条
        self._progress = QSlider(Qt.Orientation.Horizontal)
        self._progress.setRange(0, 1000)
        self._progress.setStyleSheet(f"""
            QSlider::groove:horizontal {{ height: 4px; background: {Colors.BorderDefault}; border-radius: 2px; }}
            QSlider::handle:horizontal {{ width: 12px; height: 12px; margin: -4px 0; background: {Colors.Primary}; border-radius: 6px; }}
            QSlider::sub-page:horizontal {{ background: {Colors.Primary}; border-radius: 2px; }}
        """)
        self._progress.sliderMoved.connect(self._on_seek)
        ctrl_layout.addWidget(self._progress)

        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._play_btn = QPushButton("▶")
        self._play_btn.setFixedSize(32, 28)
        self._play_btn.setStyleSheet(f"QPushButton {{ background: {Colors.Primary}; color: white; border: none; border-radius: 4px; font-size: 12px; }}")
        self._play_btn.clicked.connect(self.toggle_play)

        self._stop_btn = QPushButton("⏹")
        self._stop_btn.setFixedSize(32, 28)
        self._stop_btn.setStyleSheet(f"QPushButton {{ background: {Colors.BorderStrong}; color: white; border: none; border-radius: 4px; font-size: 12px; }}")
        self._stop_btn.clicked.connect(self.stop)

        self._time_label = QLabel("00:00 / 00:00")
        self._time_label.setStyleSheet(f"color: {Colors.TextSecondary}; font-size: 11px;")

        self._volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._volume_slider.setRange(0, 100)
        self._volume_slider.setValue(80)
        self._volume_slider.setFixedWidth(80)
        self._volume_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{ height: 3px; background: {Colors.BorderDefault}; border-radius: 1px; }}
            QSlider::handle:horizontal {{ width: 10px; height: 10px; margin: -3px 0; background: {Colors.TextMuted}; border-radius: 5px; }}
        """)
        self._volume_slider.valueChanged.connect(self._on_volume)
        vol_label = QLabel("🔊")
        vol_label.setStyleSheet(f"color: {Colors.TextSecondary}; font-size: 11px;")

        btn_row.addWidget(self._play_btn)
        btn_row.addWidget(self._stop_btn)
        btn_row.addWidget(self._time_label)
        btn_row.addStretch()
        btn_row.addWidget(vol_label)
        btn_row.addWidget(self._volume_slider)

        ctrl_layout.addLayout(btn_row)
        layout.addWidget(controls)

    def load_video(self, video_path: str):
        """加载视频"""
        if not os.path.exists(video_path):
            return
        self.current_video = video_path
        if self._player and HAS_MULTIMEDIA:
            self._player.setSource(QUrl.fromLocalFile(video_path))
            self._audio.setVolume(self._volume_slider.value() / 100.0)

    def toggle_play(self):
        if not self._player or not HAS_MULTIMEDIA:
            return
        if self._is_playing:
            self._player.pause()
        else:
            self._player.play()

    def stop(self):
        if self._player and HAS_MULTIMEDIA:
            self._player.stop()
            self._progress.setValue(0)
            self._time_label.setText("00:00 / " + self._format_time(self._duration_ms))

    def seek(self, position_ms: int):
        if self._player and HAS_MULTIMEDIA:
            self._player.setPosition(position_ms)

    def _on_position_changed(self, pos_ms: int):
        if self._duration_ms > 0:
            self._progress.blockSignals(True)
            self._progress.setValue(int(pos_ms / self._duration_ms * 1000))
            self._progress.blockSignals(False)
        self._time_label.setText(f"{self._format_time(pos_ms)} / {self._format_time(self._duration_ms)}")
        self.playback_position_changed.emit(pos_ms)

    def _on_duration_changed(self, duration_ms: int):
        self._duration_ms = duration_ms

    def _on_state_changed(self, state):
        if HAS_MULTIMEDIA:
            self._is_playing = state == QMediaPlayer.PlaybackState.PlayingState
        self._play_btn.setText("⏸" if self._is_playing else "▶")
        self.playback_state_changed.emit(self._is_playing)

    def _on_seek(self, value: int):
        if self._player and self._duration_ms > 0 and HAS_MULTIMEDIA:
            self._player.setPosition(int(value / 1000 * self._duration_ms))

    def _on_volume(self, value: int):
        if self._player and HAS_MULTIMEDIA:
            self._audio.setVolume(value / 100.0)

    @staticmethod
    def _format_time(ms: int) -> str:
        s = ms // 1000
        m, s = divmod(s, 60)
        return f"{m:02d}:{s:02d}"

    def cleanup(self):
        if self._player and HAS_MULTIMEDIA:
            self._player.stop()
            self._player.setSource(QUrl())

    def update_theme(self, is_dark: bool = True):
        """更新主题"""
        if is_dark:
            self.setStyleSheet(f"""
                QWidget {{
                    background-color: {Colors.BgBase};
                }}
                QSlider::groove:horizontal {{
                    background: {Colors.BgElevated};
                    height: 4px;
                }}
                QSlider::handle:horizontal {{
                    background: {Colors.Primary};
                    width: 14px;
                    margin: -5px 0;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QWidget {{
                    background-color: {Colors.BgSurface};
                }}
                QSlider::groove:horizontal {{
                    background: {Colors.BorderDefault};
                    height: 4px;
                }}
                QSlider::handle:horizontal {{
                    background: {Colors.Primary};
                    width: 14px;
                    margin: -5px 0;
                }}
            """)
