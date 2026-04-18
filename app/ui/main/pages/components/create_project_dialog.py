#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
创建项目对话框
"""

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QDialog, QLineEdit, QComboBox,
    QMessageBox
)
from PySide6.QtCore import Qt

from app.ui.components import (
    MacPrimaryButton, MacSecondaryButton, MacTitleLabel, MacLabel,
    MacSearchBox, MacScrollArea,
)
from app.core.project_template_manager import ProjectTemplateManager

from .project_cards import TemplateCard


class CreateProjectDialog(QDialog):
    """创建项目对话框 - macOS 风格"""

    def __init__(self, template_manager: ProjectTemplateManager, parent=None):
        super().__init__(parent)
        self.template_manager = template_manager
        self.selected_template = None
        self.templates = []
        self.setProperty("class", "modal-container")
        self._setup_ui()
        if template_manager is not None:
            self._load_templates()

    def _setup_ui(self):
        """设置UI - 使用标准化组件和 QSS 类"""
        self.setWindowTitle("创建新项目")
        self.setModal(True)
        self.setFixedSize(640, 560)

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 模态头部
        header = QWidget()
        header.setProperty("class", "modal-header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 16)

        title = MacTitleLabel("✨ 创建新项目")
        header_layout.addWidget(title)
        header_layout.addStretch()

        close_btn = MacSecondaryButton("✖️")
        close_btn.setFixedSize(32, 32)
        close_btn.clicked.connect(self.reject)
        header_layout.addWidget(close_btn)

        main_layout.addWidget(header)

        # 内容区域
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 16, 20, 16)
        content_layout.setSpacing(12)

        # 名称输入
        name_row = QWidget()
        name_layout = QHBoxLayout(name_row)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(8)

        name_label = MacLabel("📝 名称:", css_class="text-bold")
        name_layout.addWidget(name_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("输入项目名称")
        self.name_input.setText("")
        self.name_input.textChanged.connect(self._on_name_changed)
        name_layout.addWidget(self.name_input, 1)

        content_layout.addWidget(name_row)

        # 类型选择
        type_row = QWidget()
        type_layout = QHBoxLayout(type_row)
        type_layout.setContentsMargins(0, 0, 0, 0)
        type_layout.setSpacing(8)

        type_label = MacLabel("🎬 类型:", css_class="text-bold")
        type_layout.addWidget(type_label)

        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "视频剪辑",
            "AI 增强",
            "混剪合成",
            "AI 解说",
            "剧情分析",
            "多媒体"
        ])
        type_layout.addWidget(self.type_combo, 1)

        content_layout.addWidget(type_row)

        # 模板选择标签
        template_label = MacLabel("📋 模板:", css_class="text-bold")
        content_layout.addWidget(template_label)

        # 模板搜索
        self.template_search = MacSearchBox()
        self.template_search.setPlaceholderText("搜索模板...")
        self.template_search.textChanged.connect(self._on_template_search)
        content_layout.addWidget(self.template_search)

        # 模板列表
        self.template_list = MacScrollArea()
        self.template_grid = TemplateCard.create_grid_widget()
        self.template_list.setWidget(self.template_grid)
        self.template_list.setWidgetResizable(True)
        content_layout.addWidget(self.template_list, 1)

        # 按钮区域
        footer = QWidget()
        footer.setProperty("class", "modal-footer")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(20, 12, 20, 12)

        footer_layout.addStretch()

        cancel_btn = MacSecondaryButton("取消")
        cancel_btn.clicked.connect(self.reject)
        footer_layout.addWidget(cancel_btn)

        self.create_btn = MacPrimaryButton("✨ 创建")
        self.create_btn.clicked.connect(self._on_create)
        self.create_btn.setEnabled(False)
        footer_layout.addWidget(self.create_btn)

        main_layout.addWidget(footer)

    def _load_templates(self):
        """加载模板列表"""
        try:
            self.templates = self.template_manager.get_all_templates()
            self._render_templates()
        except Exception as e:
            self.template_list.setWidget(MacLabel(f"加载失败: {e}"))

    def _render_templates(self):
        """渲染模板列表"""
        from .project_cards import TemplateCard
        from PySide6.QtWidgets import QGridLayout, QWidget

        grid = QWidget()
        layout = QGridLayout(grid)
        layout.setSpacing(12)

        search_text = self.template_search.text().lower()

        for i, template in enumerate(self.templates):
            if search_text and search_text not in template.name.lower():
                continue

            card = TemplateCard(template, selected=False)
            card.clicked.connect(lambda t=template: self._on_template_selected(t))
            row = i // 2
            col = i % 2
            layout.addWidget(card, row, col)

        # 添加空白占位
        while layout.count() < 4:
            i = layout.count()
            row = i // 2
            col = i % 2
            layout.addWidget(QWidget(), row, col)

        scroll = self.template_list
        scroll.setWidget(grid)
        scroll.setWidgetResizable(False)
        scroll.setWidget(grid)

    def _on_template_search(self, text: str):
        """模板搜索"""
        self._render_templates()

    def _on_name_changed(self, text: str):
        """名称改变"""
        self.create_btn.setEnabled(bool(text.strip()))

    def _on_template_selected(self, template):
        """选择模板"""
        for i in range(self.template_grid.layout().count()):
            widget = self.template_grid.layout().itemAt(i).widget()
            if isinstance(widget, TemplateCard):
                widget.set_selected(widget.template.id == template.id)
        self.selected_template = template

    def _on_create(self):
        """创建项目"""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入项目名称")
            return

        self.accept()

    def get_project_info(self):
        """获取项目信息"""
        return {
            "name": self.name_input.text().strip(),
            "type": self.type_combo.currentIndex(),
            "template": self.selected_template,
        }


__all__ = ["CreateProjectDialog"]
