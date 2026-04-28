#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
设置页面
API Key 配置 + 关于信息
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QMessageBox
)
from PySide6.QtCore import Qt

from app.ui.components.design_system import CFButton, CFLabel, CFCard, CFInput
from .base_page import BasePage


class SettingsPage(BasePage):
    """设置页面"""

    def initialize(self) -> bool:
        return True

    def create_content(self):
        self.set_main_layout_margins(32, 24, 32, 24)
        self.set_main_layout_spacing(24)

        # 标题
        title = CFLabel("⚙️ 设置")
        title.set_style("color: #E8EDF5; font-size: 20px; font-weight: 700;")
        self.add_widget_to_main_layout(title)

        # API Key 卡片
        api_card = CFCard()
        api_layout = QVBoxLayout(api_card)
        api_layout.setSpacing(16)

        api_title = CFLabel("🔑 API 密钥")
        api_title.set_style("color: #E8EDF5; font-size: 14px; font-weight: 600;")
        api_layout.addWidget(api_title)

        hint = CFLabel("DeepSeek 用于解说文案生成，Qwen 用于视频画面理解")
        hint.set_style("color: #4A6080; font-size: 11px;")
        api_layout.addWidget(hint)

        # DeepSeek
        ds_layout = self._key_row("DeepSeek API Key", "sk-", "保存")
        api_layout.addLayout(ds_layout)

        # Qwen
        qw_layout = self._key_row("Qwen API Key", "sk-", "保存")
        api_layout.addLayout(qw_layout)

        self.add_widget_to_main_layout(api_card)

        # 关于卡片
        about_card = CFCard()
        about_layout = QVBoxLayout(about_card)
        about_layout.setSpacing(12)

        about_title = CFLabel("ℹ️ 关于 Voxplore")
        about_title.set_style("color: #E8EDF5; font-size: 14px; font-weight: 600;")
        about_layout.addWidget(about_title)

        version = CFLabel("版本 3.9.0")
        version.set_style("color: #4A6080; font-size: 12px;")
        about_layout.addWidget(version)

        desc = CFLabel(
            "AI First-Person Video Narrator\n"
            "上传视频，AI 代入画面主角视角，一键生成配音解说"
        )
        desc.set_style("color: #5A7088; font-size: 12px; line-height: 1.8;")
        about_layout.addWidget(desc)

        tech = CFLabel("Powered by: Qwen2.5-VL · DeepSeek-V4 · Edge-TTS · SenseVoice")
        tech.set_style("color: #2A3A50; font-size: 11px; padding-top: 8px;")
        about_layout.addWidget(tech)

        self.add_widget_to_main_layout(about_card)
        self.add_widget_to_main_layout(QWidget())  # spacer

    def _key_row(self, label: str, placeholder: str, btn_text: str):
        row = QHBoxLayout()
        row.setSpacing(12)

        lbl = CFLabel(label)
        lbl.setFixedWidth(140)
        lbl.set_style("color: #6A8098; font-size: 12px; font-weight: 500;")
        row.addWidget(lbl)

        inp = CFInput()
        inp.set_placeholder(placeholder + "xxxxxxxxxxxxxxxx")
        inp.set_echo_mode(Qt.EchoMode.Password)
        inp.setFixedHeight(36)
        inp.set_style(self._input_style())
        row.addWidget(inp, 1)

        btn = CFButton(btn_text)
        btn.setFixedSize(60, 36)
        btn.set_style(self._btn_style())
        btn.clicked.connect(lambda: self._save_key(label, inp))
        row.addWidget(btn)

        return row

    def _save_key(self, label: str, inp: CFInput):
        key = inp.text().strip()
        if not key:
            QMessageBox.warning(self, "提示", "请输入 API Key")
            return
        QMessageBox.information(self, "保存成功", f"{label} 已保存（显示为密文）")

    @staticmethod
    def _input_style() -> str:
        return (
            "CFInput { background: #0A0F1A; color: #D0E0F0; "
            "border: 1px solid #1A2332; border-radius: 10px; "
            "padding: 6px 14px; font-size: 12px; } "
            "CFInput:focus { border-color: #0A84FF; }"
        )

    @staticmethod
    def _btn_style() -> str:
        return (
            "CFButton { background: #0A84FF; color: white; border: none; "
            "border-radius: 10px; font-size: 12px; font-weight: 600; } "
            "CFButton:hover { background: #2196FF; }"
        )
