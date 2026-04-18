#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
项目设置对话框
"""

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QTabWidget, QLineEdit,
    QComboBox, QSpinBox, QCheckBox, QSlider, QLabel,
    QScrollArea, QGroupBox
)
from PySide6.QtCore import Qt

from app.ui.components import (
    MacPrimaryButton, MacSecondaryButton, MacIconButton,
    MacTitleLabel, MacLabel, MacCard,
)
from app.core.project_manager import Project
from app.core.project_settings_manager import ProjectSettingsManager


class ProjectSettingsDialog(QDialog):
    """项目设置对话框 - macOS 风格"""

    def __init__(self, project: Project, settings_manager: ProjectSettingsManager, parent=None):
        super().__init__(parent)
        self.project = project
        self.settings_manager = settings_manager
        self.setProperty("class", "modal-container")
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        """设置UI - 使用标准化组件"""
        self.setWindowTitle("项目设置")
        self.setModal(True)
        self.setFixedSize(840, 640)

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 模态头部
        header = QWidget()
        header.setProperty("class", "modal-header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 16)

        title = MacTitleLabel("⚙️ 项目设置")
        header_layout.addWidget(title)
        header_layout.addStretch()

        close_btn = MacIconButton("✖️", 28)
        close_btn.setProperty("class", "modal-close")
        close_btn.clicked.connect(self.reject)
        header_layout.addWidget(close_btn)

        main_layout.addWidget(header)

        # 模态主体
        content = QWidget()
        content.setProperty("class", "modal-body")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # 设置标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setProperty("class", "settings-tabs")

        # 视频设置
        video_tab = self._create_video_tab()
        self.tab_widget.addTab(video_tab, "🎬 视频")

        # 音频设置
        audio_tab = self._create_audio_tab()
        self.tab_widget.addTab(audio_tab, "🔊 音频")

        # AI 设置
        ai_tab = self._create_ai_tab()
        self.tab_widget.addTab(ai_tab, "🤖 AI")

        # 导出设置
        export_tab = self._create_export_tab()
        self.tab_widget.addTab(export_tab, "📤 导出")

        content_layout.addWidget(self.tab_widget)
        main_layout.addWidget(content)

        # 模态底部
        footer = QWidget()
        footer.setProperty("class", "modal-footer")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(20, 12, 20, 12)

        footer_layout.addStretch()

        cancel_btn = MacSecondaryButton("取消")
        cancel_btn.clicked.connect(self.reject)
        footer_layout.addWidget(cancel_btn)

        save_btn = MacPrimaryButton("💾 保存")
        save_btn.clicked.connect(self._on_save)
        footer_layout.addWidget(save_btn)

        main_layout.addWidget(footer)

    def _create_video_tab(self) -> QWidget:
        """创建视频设置标签页"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setProperty("class", "settings-scroll")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(16)

        # 分辨率
        resolution_group = QGroupBox("📐 分辨率")
        resolution_layout = QVBoxLayout(resolution_group)

        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems([
            "3840x2160 (4K)",
            "2560x1440 (2K)",
            "1920x1080 (1080p)",
            "1280x720 (720p)",
            "854x480 (480p)"
        ])
        resolution_layout.addWidget(self.resolution_combo)

        layout.addWidget(resolution_group)

        # 帧率
        fps_group = QGroupBox("⏱️ 帧率")
        fps_layout = QVBoxLayout(fps_group)

        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["24", "25", "30", "50", "60"])
        fps_layout.addWidget(self.fps_combo)

        layout.addWidget(fps_group)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    def _create_audio_tab(self) -> QWidget:
        """创建音频设置标签页"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(16)

        # 采样率
        sample_group = QGroupBox("🎵 采样率")
        sample_layout = QVBoxLayout(sample_group)

        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItems(["44100", "48000", "96000"])
        sample_layout.addWidget(self.sample_rate_combo)

        layout.addWidget(sample_group)

        # 声道
        channel_group = QGroupBox("🔊 声道")
        channel_layout = QVBoxLayout(channel_group)

        self.channel_combo = QComboBox()
        self.channel_combo.addItems(["立体声", "单声道"])
        channel_layout.addWidget(self.channel_combo)

        layout.addWidget(channel_group)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    def _create_ai_tab(self) -> QWidget:
        """创建AI设置标签页"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(16)

        # AI 提供商
        provider_group = QGroupBox("🤖 AI 提供商")
        provider_layout = QVBoxLayout(provider_group)

        self.ai_provider_combo = QComboBox()
        self.ai_provider_combo.addItems(["DeepSeek-V3", "通义千问", "Kimi", "智谱 GLM-5"])
        provider_layout.addWidget(self.ai_provider_combo)

        layout.addWidget(provider_group)

        # 自动保存
        auto_group = QGroupBox("💾 自动保存")
        auto_layout = QVBoxLayout(auto_group)

        self.auto_save_checkbox = QCheckBox("启用自动保存")
        self.auto_save_checkbox.setChecked(True)
        auto_layout.addWidget(self.auto_save_checkbox)

        layout.addWidget(auto_group)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    def _create_export_tab(self) -> QWidget:
        """创建导出设置标签页"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(16)

        # 默认格式
        format_group = QGroupBox("📦 默认格式")
        format_layout = QVBoxLayout(format_group)

        self.export_format_combo = QComboBox()
        self.export_format_combo.addItems(["MP4", "MOV", "WebM", "MKV"])
        format_layout.addWidget(self.export_format_combo)

        layout.addWidget(format_group)

        # 质量预设
        quality_group = QGroupBox("✨ 质量预设")
        quality_layout = QVBoxLayout(quality_group)

        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["高质量", "中等质量", "低质量"])
        quality_layout.addWidget(self.quality_combo)

        layout.addWidget(quality_group)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    def _load_settings(self):
        """加载设置"""
        if not self.project:
            return

        settings = self.project.settings

        # 视频设置
        resolution_map = {
            "3840x2160": 0, "2560x1440": 1, "1920x1080": 2,
            "1280x720": 3, "854x480": 4
        }
        if resolution_map.get(settings.resolution):
            self.resolution_combo.setCurrentIndex(resolution_map.get(settings.resolution, 2))

        # 音频设置
        sample_map = {"44100": 0, "48000": 1, "96000": 2}
        if sample_map.get(str(settings.sample_rate)):
            self.sample_rate_combo.setCurrentIndex(sample_map.get(str(settings.sample_rate), 0))

    def _on_save(self):
        """保存设置"""
        self.accept()

    def get_settings(self) -> dict:
        """获取设置"""
        return {
            "resolution": self.resolution_combo.currentText().split(" ")[0],
            "fps": int(self.fps_combo.currentText()),
            "sample_rate": int(self.sample_rate_combo.currentText()),
        }


__all__ = ["ProjectSettingsDialog"]
