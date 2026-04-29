#!#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Voxplore 项目管理页面 - macOS 设计系统优化版
使用标准化组件，零内联样式
"""

import os
import logging
from typing import Optional
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QSplitter, QStackedWidget, QMessageBox, QDialog, QFileDialog, QComboBox, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer

from .base_page import BasePage

# 导入辅助函数
from app.ui.common.macos_components import create_icon_text_row
from app.core.project_manager import ProjectManager, Project, ProjectType, ProjectStatus
from app.core.project_template_manager import ProjectTemplateManager
from app.core.project_settings_manager import ProjectSettingsManager

# 导入标准化组件
from app.ui.components import (
    MacCard, MacElevatedCard, MacPrimaryButton, MacSecondaryButton,
    MacDangerButton, MacIconButton, MacTitleLabel, MacLabel, MacBadge,
    MacPageToolbar, MacScrollArea, MacEmptyState,
    MacSearchBox,
)



# 导入项目卡片组件
from .components import ProjectCard, stats


# 导入对话框组件
from .components.dialogs import CreateProjectDialog, ProjectSettingsDialog


# 快捷访问
_create_stat_item = stats.create_stat_item
_create_detail_row = stats.create_detail_row

class ProjectsPage(BasePage):
    """项目管理页面"""

    def __init__(self, application):
        super().__init__("projects", "项目管理", application)

        # 日志器
        self.logger = logging.getLogger(__name__)

        # 初始化管理器
        self.project_manager: Optional[ProjectManager] = application.get_service_by_name("project_manager")
        self.template_manager: Optional[ProjectTemplateManager] = application.get_service_by_name("template_manager")
        self.settings_manager: Optional[ProjectSettingsManager] = application.get_service_by_name("settings_manager")

        # 当前选中的项目
        self.selected_project_id: Optional[str] = None

        # 检查服务状态
        self._check_services()

    def initialize(self) -> bool:
        """初始化页面"""
        try:
            self.logger.info("Initializing projects page")

            # 初始化UI
            self._init_ui()

            # 加载项目数据（添加检查，避免NoneType错误）
            self._load_projects()

            # 定时刷新
            self._setup_refresh_timer()

            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize projects page: {e}")
            return False

    def create_content(self) -> None:
        """创建页面内容"""
        # 内容创建已在 _init_ui 中完成
        # 刷新项目列表
        self._refresh_project_list()

    def _check_services(self):
        """检查服务状态"""
        if not self.project_manager:
            self.logger.warning("项目管理器服务未找到")
        if not self.template_manager:
            self.logger.warning("模板管理器服务未找到")
        if not self.settings_manager:
            self.logger.warning("设置管理器服务未找到")

    def _init_ui(self):
        """初始化UI"""
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # 标题和操作栏
        header_widget = self._create_header_section()
        self.main_layout.addWidget(header_widget)

        # 主内容区域
        content_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：项目列表
        left_widget = self._create_projects_section()
        content_splitter.addWidget(left_widget)

        # 右侧：项目详情
        right_widget = self._create_project_details_section()
        content_splitter.addWidget(right_widget)

        # 设置分割器比例
        content_splitter.setSizes([400, 400])
        content_splitter.setCollapsible(0, False)
        content_splitter.setCollapsible(1, True)

        self.main_layout.addWidget(content_splitter, 1)

    def _create_header_section(self) -> QWidget:
        """创建标题区域 - 使用 MacPageToolbar"""
        toolbar = MacPageToolbar("📁 项目管理")

        # 操作按钮
        self.new_project_btn = MacPrimaryButton("✨ 新建项目")
        self.new_project_btn.clicked.connect(self._on_new_project)
        toolbar.add_action(self.new_project_btn)

        self.open_project_btn = MacSecondaryButton("📂 打开项目")
        self.open_project_btn.clicked.connect(self._on_open_project)
        toolbar.add_action(self.open_project_btn)

        self.import_project_btn = MacSecondaryButton("📥 导入项目")
        self.import_project_btn.clicked.connect(self._on_import_project)
        toolbar.add_action(self.import_project_btn)

        self.refresh_btn = MacIconButton("🔄", 32)
        self.refresh_btn.setToolTip("刷新")
        self.refresh_btn.clicked.connect(self._refresh_projects)
        toolbar.add_action(self.refresh_btn)

        return toolbar

    def _create_projects_section(self) -> QWidget:
        """创建项目列表区域 - 使用标准化卡片布局"""
        widget = MacElevatedCard()
        widget.setProperty("class", "card section-card")
        widget.layout().setSpacing(12)

        # 搜索和过滤区域
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(8)

        # 搜索框（使用 MacSearchBox）
        self.search_box = MacSearchBox("🔍 搜索项目...")
        # MacSearchBox 的 searchRequested 信号会传回 query
        # 但我们还有下拉过滤，所以统一用 _filter_projects
        self.search_box.searchRequested.connect(lambda: self._filter_projects())
        filter_layout.addWidget(self.search_box, 1)

        # 按钮组用于类型和状态过滤
        self.type_filter = QComboBox()
        self.type_filter.setProperty("class", "input")
        self.type_filter.setMinimumWidth(120)
        self.type_filter.addItem("全部类型")
        for project_type in ProjectType:
            self.type_filter.addItem(project_type.value)
        self.type_filter.currentTextChanged.connect(self._filter_projects)
        filter_layout.addWidget(self.type_filter)

        self.status_filter = QComboBox()
        self.status_filter.setProperty("class", "input")
        self.status_filter.setMinimumWidth(120)
        self.status_filter.addItem("全部状态")
        for status in ProjectStatus:
            self.status_filter.addItem(status.value)
        self.status_filter.currentTextChanged.connect(self._filter_projects)
        filter_layout.addWidget(self.status_filter)

        filter_container = QWidget()
        filter_container.setLayout(filter_layout)
        widget.layout().addWidget(filter_container)

        # 项目网格（使用 MacScrollArea）
        self.projects_scroll = MacScrollArea()
        self.projects_widget = QWidget()
        self.projects_widget.setProperty("class", "grid")
        self.projects_layout = QGridLayout(self.projects_widget)
        self.projects_layout.setSpacing(12)
        self.projects_layout.setContentsMargins(0, 0, 0, 0)
        self.projects_scroll.setWidget(self.projects_widget)
        widget.layout().addWidget(self.projects_scroll, 1)

        return widget

    def _filter_projects(self):
        """过滤项目 - 响应搜索框和下拉框"""
        # 获取搜索文本
        search_text = ""
        if hasattr(self, 'search_box') and self.search_box:
            search_text = self.search_box.input.text().lower()

        type_filter = self.type_filter.currentText()
        status_filter = self.status_filter.currentText()

        for project_id, card in self.project_cards.items():
            project = card.project
            matches = True

            # 搜索过滤
            if search_text:
                matches = (search_text in project.metadata.name.lower() or
                           search_text in project.metadata.description.lower())

            # 类型过滤
            if matches and type_filter != "全部类型":
                matches = project.metadata.project_type.value == type_filter

            # 状态过滤
            if matches and status_filter != "全部状态":
                matches = project.metadata.status.value == status_filter

            card.setVisible(matches)

    def _create_project_details_section(self) -> QWidget:
        """创建项目详情区域 - 重新设计的现代化布局"""
        widget = MacElevatedCard()
        widget.setProperty("class", "card section-card")
        widget.layout().setSpacing(16)

        # 详情标题
        title_row = create_icon_text_row("📋", "项目详情")
        widget.layout().addWidget(title_row)

        # 详情内容 - 使用 StackedWidget
        self.details_stack = QStackedWidget()

        # 空状态页面
        empty_widget = MacEmptyState(
            icon="📭",
            title="未选择项目",
            description="请在左侧选择一个项目查看详情"
        )
        self.details_stack.addWidget(empty_widget)

        # 项目详情页面（使用 MacScrollArea）
        self.details_scroll = MacScrollArea()
        self.details_widget = self._create_project_details_content()
        self.details_scroll.setWidget(self.details_widget)
        self.details_stack.addWidget(self.details_scroll)

        widget.layout().addWidget(self.details_stack, 1)

        # 操作按钮
        self.details_buttons = self._create_details_buttons()
        widget.layout().addWidget(self.details_buttons)

        # 初始禁用按钮
        self._set_details_buttons_enabled(False)

        return widget

    def _set_details_buttons_enabled(self, enabled: bool):
        """设置详情按钮启用状态"""
        if hasattr(self, 'edit_project_btn'):
            self.edit_project_btn.setEnabled(enabled)
        if hasattr(self, 'settings_project_btn'):
            self.settings_project_btn.setEnabled(enabled)
        if hasattr(self, 'export_project_btn'):
            self.export_project_btn.setEnabled(enabled)
        if hasattr(self, 'delete_project_btn'):
            self.delete_project_btn.setEnabled(enabled)
        if hasattr(self, 'open_project_btn'):
            self.open_project_btn.setEnabled(enabled)

    def _create_project_details_content(self) -> QWidget:
        """创建项目详情内容 - 现代化卡片布局"""
        content = QWidget()
        content.setProperty("class", "section-content")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # ===== 1. 项目预览卡片 =====
        preview_card = MacCard()
        preview_card.setProperty("class", "card")
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setSpacing(12)

        # 项目图标/预览区域
        self.detail_icon_label = QLabel()
        self.detail_icon_label.setFixedSize(80, 80)
        self.detail_icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail_icon_label.setStyleSheet("font-size: 48px;")
        preview_layout.addWidget(self.detail_icon_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # 项目名称（大标题）
        self.detail_name = MacTitleLabel("")
        self.detail_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detail_name.setStyleSheet("font-size: 18px; font-weight: bold;")
        preview_layout.addWidget(self.detail_name, alignment=Qt.AlignmentFlag.AlignCenter)

        # 项目类型徽章
        self.detail_type_badge = MacBadge("")
        self.detail_type_badge.setProperty("class", "badge badge-primary")
        self.detail_type_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(self.detail_type_badge, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(preview_card)

        # ===== 2. 统计信息卡片（网格布局）=====
        stats_card = MacCard()
        stats_card.setProperty("class", "card")
        stats_layout = QGridLayout(stats_card)
        stats_layout.setSpacing(12)

        # 媒体文件数
        self.stat_media_container = self._create_stat_item("🎬", "媒体文件", "0")
        stats_layout.addWidget(self.stat_media_container, 0, 0)

        # 总时长
        self.stat_duration_container = self._create_stat_item("⏱️", "总时长", "0:00")
        stats_layout.addWidget(self.stat_duration_container, 0, 1)

        # 项目大小
        self.stat_size_container = self._create_stat_item("💾", "项目大小", "0 MB")
        stats_layout.addWidget(self.stat_size_container, 1, 0)

        # 项目状态
        self.stat_status_container = self._create_stat_item("📊", "状态", "未设置")
        stats_layout.addWidget(self.stat_status_container, 1, 1)

        layout.addWidget(stats_card)

        # ===== 3. 基本信息卡片 =====
        info_card = MacCard()
        info_card.setProperty("class", "card")
        info_layout = QVBoxLayout(info_card)
        info_layout.setSpacing(8)

        info_title = MacTitleLabel("时间信息")
        info_layout.addWidget(info_title)

        self.detail_created = MacLabel("", css_class="text-base")
        info_layout.addWidget(self._create_detail_row("🗓️ 创建时间:", self.detail_created))

        self.detail_modified = MacLabel("", css_class="text-base")
        info_layout.addWidget(self._create_detail_row("🔄 修改时间:", self.detail_modified))

        layout.addWidget(info_card)

        # ===== 4. 描述卡片 =====
        desc_card = MacCard()
        desc_card.setProperty("class", "card")
        desc_layout = QVBoxLayout(desc_card)
        desc_layout.setSpacing(8)

        desc_title = MacTitleLabel("项目描述")
        desc_layout.addWidget(desc_title)

        self.detail_description = MacLabel("暂无描述", css_class="text-secondary")
        self.detail_description.setWordWrap(True)
        desc_layout.addWidget(self.detail_description)

        layout.addWidget(desc_card)

        layout.addStretch()

        return content

    def _create_details_buttons(self) -> QWidget:
        """创建详情区域按钮 - 现代化布局"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 打开项目按钮（主要操作）
        self.open_project_btn = MacPrimaryButton("🚀 打开项目")
        self.open_project_btn.clicked.connect(self._on_edit_project)
        layout.addWidget(self.open_project_btn)

        # 编辑按钮
        self.edit_project_btn = MacSecondaryButton("✏️ 编辑")
        self.edit_project_btn.clicked.connect(self._on_edit_project)
        layout.addWidget(self.edit_project_btn)

        # 设置按钮
        self.settings_project_btn = MacSecondaryButton("⚙️ 设置")
        self.settings_project_btn.clicked.connect(self._on_project_settings)
        layout.addWidget(self.settings_project_btn)

        # 导出按钮
        self.export_project_btn = MacSecondaryButton("📤 导出")
        self.export_project_btn.clicked.connect(self._on_export_project)
        layout.addWidget(self.export_project_btn)

        # 删除按钮
        self.delete_project_btn = MacDangerButton("🗑️ 删除")
        self.delete_project_btn.clicked.connect(self._on_delete_project)
        layout.addWidget(self.delete_project_btn)

        layout.addStretch()

        return widget

    def _load_projects(self):
        """加载项目列表"""
        self.project_cards = {}

        # 检查布局是否仍然有效（防止 Qt 对象已删除的竞态条件）
        if not hasattr(self, 'projects_layout') or self.projects_layout is None:
            self.logger.debug("项目布局已失效，跳过加载")
            return

        # 检查父控件是否已删除
        try:
            if self.projects_layout.parent() is None:
                self.logger.debug("项目布局父控件已失效，跳过加载")
                return
        except RuntimeError:
            self.logger.debug("项目布局已失效，跳过加载")
            return

        # 检查项目管理器是否可用
        if not self.project_manager:
            self.logger.warning("项目管理器不可用，无法加载项目")

            # 显示空状态
            try:
                self.projects_layout.addItem(QSpacerItem(1, 1, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding), 0, 0)
            except RuntimeError as e:
                self.logger.warning(f"添加空状态间隔器失败: {e}")
            return

        try:
            projects = self.project_manager.get_all_projects()
        except Exception as e:
            self.logger.error(f"获取项目列表失败: {e}")
            return

        # 清空现有卡片
        try:
            for i in reversed(range(self.projects_layout.count())):
                child = self.projects_layout.itemAt(i).widget()
                if child:
                    child.deleteLater()
                else:
                    # 移除非widget项（如QSpacerItem）
                    item = self.projects_layout.takeAt(i)
                    if item and hasattr(item, 'deleteLater'):
                        item.deleteLater()
        except RuntimeError as e:
            self.logger.warning(f"清空项目布局时出错: {e}")
            return

        # 添加项目卡片
        row, col = 0, 0
        for project in projects:
            card = ProjectCard(project)
            card.clicked.connect(self._on_project_selected)
            card.edit_clicked.connect(self._on_edit_project)
            card.export_clicked.connect(self._on_export_project)
            card.delete_clicked.connect(self._on_delete_project)

            self.projects_layout.addWidget(card, row, col)
            self.project_cards[project.id] = card

            col += 1
            if col >= 2:
                col = 0
                row += 1

        # 添加拉伸空间
        self.projects_layout.addItem(QSpacerItem(1, 1, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding), row, col)

    # _filter_projects 已在前面定义，支持 MacSearchBox

    def _on_project_selected(self, project_id: str):
        """项目选择"""
        self.selected_project_id = project_id
        project = self.project_manager.get_project(project_id)

        if project:
            # 更新详情显示
            self._update_project_details(project)
            self.details_stack.setCurrentWidget(self.details_widget)

            # 更新按钮状态 - 使用新方法启用按钮
            self._set_details_buttons_enabled(True)

    def _update_project_details(self, project: Project):
        """更新项目详情 - 适配新的UI组件"""
        # Guard: ensure UI widgets are initialized before accessing them
        if not hasattr(self, 'detail_type_badge') or not hasattr(self, 'detail_name') or not hasattr(self, 'detail_icon_label'):
            self.logger.debug("UI widgets not yet initialized, skipping detail update")
            return
        # 项目图标（根据类型显示不同图标）
        project_type = project.metadata.project_type.value
        icon_map = {
            "视频剪辑": "🎬",
            "视频合成": "🎨",
            "音频处理": "🎵",
            "字幕制作": "📝",
            "格式转换": "🔄"
        }
        self.detail_icon_label.setText(icon_map.get(project_type, "📁"))

        # 项目名称
        self.detail_name.setText(project.metadata.name)

        # 项目类型徽章
        self.detail_type_badge.setText(project_type)

        # 统计信息（更新容器内的值标签）
        media_count = len(project.media_files)
        if hasattr(self, 'stat_media_container') and hasattr(self.stat_media_container, 'stat_value_label'):
            self.stat_media_container.stat_value_label.setText(str(media_count))

        duration = project.timeline.duration
        duration_str = self._format_duration(duration)
        if hasattr(self, 'stat_duration_container') and hasattr(self.stat_duration_container, 'stat_value_label'):
            self.stat_duration_container.stat_value_label.setText(duration_str)

        project_size = self._calculate_project_size(project)
        size_str = self._format_file_size(project_size)
        if hasattr(self, 'stat_size_container') and hasattr(self.stat_size_container, 'stat_value_label'):
            self.stat_size_container.stat_value_label.setText(size_str)

        status = project.metadata.status.value
        if hasattr(self, 'stat_status_container') and hasattr(self.stat_status_container, 'stat_value_label'):
            self.stat_status_container.stat_value_label.setText(status)

        # 时间信息
        self.detail_created.setText(project.metadata.created_at.strftime("%Y-%m-%d %H:%M:%S"))
        self.detail_modified.setText(project.metadata.modified_at.strftime("%Y-%m-%d %H:%M:%S"))

        # 描述
        self.detail_description.setText(project.metadata.description or "暂无描述")

    def _calculate_project_size(self, project: Project) -> int:
        """计算项目大小"""
        try:
            total_size = 0
            project_path = Path(project.path)
            for file_path in project_path.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return total_size
        except Exception:
            return 0

    def _format_file_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes == 0:
            return "0 B"

        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1

        return f"{size_bytes:.1f} {size_names[i]}"

    def _format_duration(self, seconds: float) -> str:
        """格式化时长"""
        if seconds < 60:
            return f"{seconds:.1f}秒"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}:{secs:02d}"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            return f"{hours}:{minutes:02d}:{secs:02d}"

    def _on_new_project(self):
        """新建项目"""
        # 检查模板管理器是否可用
        if not self.template_manager:
            self.logger.warning("template_manager is None, showing warning")
            QMessageBox.warning(self, "错误", "模板管理器不可用，无法创建项目")
            return

        # 检查项目管理器是否可用
        if not self.project_manager:
            self.logger.warning("project_manager is None, showing warning")
            QMessageBox.warning(self, "错误", "项目管理器不可用，无法创建项目")
            return

        try:
            dialog = CreateProjectDialog(self.template_manager, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                project_info = dialog.get_project_info()

                project_id = self.project_manager.create_project(
                    name=project_info['name'],
                    project_type=project_info['type'],
                    description=project_info['description'],
                    template_id=project_info['template_id']
                )

                if project_id:
                    QMessageBox.information(self, "成功", "项目创建成功！")
                    self._load_projects()

                    # 切换到项目详情页面
                    self._on_project_selected(project_id)
                else:
                    QMessageBox.warning(self, "失败", "无法创建项目")
        except Exception as e:
            self.logger.error(f"Exception creating project: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "错误", f"创建项目时发生错误: {str(e)}")

    def _on_open_project(self):
        """打开项目"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开项目", "", "Voxplore项目 (*.json)"
        )

        if file_path:
            project_dir = os.path.dirname(file_path)
            project_id = self.project_manager.open_project(project_dir)

            if project_id:
                QMessageBox.information(self, "成功", "项目打开成功！")
                self._load_projects()
                self._on_project_selected(project_id)
            else:
                QMessageBox.warning(self, "失败", "无法打开项目")

    def _on_import_project(self):
        """导入项目"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入项目", "", "Voxplore项目包 (*.zip)"
        )

        if file_path:
            project_id = self.project_manager.import_project(file_path)

            if project_id:
                QMessageBox.information(self, "成功", "项目导入成功！")
                self._load_projects()
                self._on_project_selected(project_id)
            else:
                QMessageBox.warning(self, "失败", "无法导入项目")

    def _on_edit_project(self, project_id: str = None):
        """编辑项目"""
        if project_id is None:
            project_id = self.selected_project_id

        if project_id:
            project = self.project_manager.get_project(project_id)
            if project:
                # 这里可以打开项目编辑器
                QMessageBox.information(self, "编辑项目", f"正在编辑项目: {project.metadata.name}")

    def _on_project_settings(self, project_id: str = None):
        """项目设置"""
        if project_id is None:
            project_id = self.selected_project_id

        if project_id:
            project = self.project_manager.get_project(project_id)
            if project:
                dialog = ProjectSettingsDialog(project, self.settings_manager, self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    # 保存项目设置
                    self.project_manager.save_project(project_id)
                    QMessageBox.information(self, "成功", "项目设置已保存！")

    def _on_export_project(self, project_id: str = None):
        """导出项目"""
        if project_id is None:
            project_id = self.selected_project_id

        if project_id:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "导出项目", "", "Voxplore项目包 (*.zip)"
            )

            if file_path:
                include_media = QMessageBox.question(
                    self, "包含媒体文件",
                    "是否包含媒体文件一起导出？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                ) == QMessageBox.StandardButton.Yes

                if self.project_manager.export_project(project_id, file_path, include_media):
                    QMessageBox.information(self, "成功", "项目导出成功！")
                else:
                    QMessageBox.warning(self, "失败", "无法导出项目")

    def _on_delete_project(self, project_id: str = None):
        """删除项目"""
        if project_id is None:
            project_id = self.selected_project_id

        if project_id:
            project = self.project_manager.get_project(project_id)
            if project:
                reply = QMessageBox.question(
                    self, "确认删除",
                    f"确定要删除项目 '{project.metadata.name}' 吗？\n此操作不可撤销！",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )

                if reply == QMessageBox.StandardButton.Yes:
                    if self.project_manager.delete_project(project_id):
                        QMessageBox.information(self, "成功", "项目删除成功！")
                        self._load_projects()
                        self.details_stack.setCurrentWidget(self.details_stack.widget(0))  # 显示空状态
                        self.selected_project_id = None
                        # 禁用按钮
                        self._set_details_buttons_enabled(False)
                    else:
                        QMessageBox.warning(self, "失败", "无法删除项目")

    def _refresh_projects(self):
        """刷新项目列表"""
        self._load_projects()
        QMessageBox.information(self, "刷新", "项目列表已刷新！")

    def _setup_refresh_timer(self):
        """设置定时刷新"""
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._auto_refresh)
        self.refresh_timer.start(60000)  # 每分钟刷新一次

    def _auto_refresh(self):
        """自动刷新"""
        if self.selected_project_id:
            project = self.project_manager.get_project(self.selected_project_id)
            if project:
                self._update_project_details(project)

    def refresh(self):
        """刷新页面"""
        self._load_projects()
        if self.selected_project_id:
            project = self.project_manager.get_project(self.selected_project_id)
            if project:
                self._update_project_details(project)

    def get_page_type(self) -> str:
        """获取页面类型"""
        return "projects"
