#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Voxplore 项目管理页面 - 重构版
使用独立的 ProjectsListPanel 和 ProjectDetailsPanel 组件
"""

import logging
from typing import Optional
from PySide6.QtWidgets import QSplitter, QWidget
from PySide6.QtCore import Qt

from .base_page import BasePage
from voxplore.ui.components import MacPageToolbar, MacPrimaryButton, MacSecondaryButton, MacIconButton


class ProjectsPage(BasePage):
    """项目管理页面 - 简洁版，委托给面板组件"""

    def __init__(self, application):
        super().__init__("projects", "项目管理", application)

        self._logger = logging.getLogger(__name__)

        # 获取服务
        self._project_manager = application.get_service_by_name("project_manager")
        self._template_manager = application.get_service_by_name("template_manager")
        self._settings_manager = application.get_service_by_name("settings_manager")

        # 面板引用
        self._list_panel: Optional[QWidget] = None
        self._details_panel: Optional[QWidget] = None

        self._check_services()

    def initialize(self) -> bool:
        """初始化页面"""
        try:
            self._logger.info("Initializing projects page")
            self._init_ui()
            self._list_panel.load_projects()
            return True
        except Exception as e:
            self._logger.error(f"Failed to initialize projects page: {e}")
            return False

    def create_content(self) -> None:
        """创建页面内容"""
        self._refresh()

    def _check_services(self):
        """检查服务状态"""
        if not self._project_manager:
            self._logger.warning("项目管理器服务未找到")
        if not self._template_manager:
            self._logger.warning("模板管理器服务未找到")
        if not self._settings_manager:
            self._logger.warning("设置管理器服务未找到")

    def _init_ui(self):
        """初始化UI"""
        from .components.proj_details_pnl import ProjectDetailsPanel
        from .components.proj_list_pnl import ProjectsListPanel

        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # 标题栏
        header = self._create_header()
        self.main_layout.addWidget(header)

        # 分割布局：左侧列表 + 右侧详情
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：列表面板
        self._list_panel = ProjectsListPanel(self._project_manager)
        # 连接列表信号到详情面板
        self._list_panel.project_selected.connect(self._on_project_selected)
        splitter.addWidget(self._list_panel)

        # 右侧：详情面板
        self._details_panel = ProjectDetailsPanel(
            self._project_manager,
            self._settings_manager
        )
        splitter.addWidget(self._details_panel)

        splitter.setSizes([400, 400])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, True)

        self.main_layout.addWidget(splitter, 1)

    def _create_header(self) -> QWidget:
        """创建标题栏"""
        toolbar = MacPageToolbar("📁 项目管理")

        new_btn = MacPrimaryButton("✨ 新建项目")
        new_btn.clicked.connect(self._on_new_project)
        toolbar.add_action(new_btn)

        open_btn = MacSecondaryButton("📂 打开项目")
        open_btn.clicked.connect(self._on_open_project)
        toolbar.add_action(open_btn)

        import_btn = MacSecondaryButton("📥 导入项目")
        import_btn.clicked.connect(self._on_import_project)
        toolbar.add_action(import_btn)

        refresh_btn = MacIconButton("🔄", 32)
        refresh_btn.setToolTip("刷新")
        refresh_btn.clicked.connect(self._on_refresh)
        toolbar.add_action(refresh_btn)

        return toolbar

    # ── 事件处理 ──────────────────────────────────────────────

    def _on_project_selected(self, project_id: str):
        """项目选中"""
        self._details_panel.show_project(project_id)

    def _on_new_project(self):
        """新建项目"""
        from PySide6.QtWidgets import QMessageBox, QDialog
        from .components.create_proj_dlg import CreateProjectDialog

        if not self._template_manager:
            QMessageBox.warning(self, "错误", "模板管理器不可用，无法创建项目")
            return
        if not self._project_manager:
            QMessageBox.warning(self, "错误", "项目管理器不可用，无法创建项目")
            return

        try:
            dialog = CreateProjectDialog(self._template_manager, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                info = dialog.get_project_info()
                project_id = self._project_manager.create_project(
                    name=info['name'],
                    project_type=info['type'],
                    description=info['description'],
                    template_id=info['template_id']
                )
                if project_id:
                    QMessageBox.information(self, "成功", "项目创建成功！")
                    self._list_panel.load_projects()
                    self._details_panel.show_project(project_id)
                else:
                    QMessageBox.warning(self, "失败", "无法创建项目")
        except Exception as e:
            self._logger.error(f"创建项目异常: {e}")
            QMessageBox.critical(self, "错误", f"创建项目时发生错误: {str(e)}")

    def _on_open_project(self):
        """打开项目"""
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        if not self._project_manager:
            return

        path, _ = QFileDialog.getOpenFileName(
            self, "打开项目", "", "Voxplore项目 (*.json)"
        )
        if path:
            import os
            project_dir = os.path.dirname(path)
            project_id = self._project_manager.open_project(project_dir)
            if project_id:
                QMessageBox.information(self, "成功", "项目打开成功！")
                self._list_panel.load_projects()
                self._details_panel.show_project(project_id)
            else:
                QMessageBox.warning(self, "失败", "无法打开项目")

    def _on_import_project(self):
        """导入项目"""
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        if not self._project_manager:
            return

        path, _ = QFileDialog.getOpenFileName(
            self, "导入项目", "", "Voxplore项目包 (*.zip)"
        )
        if path:
            project_id = self._project_manager.import_project(path)
            if project_id:
                QMessageBox.information(self, "成功", "项目导入成功！")
                self._list_panel.load_projects()
                self._details_panel.show_project(project_id)
            else:
                QMessageBox.warning(self, "失败", "无法导入项目")

    def _on_refresh(self):
        """刷新"""
        self._list_panel.load_projects()

    def refresh(self):
        """刷新页面"""
        if hasattr(self, '_list_panel') and self._list_panel:
            self._list_panel.load_projects()

    def get_page_type(self) -> str:
        """获取页面类型"""
        return "projects"
