#!/usr/bin/env python3

"""
导出面板
提供完整的视频导出功能界面
"""

import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from scenefab.logger import Logger

from ...export.export_system import ExportPreset
from .export_format_selector import ExportSettingsDialog
from .export_progress import ExportQueueWidget


class ExportPanel(QWidget):


    def build_quick_export_tab(self) -> QWidget:
        """创建快速导出标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 项目信息
        project_group = QGroupBox("项目信息")
        project_layout = QFormLayout(project_group)

        self.project_name_label = QLabel("未选择项目")
        self.project_duration_label = QLabel("00:00:00")
        self.project_resolution_label = QLabel("1920x1080")

        project_layout.addRow("项目名称:", self.project_name_label)
        project_layout.addRow("持续时间:", self.project_duration_label)
        project_layout.addRow("分辨率:", self.project_resolution_label)

        # 导出设置
        export_group = QGroupBox("导出设置")
        export_layout = QFormLayout(export_group)

        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(200)
        self.refresh_presets()

        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("选择输出路径...")
        self.browse_btn = QPushButton("浏览")
        self.browse_btn.clicked.connect(self.browse_output_path)

        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_path_edit, 1)
        output_layout.addWidget(self.browse_btn)

        export_layout.addRow("导出预设:", self.preset_combo)
        export_layout.addRow("输出路径:", output_layout)

        # 快速操作按钮
        quick_actions_group = QGroupBox("快速操作")
        quick_actions_layout = QHBoxLayout(quick_actions_group)

        self.export_youtube_btn = QPushButton("导出 YouTube")
        self.export_tiktok_btn = QPushButton("导出 TikTok")
        self.export_instagram_btn = QPushButton("导出 Instagram")
        self.export_jianying_btn = QPushButton("导出剪映草稿")

        self.export_youtube_btn.clicked.connect(lambda: self.quick_export("youtube_1080p"))
        self.export_tiktok_btn.clicked.connect(lambda: self.quick_export("tiktok_video"))
        self.export_instagram_btn.clicked.connect(lambda: self.quick_export("instagram_reel"))
        self.export_jianying_btn.clicked.connect(lambda: self.quick_export("jianying_draft"))

        quick_actions_layout.addWidget(self.export_youtube_btn)
        quick_actions_layout.addWidget(self.export_tiktok_btn)
        quick_actions_layout.addWidget(self.export_instagram_btn)
        quick_actions_layout.addWidget(self.export_jianying_btn)

        # 导出按钮
        self.export_btn = QPushButton("开始导出")
        self.export_btn.setMinimumHeight(40)
        self.export_btn.clicked.connect(self.start_export)

        # 添加到布局
        layout.addWidget(project_group)
        layout.addWidget(export_group)
        layout.addWidget(quick_actions_group)
        layout.addWidget(self.export_btn)
        layout.addStretch()

        return widget


    def build_batch_export_tab(self) -> QWidget:
        """创建批量导出标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 批量配置
        config_group = QGroupBox("批量配置")
        config_layout = QFormLayout(config_group)

        self.batch_output_dir_edit = QLineEdit()
        self.batch_output_dir_edit.setPlaceholderText("选择输出目录...")
        self.batch_browse_btn = QPushButton("浏览")
        self.batch_browse_btn.clicked.connect(self.browse_batch_output_dir)

        batch_output_layout = QHBoxLayout()
        batch_output_layout.addWidget(self.batch_output_dir_edit, 1)
        batch_output_layout.addWidget(self.batch_browse_btn)

        self.batch_preset_combo = QComboBox()
        self.batch_preset_combo.setMinimumWidth(200)

        config_layout.addRow("输出目录:", batch_output_layout)
        config_layout.addRow("导出预设:", self.batch_preset_combo)

        # 项目列表
        projects_group = QGroupBox("项目列表")
        projects_layout = QVBoxLayout(projects_group)

        self.batch_projects_table = QTableWidget()
        self.batch_projects_table.setColumnCount(4)
        self.batch_projects_table.setHorizontalHeaderLabels([
            "选择", "项目名称", "持续时间", "分辨率"
        ])
        self.batch_projects_table.horizontalHeader().setStretchLastSection(True)

        projects_layout.addWidget(self.batch_projects_table)

        # 批量操作按钮
        batch_actions_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("全选")
        self.select_none_btn = QPushButton("全不选")
        self.batch_export_btn = QPushButton("批量导出")

        self.select_all_btn.clicked.connect(self.select_all_projects)
        self.select_none_btn.clicked.connect(self.select_none_projects)
        self.batch_export_btn.clicked.connect(self.start_batch_export)

        batch_actions_layout.addWidget(self.select_all_btn)
        batch_actions_layout.addWidget(self.select_none_btn)
        batch_actions_layout.addStretch()
        batch_actions_layout.addWidget(self.batch_export_btn)

        # 添加到布局
        layout.addWidget(config_group)
        layout.addWidget(projects_group)
        layout.addLayout(batch_actions_layout)
        layout.addStretch()

        return widget


    def build_queue_tab(self) -> QWidget:
        """创建队列管理标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 队列状态
        self.queue_widget = ExportQueueWidget()
        layout.addWidget(self.queue_widget)

        # 队列设置
        settings_group = QGroupBox("队列设置")
        settings_layout = QFormLayout(settings_group)

        self.max_concurrent_spin = QSpinBox()
        self.max_concurrent_spin.setRange(1, 8)
        self.max_concurrent_spin.setValue(2)

        self.auto_cleanup_check = QCheckBox("自动清理已完成任务")
        self.auto_cleanup_check.setChecked(True)

        settings_layout.addRow("最大并发数:", self.max_concurrent_spin)
        settings_layout.addRow("自动清理:", self.auto_cleanup_check)

        # 应用设置按钮
        self.apply_queue_settings_btn = QPushButton("应用设置")
        self.apply_queue_settings_btn.clicked.connect(self.apply_queue_settings)

        # 添加到布局
        layout.addWidget(settings_group)
        layout.addWidget(self.apply_queue_settings_btn)

        return widget


    def build_presets_tab(self) -> QWidget:
        """创建预设管理标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 预设列表
        presets_group = QGroupBox("导出预设")
        presets_layout = QVBoxLayout(presets_group)

        self.presets_table = QTableWidget()
        self.presets_table.setColumnCount(5)
        self.presets_table.setHorizontalHeaderLabels([
            "预设名称", "格式", "分辨率", "比特率", "操作"
        ])
        self.presets_table.horizontalHeader().setStretchLastSection(True)

        presets_layout.addWidget(self.presets_table)

        # 预设操作按钮
        preset_actions_layout = QHBoxLayout()
        self.add_preset_btn = QPushButton("添加预设")
        self.edit_preset_btn = QPushButton("编辑预设")
        self.delete_preset_btn = QPushButton("删除预设")
        self.refresh_presets_btn = QPushButton("刷新")

        self.add_preset_btn.clicked.connect(self.add_preset)
        self.edit_preset_btn.clicked.connect(self.edit_preset)
        self.delete_preset_btn.clicked.connect(self.delete_preset)
        self.refresh_presets_btn.clicked.connect(self.refresh_presets_table)

        preset_actions_layout.addWidget(self.add_preset_btn)
        preset_actions_layout.addWidget(self.edit_preset_btn)
        preset_actions_layout.addWidget(self.delete_preset_btn)
        preset_actions_layout.addWidget(self.refresh_presets_btn)

        # 添加到布局
        layout.addWidget(presets_group)
        layout.addLayout(preset_actions_layout)
        layout.addStretch()

        return widget


