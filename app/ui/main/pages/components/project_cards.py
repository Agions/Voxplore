#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
项目卡片组件
包含 ProjectCard 和 TemplateCard
"""

import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap

from app.ui.components import MacCard, MacIconButton, MacLabel, MacBadge


class ProjectCard(MacCard):
    """项目卡片组件 - 使用标准化 macOS 组件"""

    clicked = Signal(str)  # 项目点击信号
    edit_clicked = Signal(str)  # 编辑点击信号
    delete_clicked = Signal(str)  # 删除点击信号
    export_clicked = Signal(str)  # 导出点击信号

    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self.setProperty("class", "card project-card")
        self.set_interactive(True)  # 设置为可交互卡片
        self.setFixedSize(300, 200)

        self._setup_ui()
        self._update_display()

    def _setup_ui(self):
        """设置UI - 使用 QSS 类名，无内联样式"""
        layout = self.layout()

        # 项目名称 (大标题)
        self.name_label = MacLabel("", "card-title")
        self.name_label.setWordWrap(True)
        layout.addWidget(self.name_label)

        # 项目描述 (副标题)
        self.desc_label = MacLabel("", "card-subtitle")
        self.desc_label.setWordWrap(True)
        layout.addWidget(self.desc_label)

        # 项目信息行
        info_row = QWidget()
        info_row.setProperty("class", "stat-row")
        info_layout = QHBoxLayout(info_row)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(8)

        # 类型徽章
        self.type_badge = MacBadge("", "neutral")
        info_layout.addWidget(self.type_badge)

        info_layout.addStretch()

        # 日期标签
        self.date_label = MacLabel("", "text-sm text-muted")
        info_layout.addWidget(self.date_label)

        layout.addWidget(info_row)

        # 操作按钮行
        button_row = QWidget()
        button_row.setProperty("class", "icon-text-row")
        button_layout = QHBoxLayout(button_row)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(6)

        # 编辑按钮
        self.edit_btn = MacIconButton("✏️", 28)
        self.edit_btn.setToolTip("编辑项目")
        self.edit_btn.clicked.connect(lambda: self.edit_clicked.emit(self.project.id))
        button_layout.addWidget(self.edit_btn)

        # 导出按钮
        self.export_btn = MacIconButton("📤", 28)
        self.export_btn.setToolTip("导出项目")
        self.export_btn.clicked.connect(lambda: self.export_clicked.emit(self.project.id))
        button_layout.addWidget(self.export_btn)

        # 删除按钮（使用危险样式）
        self.delete_btn = MacIconButton("🗑️", 28)
        self.delete_btn.setProperty("class", "button icon-only danger")
        self.delete_btn.setToolTip("删除项目")
        self.delete_btn.clicked.connect(lambda: self.delete_clicked.emit(self.project.id))
        button_layout.addWidget(self.delete_btn)

        button_layout.addStretch()
        layout.addWidget(button_row)

    def _update_display(self):
        """更新显示"""
        self.name_label.setText(self.project.metadata.name)
        self.desc_label.setText(self.project.metadata.description or "无描述")
        self.type_badge.setText(self.project.metadata.project_type.value)
        self.date_label.setText(self.project.metadata.modified_at.strftime("%m-%d"))

    def mousePressEvent(self, event):
        """鼠标点击事件 - 点击卡片本身触发"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 检查点击位置是否在操作按钮区域外
            # 简单处理：点击卡片即触发
            self.clicked.emit(self.project.id)
        super().mousePressEvent(event)


class TemplateCard(MacCard):
    """模板卡片组件 - 使用标准化 macOS 组件"""

    selected = Signal(str)  # 模板选择信号
    preview_clicked = Signal(str)  # 预览点击信号

    def __init__(self, template, parent=None):
        super().__init__(parent)
        self.template = template
        self.is_selected = False
        self.setProperty("class", "card template-card")
        self.setFixedSize(220, 180)
        self.set_interactive(True)

        self._setup_ui()
        self._update_display()

    def _setup_ui(self):
        """设置UI - 使用 QSS 类名，无内联样式"""
        self.layout().setSpacing(8)
        self.layout().setContentsMargins(12, 12, 12, 12)

        # 模板名称
        self.name_label = MacLabel("", "text-lg text-bold")
        self.name_label.setWordWrap(True)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self.name_label)

        # 模板预览图容器
        preview_container = QWidget()
        preview_container.setProperty("class", "template-preview-container")
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)

        self.preview_label = QLabel()
        self.preview_label.setFixedSize(160, 90)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setProperty("class", "template-preview")
        preview_layout.addWidget(self.preview_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.layout().addWidget(preview_container)

        # 模板类别徽章
        self.category_badge = MacBadge("", "primary")
        self.category_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self.category_badge, alignment=Qt.AlignmentFlag.AlignCenter)

    def _update_display(self):
        """更新显示"""
        self.name_label.setText(self.template.name)
        self.category_badge.setText(self.template.category)

        # 加载预览图
        if self.template.preview_image and os.path.exists(self.template.preview_image):
            pixmap = QPixmap(self.template.preview_image)
            scaled_pixmap = pixmap.scaled(160, 90, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.preview_label.setPixmap(scaled_pixmap)
        else:
            self.preview_label.setText("🖼️")

    def set_selected(self, selected: bool):
        """设置选中状态"""
        self.is_selected = selected
        if selected:
            self.setProperty("class", "card template-card template-selected")
        else:
            self.setProperty("class", "card template-card")

        # 刷新样式
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_selected(True)
            self.selected.emit(self.template.id)
        super().mousePressEvent(event)
