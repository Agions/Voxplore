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
from scenefab.services.export import ExportPreset


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

        self.name_input = QLineEdit(self.preset.name if self.preset else "新建预设")
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(80)
        self.description_input.setText(self.preset.description if self.preset else "")

        basic_layout.addRow("预设名称:", self.name_input)
        basic_layout.addRow("描述:", self.description_input)
        return basic_group

    def _create_format_settings_group(self) -> QGroupBox:
        """创建格式设置分组"""
        format_group = QGroupBox("格式设置")
        format_layout = QFormLayout(format_group)

        self.format_combo = QComboBox()
        self.format_combo.addItems(
            [
                "MP4 (H.264)",
                "MP4 (H.265)",
                "MOV (ProRes)",
                "AVI (无压缩)",
                "MKV (H.264)",
                "WebM (VP9)",
                "GIF动画",
                "MP3音频",
                "WAV音频",
                "剪映草稿",
            ]
        )

        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(
            [
                "3840x2160 (4K)",
                "2560x1440 (2K)",
                "1920x1080 (1080p)",
                "1280x720 (720p)",
                "854x480 (480p)",
                "自定义",
            ]
        )

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
        self.name_input.setText(self.preset.name)
        self.description_input.setText(self.preset.description)
        self.bitrate_spin.setValue(self.preset.bitrate)  # type: ignore[arg-type]
        self.audio_bitrate_spin.setValue(self.preset.audio_bitrate)  # type: ignore[arg-type]
        self.fps_spin.setValue(int(self.preset.fps))

        # 设置分辨率
        resolution_text = f"{self.preset.resolution[0]}x{self.preset.resolution[1]}"
        index = self.resolution_combo.findText(resolution_text)
        if index >= 0:
            self.resolution_combo.setCurrentIndex(index)
        else:
            self.resolution_combo.setCurrentText("自定义")

    def get_preset_data(self) -> dict[str, Any]:
        """获取预设数据"""
        return {
            "name": self.name_input.text(),
            "description": self.description_input.toPlainText(),
            "format": self.format_combo.currentText(),
            "resolution": self.resolution_combo.currentText(),
            "bitrate": self.bitrate_spin.value(),
            "audio_bitrate": self.audio_bitrate_spin.value(),
            "fps": self.fps_spin.value(),
            "codec_params": self.codec_params_edit.toPlainText(),
        }
