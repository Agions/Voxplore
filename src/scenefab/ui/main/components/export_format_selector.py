#!/usr/bin/env python3

"""
导出格式选择器
提供导出格式和预设设置对话框
"""

from typing import Any

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from scenefab.logger import Logger
from scenefab.services.export import (
    DEFAULT_AUDIO_BITRATE_KBPS,
    DEFAULT_VIDEO_BITRATE_KBPS,
    ExportPreset,
    normalize_bitrate,
    normalize_resolution,
    parse_bitrate_kbps,
)

FORMAT_OPTIONS = [
    ("MP4 (H.264)", "mp4", "h264"),
    ("MP4 (H.265)", "mp4", "h265"),
    ("MOV (ProRes)", "mov", "prores"),
    ("AVI (无压缩)", "avi", "rawvideo"),
    ("MKV (H.264)", "mkv", "h264"),
    ("WebM (VP9)", "webm", "vp9"),
    ("GIF 动画", "gif", "gif"),
    ("MP3 音频", "mp3", "mp3"),
    ("WAV 音频", "wav", "pcm_s16le"),
    ("剪映草稿", "jianying", "jianying"),
]

RESOLUTION_OPTIONS = [
    ("1080x1920 (竖屏 9:16)", "1080x1920"),
    ("720x1280 (竖屏 9:16)", "720x1280"),
    ("2160x3840 (竖屏 4K)", "2160x3840"),
    ("1920x1080 (横屏 1080p)", "1920x1080"),
    ("1280x720 (横屏 720p)", "1280x720"),
    ("1080x1080 (方形 1:1)", "1080x1080"),
]


class ExportSettingsDialog(QDialog):
    """导出设置对话框"""

    def __init__(self, preset: ExportPreset = None, parent=None):  # type: ignore[assignment]
        super().__init__(parent)
        self.preset = preset
        self.logger = Logger.get_logger(__name__)
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("导出设置")
        self.setMinimumWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)

        layout.addWidget(self._create_basic_info_group())
        layout.addWidget(self._create_format_settings_group())
        layout.addWidget(self._create_quality_settings_group())
        layout.addWidget(self._create_advanced_settings_group())

        self._add_dialog_buttons(layout)

        if self.preset:
            self.load_preset_data()

    def _create_basic_info_group(self) -> QGroupBox:
        """创建基本信息分组"""
        basic_group = QGroupBox("基本信息")
        basic_layout = QFormLayout(basic_group)

        preset_name = getattr(self.preset, "name", "新建预设")
        self.name_input = QLineEdit(preset_name)
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(80)
        self.description_input.setText(getattr(self.preset, "description", ""))

        basic_layout.addRow("预设名称:", self.name_input)
        basic_layout.addRow("描述:", self.description_input)
        return basic_group

    def _create_format_settings_group(self) -> QGroupBox:
        """创建格式设置分组"""
        format_group = QGroupBox("格式设置")
        format_layout = QFormLayout(format_group)

        self.format_combo = QComboBox()
        for label, file_format, codec in FORMAT_OPTIONS:
            self.format_combo.addItem(label, (file_format, codec))

        self.resolution_combo = QComboBox()
        self.resolution_combo.setEditable(True)
        for label, resolution in RESOLUTION_OPTIONS:
            self.resolution_combo.addItem(label, resolution)
        self.resolution_combo.addItem("自定义", "custom")

        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 120)
        self.fps_spin.setValue(30)

        format_layout.addRow("输出格式:", self.format_combo)
        format_layout.addRow("分辨率:", self.resolution_combo)
        format_layout.addRow("帧率 (FPS):", self.fps_spin)
        return format_group

    def _create_quality_settings_group(self) -> QGroupBox:
        """创建质量设置分组"""
        quality_group = QGroupBox("质量设置")
        quality_layout = QFormLayout(quality_group)

        self.bitrate_spin = QSpinBox()
        self.bitrate_spin.setRange(100, 100000)
        self.bitrate_spin.setValue(8000)
        self.bitrate_spin.setSuffix(" kbps")

        self.audio_bitrate_spin = QSpinBox()
        self.audio_bitrate_spin.setRange(32, 512)
        self.audio_bitrate_spin.setValue(128)
        self.audio_bitrate_spin.setSuffix(" kbps")

        quality_layout.addRow("视频比特率:", self.bitrate_spin)
        quality_layout.addRow("音频比特率:", self.audio_bitrate_spin)
        return quality_group

    def _create_advanced_settings_group(self) -> QGroupBox:
        """创建高级设置分组"""
        advanced_group = QGroupBox("高级设置")
        advanced_layout = QFormLayout(advanced_group)

        self.codec_params_edit = QTextEdit()
        self.codec_params_edit.setMaximumHeight(100)
        self.codec_params_edit.setPlaceholderText(
            "额外的编码参数，如: -crf 23 -preset medium"
        )

        advanced_layout.addRow("编码参数:", self.codec_params_edit)
        return advanced_group

    def _add_dialog_buttons(self, layout: QVBoxLayout) -> None:
        """添加对话框按钮"""
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def load_preset_data(self):
        """加载预设数据"""
        preset_name = getattr(self.preset, "name", "新建预设")
        preset_format = self._preset_value(getattr(self.preset, "format", "mp4"))
        preset_codec = self._preset_value(getattr(self.preset, "codec", "h264"))
        preset_resolution = getattr(self.preset, "resolution", None)
        preset_bitrate = getattr(self.preset, "bitrate", DEFAULT_VIDEO_BITRATE_KBPS)
        preset_audio_bitrate = getattr(
            self.preset, "audio_bitrate", DEFAULT_AUDIO_BITRATE_KBPS
        )

        self.name_input.setText(preset_name)
        self.description_input.setText(getattr(self.preset, "description", ""))
        self.bitrate_spin.setValue(
            parse_bitrate_kbps(preset_bitrate, DEFAULT_VIDEO_BITRATE_KBPS)
        )
        self.audio_bitrate_spin.setValue(
            parse_bitrate_kbps(
                preset_audio_bitrate, DEFAULT_AUDIO_BITRATE_KBPS
            )
        )
        self.fps_spin.setValue(int(getattr(self.preset, "fps", 30)))
        self.codec_params_edit.setText(getattr(self.preset, "codec_params", ""))

        format_index = self.format_combo.findData((preset_format, preset_codec))
        if format_index < 0:
            format_index = self._find_format_index(preset_format)
        if format_index >= 0:
            self.format_combo.setCurrentIndex(format_index)

        # 设置分辨率
        resolution_text = normalize_resolution(preset_resolution)
        index = self.resolution_combo.findData(resolution_text)
        if index >= 0:
            self.resolution_combo.setCurrentIndex(index)
        else:
            self.resolution_combo.addItem(f"{resolution_text} (自定义)", resolution_text)
            self.resolution_combo.setCurrentIndex(self.resolution_combo.count() - 1)

    def get_preset_data(self) -> dict[str, Any]:
        """获取预设数据"""
        file_format, codec = self.format_combo.currentData()
        resolution = self.resolution_combo.currentData()
        if resolution == "custom":
            resolution = self.resolution_combo.currentText()
        return {
            "name": self.name_input.text(),
            "description": self.description_input.toPlainText(),
            "format": file_format,
            "codec": codec,
            "resolution": normalize_resolution(resolution),
            "bitrate": normalize_bitrate(
                self.bitrate_spin.value(), DEFAULT_VIDEO_BITRATE_KBPS
            ),
            "audio_bitrate": normalize_bitrate(
                self.audio_bitrate_spin.value(), DEFAULT_AUDIO_BITRATE_KBPS
            ),
            "fps": self.fps_spin.value(),
            "codec_params": self.codec_params_edit.toPlainText(),
        }

    def _find_format_index(self, file_format: str) -> int:
        """Find the first combo item for a file format."""
        for index in range(self.format_combo.count()):
            item_format, _codec = self.format_combo.itemData(index)
            if item_format == file_format:
                return index
        return -1

    @staticmethod
    def _preset_value(value: Any) -> str:
        return str(getattr(value, "value", value))
