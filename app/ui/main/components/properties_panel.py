#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Voxplore 属性面板
显示和编辑选中片段的属性（时间/转场/字幕/配音）
"""

from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QDoubleSpinBox, QComboBox, QTextEdit, QGroupBox,
    QFormLayout, QScrollArea, QSlider,
    QCheckBox
)
from PySide6.QtCore import Qt, Signal

from app.ui.components.design_system import Colors


class PropertiesPanel(QWidget):
    """属性面板"""

    property_changed = Signal(str, str, object)  # clip_id, property_name, value

    def __init__(self, application=None):
        super().__init__(application)
        self.application = application
        self._current_clip: Optional[Dict[str, Any]] = None

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题
        header = QLabel("⚙️ 属性")
        header.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TextPrimary}; font-size: 13px; font-weight: bold;
                padding: 10px 12px;
                background-color: {Colors.BgElevated};
                border-bottom: 1px solid {Colors.BorderDefault};
            }}
        """)
        layout.addWidget(header)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea {{ background: {Colors.BgBase}; border: none; }}")

        content = QWidget()
        self._form_layout = QVBoxLayout(content)
        self._form_layout.setContentsMargins(12, 8, 12, 8)
        self._form_layout.setSpacing(12)

        # ---- 基本信息 ----
        self._info_group = self._create_group("📋 基本信息")
        info_form = QFormLayout()
        info_form.setSpacing(6)

        self._clip_id_label = QLabel("—")
        self._clip_type_label = QLabel("—")
        info_form.addRow("ID:", self._clip_id_label)
        info_form.addRow("类型:", self._clip_type_label)
        self._info_group.layout().addLayout(info_form)
        self._form_layout.addWidget(self._info_group)

        # ---- 时间 ----
        self._time_group = self._create_group("⏱️ 时间")
        time_form = QFormLayout()
        time_form.setSpacing(6)

        self._start_spin = QDoubleSpinBox()
        self._start_spin.setRange(0, 99999)
        self._start_spin.setDecimals(2)
        self._start_spin.setSuffix(" s")
        self._start_spin.valueChanged.connect(lambda v: self._emit_change("start", v))

        self._end_spin = QDoubleSpinBox()
        self._end_spin.setRange(0, 99999)
        self._end_spin.setDecimals(2)
        self._end_spin.setSuffix(" s")
        self._end_spin.valueChanged.connect(lambda v: self._emit_change("end", v))

        self._duration_label = QLabel("0.00 s")

        time_form.addRow("开始:", self._start_spin)
        time_form.addRow("结束:", self._end_spin)
        time_form.addRow("时长:", self._duration_label)
        self._time_group.layout().addLayout(time_form)
        self._form_layout.addWidget(self._time_group)

        # ---- 转场 ----
        self._transition_group = self._create_group("✨ 转场效果")
        trans_form = QFormLayout()

        self._transition_combo = QComboBox()
        self._transition_combo.addItems(["无", "淡入淡出", "交叉溶解", "擦除", "滑动", "缩放"])
        self._transition_combo.currentTextChanged.connect(lambda v: self._emit_change("transition", v))

        self._trans_duration_spin = QDoubleSpinBox()
        self._trans_duration_spin.setRange(0.1, 5.0)
        self._trans_duration_spin.setValue(0.5)
        self._trans_duration_spin.setSuffix(" s")

        trans_form.addRow("效果:", self._transition_combo)
        trans_form.addRow("时长:", self._trans_duration_spin)
        self._transition_group.layout().addLayout(trans_form)
        self._form_layout.addWidget(self._transition_group)

        # ---- 字幕 ----
        self._subtitle_group = self._create_group("💬 字幕")
        sub_layout = QVBoxLayout()

        self._subtitle_text = QTextEdit()
        self._subtitle_text.setMaximumHeight(80)
        self._subtitle_text.setPlaceholderText("字幕内容...")
        self._subtitle_text.setStyleSheet(f"QTextEdit {{ background: {Colors.BgElevated}; color: {Colors.TextPrimary}; border: 1px solid {Colors.BorderDefault}; border-radius: 4px; padding: 4px; }}")

        sub_style_form = QFormLayout()
        self._font_size_spin = QDoubleSpinBox()
        self._font_size_spin.setRange(10, 72)
        self._font_size_spin.setValue(24)

        self._sub_position = QComboBox()
        self._sub_position.addItems(["底部", "顶部", "居中"])

        sub_style_form.addRow("字号:", self._font_size_spin)
        sub_style_form.addRow("位置:", self._sub_position)

        sub_layout.addWidget(self._subtitle_text)
        sub_layout.addLayout(sub_style_form)
        self._subtitle_group.layout().addLayout(sub_layout)
        self._form_layout.addWidget(self._subtitle_group)

        # ---- 音频 ----
        self._audio_group = self._create_group("🔊 音频")
        audio_form = QFormLayout()

        self._volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._volume_slider.setRange(0, 200)
        self._volume_slider.setValue(100)

        self._mute_check = QCheckBox("静音")

        audio_form.addRow("音量:", self._volume_slider)
        audio_form.addRow("", self._mute_check)
        self._audio_group.layout().addLayout(audio_form)
        self._form_layout.addWidget(self._audio_group)

        self._form_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

        # 初始隐藏
        self._show_empty()

    def _create_group(self, title: str) -> QGroupBox:
        group = QGroupBox(title)
        group.setStyleSheet(f"""
            QGroupBox {{
                color: {Colors.TextSecondary}; font-size: 12px; font-weight: bold;
                border: 1px solid {Colors.BorderDefault}; border-radius: 6px;
                margin-top: 8px; padding-top: 16px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 8px; padding: 0 4px;
            }}
            QLabel {{ color: {Colors.TextMuted}; font-size: 11px; }}
            QDoubleSpinBox, QComboBox, QLineEdit {{
                background: {Colors.BgElevated}; color: {Colors.TextPrimary}; border: 1px solid {Colors.BorderDefault};
                border-radius: 3px; padding: 2px 4px;
            }}
        """)
        group.setLayout(QVBoxLayout())
        return group

    def _show_empty(self):
        """无选中状态"""
        self._info_group.hide()
        self._time_group.hide()
        self._transition_group.hide()
        self._subtitle_group.hide()
        self._audio_group.hide()

    def load_clip(self, clip_data: Dict[str, Any]):
        """加载选中片段的属性"""
        self._current_clip = clip_data
        clip_type = clip_data.get("track_type", "video")

        self._clip_id_label.setText(clip_data.get("id", "—"))
        self._clip_type_label.setText({"video": "视频", "audio": "音频", "subtitle": "字幕"}.get(clip_type, clip_type))

        self._start_spin.blockSignals(True)
        self._end_spin.blockSignals(True)
        self._start_spin.setValue(clip_data.get("start", 0))
        self._end_spin.setValue(clip_data.get("end", 0))
        self._duration_label.setText(f"{clip_data.get('end', 0) - clip_data.get('start', 0):.2f} s")
        self._start_spin.blockSignals(False)
        self._end_spin.blockSignals(False)

        # 显示相关面板
        self._info_group.show()
        self._time_group.show()
        self._transition_group.setVisible(clip_type == "video")
        self._subtitle_group.setVisible(clip_type == "subtitle")
        self._audio_group.setVisible(clip_type in ("video", "audio"))

        if clip_type == "subtitle":
            self._subtitle_text.setPlainText(clip_data.get("text", ""))

    def clear(self):
        self._current_clip = None
        self._show_empty()

    def _emit_change(self, prop: str, value: Any):
        if self._current_clip:
            cid = self._current_clip.get("id", "")
            self.property_changed.emit(cid, prop, value)

    def cleanup(self):
        self.clear()

    def update_theme(self, is_dark: bool = True):
        """更新主题"""
        if is_dark:
            self.setStyleSheet(f"""
                QScrollArea {{
                    background-color: {Colors.BgBase};
                    border: none;
                }}
                QLabel {{
                    color: {Colors.TextPrimary};
                }}
                QLineEdit, QSpinBox, QComboBox {{
                    background-color: {Colors.BgElevated};
                    color: {Colors.TextPrimary};
                    border: 1px solid {Colors.BorderDefault};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QScrollArea {{
                    background-color: {Colors.BgSurface};
                    border: none;
                }}
                QLabel {{
                    color: {Colors.TextPrimary};
                }}
                QLineEdit, QSpinBox, QComboBox {{
                    background-color: {Colors.BgSurface};
                    color: {Colors.TextPrimary};
                    border: 1px solid {Colors.BorderDefault};
                }}
            """)
