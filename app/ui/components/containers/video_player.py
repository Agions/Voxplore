#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
视频预览播放器组件
支持播放控制和帧提取
"""

import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton, QFrame
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget


class VideoPlayer(QWidget):
    """视频播放器组件"""

    # 信号
    position_changed = Signal(float)  # 当前位置(秒)
    duration_changed = Signal(float)  # 总时长(秒)
    state_changed = Signal(str)       # 播放状态
    frame_changed = Signal(int)       # 当前帧

    def __init__(self, parent=None):
        super().__init__(parent)
        self._player = QMediaPlayer()
        self._audio = QAudioOutput()
        self._player.setAudioOutput(self._audio)
        self._video_widget = QVideoWidget()

        self._is_playing = False
        self._duration = 0
        self._current_frame = 0
        self._fps = 30.0

        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 视频显示区域
        self._video_widget.setMinimumSize(640, 360)
        self._player.setVideoOutput(self._video_widget)
        layout.addWidget(self._video_widget)

        # 控制栏
        controls = QFrame()
        controls.setObjectName("player_controls")
        controls_layout = QVBoxLayout(controls)

        # 进度条
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 1000)
        self._slider.sliderMoved.connect(self._on_seek)
        controls_layout.addWidget(self._slider)

        # 按钮栏
        btn_layout = QHBoxLayout()

        # 播放/暂停
        self._btn_play = QPushButton("▶")
        self._btn_play.clicked.connect(self.toggle_play)
        self._btn_play.setFixedSize(40, 40)
        btn_layout.addWidget(self._btn_play)

        # 停止
        self._btn_stop = QPushButton("⏹")
        self._btn_stop.clicked.connect(self.stop)
        self._btn_stop.setFixedSize(40, 40)
        btn_layout.addWidget(self._btn_stop)

        # 时间显示
        self._label_time = QLabel("00:00 / 00:00")
        self._label_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_layout.addWidget(self._label_time)

        # 音量
        self._btn_mute = QPushButton("🔊")
        self._btn_mute.clicked.connect(self.toggle_mute)
        self._btn_mute.setFixedSize(40, 40)
        btn_layout.addWidget(self._btn_mute)

        # 音量滑块
        self._slider_volume = QSlider(Qt.Orientation.Horizontal)
        self._slider_volume.setRange(0, 100)
        self._slider_volume.setValue(80)
        self._slider_volume.setFixedWidth(80)
        self._slider_volume.valueChanged.connect(self._on_volume_changed)
        btn_layout.addWidget(self._slider_volume)

        btn_layout.addStretch()

        # 全屏
        self._btn_fullscreen = QPushButton("⛶")
        self._btn_fullscreen.clicked.connect(self.toggle_fullscreen)
        self._btn_fullscreen.setFixedSize(40, 40)
        btn_layout.addWidget(self._btn_fullscreen)

        controls_layout.addLayout(btn_layout)
        layout.addWidget(controls)

    def _connect_signals(self):
        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.playbackStateChanged.connect(self._on_state_changed)

    # ===== 公共方法 =====

    def load(self, path: str) -> bool:
        """加载视频"""
        if not os.path.exists(path):
            return False

        url = QUrl.fromLocalFile(os.path.abspath(path))
        self._player.setSource(url)
        return True

    def play(self):
        """播放"""
        self._player.play()
        self._is_playing = True
        self._btn_play.setText("⏸")

    def pause(self):
        """暂停"""
        self._player.pause()
        self._is_playing = False
        self._btn_play.setText("▶")

    def stop(self):
        """停止"""
        self._player.stop()
        self._is_playing = False
        self._btn_play.setText("▶")

    def toggle_play(self):
        """切换播放/暂停"""
        if self._is_playing:
            self.pause()
        else:
            self.play()

    def seek(self, position: float):
        """跳转到指定位置(秒)"""
        self._player.setPosition(int(position * 1000))

    def _on_seek(self, value: int):
        """进度条拖动"""
        if self._duration > 0:
            position = (value / 1000) * self._duration
            self.seek(position)

    def set_fps(self, fps: float):
        """设置帧率"""
        self._fps = fps

    def toggle_mute(self):
        """切换静音"""
        if self._audio.isMuted():
            self._audio.setMuted(False)
            self._btn_mute.setText("🔊")
        else:
            self._audio.setMuted(True)
            self._btn_mute.setText("🔇")

    def toggle_fullscreen(self):
        """切换全屏"""
        if self.isFullScreen():
            self.showNormal()
            self._btn_fullscreen.setText("⛶")
        else:
            self.showFullScreen()
            self._btn_fullscreen.setText("✕")

    def keyPressEvent(self, event):
        """键盘事件 - ESC 退出全屏"""
        if event.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self.showNormal()
            self._btn_fullscreen.setText("⛶")
        super().keyPressEvent(event)

    # ===== 信号处理 =====

    def _on_position_changed(self, position: int):
        """位置变化"""
        if self._duration > 0:
            current = position / 1000
            self._current_frame = int(current * self._fps)
            self.position_changed.emit(current)
            self.frame_changed.emit(self._current_frame)

            # 更新滑块
            ratio = position / (self._duration * 1000)
            self._slider.setValue(int(ratio * 1000))

            # 更新时间显示
            self._update_time_display(current)

    def _on_duration_changed(self, duration: int):
        """时长变化"""
        self._duration = duration / 1000
        self.duration_changed.emit(self._duration)

    def _on_state_changed(self, state):
        """状态变化"""
        state_map = {
            QMediaPlayer.PlaybackState.StoppedState: "stopped",
            QMediaPlayer.PlaybackState.PlayingState: "playing",
            QMediaPlayer.PlaybackState.PausedState: "paused",
        }
        self.state_changed.emit(state_map.get(state, "unknown"))

    def _on_volume_changed(self, value: int):
        """音量变化"""
        self._audio.setVolume(value / 100)

    def _update_time_display(self, current: float):
        """更新时间显示"""
        current_str = self._format_time(current)
        total_str = self._format_time(self._duration)
        self._label_time.setText(f"{current_str} / {total_str}")

    def _format_time(self, seconds: float) -> str:
        """格式化时间"""
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m:02d}:{s:02d}"

    # ===== 属性 =====

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @property
    def duration(self) -> float:
        return self._duration

    @property
    def position(self) -> float:
        return self._player.position() / 1000

    @property
    def current_frame(self) -> int:
        return self._current_frame


class ThumbnailGenerator:
    """视频缩略图生成器"""

    @staticmethod
    def generate_thumbnails(
        video_path: str,
        output_dir: str,
        count: int = 10,
    ) -> list:
        """生成视频缩略图"""
        import subprocess
        import os

        output_dir = os.path.join(output_dir, "thumbnails")
        os.makedirs(output_dir, exist_ok=True)

        # 获取时长
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration = float(result.stdout.strip() or 0)

        # 生成缩略图
        interval = duration / (count + 1)
        thumbnails = []

        for i in range(count):
            timestamp = interval * (i + 1)
            output_path = os.path.join(output_dir, f"thumb_{i:03d}.jpg")

            cmd = [
                "ffmpeg",
                "-y",
                "-ss", str(timestamp),
                "-i", video_path,
                "-vframes", "1",
                "-q:v", "2",
                output_path,
            ]

            subprocess.run(cmd, capture_output=True)
            thumbnails.append(output_path)

        return thumbnails


__all__ = ["VideoPlayer", "ThumbnailGenerator"]
