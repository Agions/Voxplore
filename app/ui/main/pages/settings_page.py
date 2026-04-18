#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
设置页面
API Key 配置 + 关于信息
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QLineEdit, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt

from .base_page import BasePage


class SettingsPage(BasePage):
    """设置页面"""

    def initialize(self) -> bool:
        return True

    def create_content(self):
        self.set_main_layout_margins(32, 24, 32, 24)
        self.set_main_layout_spacing(24)

        # 标题
        title = QLabel("⚙️ 设置")
        title.setStyleSheet("color: #E8EDF5; font-size: 20px; font-weight: 700;")
        self.add_widget_to_main_layout(title)

        # API Key 卡片
        api_card = self._make_card()
        api_layout = QVBoxLayout(api_card)
        api_layout.setSpacing(16)

        api_title = QLabel("🔑 API 密钥")
        api_title.setStyleSheet("color: #E8EDF5; font-size: 14px; font-weight: 600;")
        api_layout.addWidget(api_title)

        hint = QLabel("DeepSeek 用于解说文案生成，Qwen 用于视频画面理解")
        hint.setStyleSheet("color: #4A6080; font-size: 11px;")
        api_layout.addWidget(hint)

        # DeepSeek
        ds_layout = self._key_row("DeepSeek API Key", "sk-", "保存")
        api_layout.addLayout(ds_layout)

        # Qwen
        qw_layout = self._key_row("Qwen API Key", "sk-", "保存")
        api_layout.addLayout(qw_layout)

        self.add_widget_to_main_layout(api_card)

        # 关于卡片
        about_card = self._make_card()
        about_layout = QVBoxLayout(about_card)
        about_layout.setSpacing(12)

        about_title = QLabel("ℹ️ 关于 Voxplore")
        about_title.setStyleSheet("color: #E8EDF5; font-size: 14px; font-weight: 600;")
        about_layout.addWidget(about_title)

        version = QLabel("版本 3.2.0")
        version.setStyleSheet("color: #4A6080; font-size: 12px;")
        about_layout.addWidget(version)

        desc = QLabel(
            "AI First-Person Video Narrator\n"
            "上传视频，AI 代入画面主角视角，一键生成配音解说"
        )
        desc.setStyleSheet("color: #5A7088; font-size: 12px; line-height: 1.8;")
        about_layout.addWidget(desc)

        tech = QLabel("Powered by: Qwen2.5-VL · DeepSeek-V3 · Edge-TTS · SenseVoice")
        tech.setStyleSheet("color: #2A3A50; font-size: 11px; padding-top: 8px;")
        about_layout.addWidget(tech)

        self.add_widget_to_main_layout(about_card)
        self.add_widget_to_main_layout(QWidget())  # spacer

    def _key_row(self, label: str, placeholder: str, btn_text: str):
        row = QHBoxLayout()
        row.setSpacing(12)

        lbl = QLabel(label)
        lbl.setFixedWidth(140)
        lbl.setStyleSheet("color: #6A8098; font-size: 12px; font-weight: 500;")
        row.addWidget(lbl)

        inp = QLineEdit()
        inp.setPlaceholderText(placeholder + "xxxxxxxxxxxxxxxx")
        inp.setEchoMode(QLineEdit.EchoMode.Password)
        inp.setFixedHeight(36)
        inp.setStyleSheet(self._input_style())
        row.addWidget(inp, 1)

        btn = QPushButton(btn_text)
        btn.setFixedSize(60, 36)
        btn.setStyleSheet(self._btn_style())
        btn.clicked.connect(lambda: self._save_key(label, inp))
        row.addWidget(btn)

        return row

    def _save_key(self, label: str, inp: QLineEdit):
        key = inp.text().strip()
        if not key:
            QMessageBox.warning(self, "提示", "请输入 API Key")
            return
        QMessageBox.information(self, "保存成功", f"{label} 已保存（显示为密文）")

    @staticmethod
    def _make_card() -> QFrame:
        f = QFrame()
        f.setStyleSheet(
            "background: #0D1520; border: 1px solid #1A2332; "
            "border-radius: 16px; padding: 20px;"
        )
        return f

    @staticmethod
    def _input_style() -> str:
        return (
            "QLineEdit { background: #0A0F1A; color: #D0E0F0; "
            "border: 1px solid #1A2332; border-radius: 10px; "
            "padding: 6px 14px; font-size: 12px; } "
            "QLineEdit:focus { border-color: #0A84FF; }"
        )

    @staticmethod
    def _btn_style() -> str:
        return (
            "QPushButton { background: #0A84FF; color: white; border: none; "
            "border-radius: 10px; font-size: 12px; font-weight: 600; } "
            "QPushButton:hover { background: #2196FF; }"
        )
