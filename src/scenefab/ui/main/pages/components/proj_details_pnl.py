#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
项目管理详情面板 - 独立的详情展示组件
从 projects_page.py 拆分出来
"""

import logging
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QStackedWidget, QMessageBox, QDialog,
)
from PySide6.QtCore import Qt

from ....components import (
    MacCard, MacElevatedCard, MacPrimaryButton, MacSecondaryButton,
    MacDangerButton, MacTitleLabel, MacLabel, MacBadge,
    MacScrollArea, MacEmptyState,
)
from ....common.macos_components import create_icon_text_row
from .settings_dialog import ProjectSettingsDialog
from .stats import create_stat_item

logger = logging.getLogger(__name__)


class ProjectDetailsPanel(QWidget):
    """
    项目详情面板
    负责展示单个项目的详细信息和操作按钮
    """

    def __init__(self, project_manager, settings_manager, parent=None):
        super().__init__(parent)
        self._project_manager = project_manager
        self._settings_manager = settings_manager
        self._current_project_id = None
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # 详情卡片
        card = MacElevatedCard()
        card.layout().setSpacing(16)

        # 标题
        title_row = create_icon_text_row("📋", "项目详情")
        card.layout().addWidget(title_row)

        # 堆叠窗口：空状态 / 详情内容
        self._stack = QStackedWidget()

        # 空状态
        empty = MacEmptyState(
            icon="📭",
            title="未选择项目",
            description="请在左侧选择一个项目查看详情"
        )
        self._stack.addWidget(empty)

        # 详情内容
        self._details_scroll = MacScrollArea()
        self._details_content = self._create_details_content()
        self._details_scroll.setWidget(self._details_content)
        self._stack.addWidget(self._details_scroll)

        card.layout().addWidget(self._stack, 1)

        # 操作按钮
        self._buttons = self._create_buttons()
        card.layout().addWidget(self._buttons)

        layout.addWidget(card)

        # 初始禁用按钮
        self._set_buttons_enabled(False)

    def _create_details_content(self) -> QWidget:
        """创建详情内容"""
        content = QWidget()
        content.setProperty("class", "section-content")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # 1. 预览卡片
        preview_card = MacCard()
        preview_card.setProperty("class", "card")
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setSpacing(12)

        self._icon_label = QLabel()
        self._icon_label.setFixedSize(80, 80)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setStyleSheet("font-size: 48px;")
        preview_layout.addWidget(self._icon_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self._name_label = MacTitleLabel("")
        self._name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._name_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        preview_layout.addWidget(self._name_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self._type_badge = MacBadge("")
        self._type_badge.setProperty("class", "badge badge-primary")
        self._type_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(self._type_badge, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(preview_card)

        # 2. 统计卡片
        stats_card = MacCard()
        stats_card.setProperty("class", "card")
        stats_layout = QGridLayout(stats_card)
        stats_layout.setSpacing(12)

        self._stat_media = create_stat_item("🎬", "媒体文件", "0")
        stats_layout.addWidget(self._stat_media, 0, 0)

        self._stat_duration = create_stat_item("⏱️", "总时长", "0:00")
        stats_layout.addWidget(self._stat_duration, 0, 1)

        self._stat_size = create_stat_item("💾", "项目大小", "0 MB")
        stats_layout.addWidget(self._stat_size, 1, 0)

        self._stat_status = create_stat_item("📊", "状态", "未设置")
        stats_layout.addWidget(self._stat_status, 1, 1)

        layout.addWidget(stats_card)

        # 3. 基本信息卡片
        info_card = MacCard()
        info_card.setProperty("class", "card")
        info_layout = QVBoxLayout(info_card)
        info_layout.setSpacing(8)

        info_title = MacTitleLabel("时间信息")
        info_layout.addWidget(info_title)

        self._created_label = MacLabel("", css_class="text-base")
        info_layout.addWidget(self._create_detail_row("🗓️ 创建时间:", self._created_label))

        self._modified_label = MacLabel("", css_class="text-base")
        info_layout.addWidget(self._create_detail_row("🔄 修改时间:", self._modified_label))

        layout.addWidget(info_card)

        # 4. 描述卡片
        desc_card = MacCard()
        desc_card.setProperty("class", "card")
        desc_layout = QVBoxLayout(desc_card)
        desc_layout.setSpacing(8)

        desc_title = MacTitleLabel("项目描述")
        desc_layout.addWidget(desc_title)

        self._description_label = MacLabel("暂无描述", css_class="text-secondary")
        self._description_label.setWordWrap(True)
        desc_layout.addWidget(self._description_label)

        layout.addWidget(desc_card)

        layout.addStretch()
        return content

    def _create_detail_row(self, label_text: str, value_label: QLabel) -> QWidget:
        """创建详情行"""
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        label = QLabel(label_text)
        label.setStyleSheet("color: oklch(0.75 0.01 250);")
        row_layout.addWidget(label)
        row_layout.addWidget(value_label, 1)
        row_layout.addStretch()

        return row

    def _create_buttons(self) -> QWidget:
        """创建操作按钮"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._open_btn = MacPrimaryButton("🚀 打开项目")
        self._open_btn.clicked.connect(self._on_open)
        layout.addWidget(self._open_btn)

        self._edit_btn = MacSecondaryButton("✏️ 编辑")
        self._edit_btn.clicked.connect(self._on_edit)
        layout.addWidget(self._edit_btn)

        self._settings_btn = MacSecondaryButton("⚙️ 设置")
        self._settings_btn.clicked.connect(self._on_settings)
        layout.addWidget(self._settings_btn)

        self._export_btn = MacSecondaryButton("📤 导出")
        self._export_btn.clicked.connect(self._on_export)
        layout.addWidget(self._export_btn)

        self._delete_btn = MacDangerButton("🗑️ 删除")
        self._delete_btn.clicked.connect(self._on_delete)
        layout.addWidget(self._delete_btn)

        layout.addStretch()
        return widget

    def _set_buttons_enabled(self, enabled: bool):
        """设置按钮启用状态"""
        for btn in (self._open_btn, self._edit_btn, self._settings_btn,
                    self._export_btn, self._delete_btn):
            btn.setEnabled(enabled)

    # ── 公开方法 ──────────────────────────────────────────────

    def show_project(self, project_id: str):
        """显示项目详情"""
        self._current_project_id = project_id
        project = self._project_manager.get_project(project_id)
        if not project:
            return

        self._update_details(project)
        self._stack.setCurrentWidget(self._details_content)
        self._set_buttons_enabled(True)

    def clear(self):
        """清空详情，显示空状态"""
        self._current_project_id = None
        self._stack.setCurrentWidget(self._stack.widget(0))
        self._set_buttons_enabled(False)

    def get_current_project_id(self) -> str:
        """获取当前项目ID"""
        return self._current_project_id

    # ── 内部更新 ──────────────────────────────────────────────

    def _update_details(self, project):
        """更新详情显示"""
        # 图标
        icon_map = {
            "视频剪辑": "🎬", "视频合成": "🎨",
            "音频处理": "🎵", "字幕制作": "📝", "格式转换": "🔄"
        }
        self._icon_label.setText(icon_map.get(
            project.metadata.project_type.value, "📁"
        ))

        # 名称和类型
        self._name_label.setText(project.metadata.name)
        self._type_badge.setText(project.metadata.project_type.value)

        # 统计
        self._stat_media.stat_value_label.setText(str(len(project.media_files)))

        duration = project.timeline.duration
        self._stat_duration.stat_value_label.setText(self._format_duration(duration))

        size = self._calc_size(project)
        self._stat_size.stat_value_label.setText(self._format_size(size))

        self._stat_status.stat_value_label.setText(project.metadata.status.value)

        # 时间
        self._created_label.setText(project.metadata.created_at.strftime("%Y-%m-%d %H:%M:%S"))
        self._modified_label.setText(project.metadata.modified_at.strftime("%Y-%m-%d %H:%M:%S"))

        # 描述
        self._description_label.setText(project.metadata.description or "暂无描述")

    def _calc_size(self, project) -> int:
        """计算项目大小"""
        try:
            total = 0
            for fp in Path(project.path).rglob('*'):
                if fp.is_file():
                    total += fp.stat().st_size
            return total
        except Exception as e:
            logger.debug(f"Failed to calculate project size: {e}")
            return 0

    def _format_duration(self, seconds: float) -> str:
        """格式化时长"""
        if seconds < 60:
            return f"{seconds:.1f}秒"
        elif seconds < 3600:
            return f"{int(seconds // 60)}:{int(seconds % 60):02d}"
        else:
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = int(seconds % 60)
            return f"{h}:{m:02d}:{s:02d}"

    def _format_size(self, size_bytes: int) -> str:
        """格式化大小"""
        if size_bytes == 0:
            return "0 B"
        units = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024 and i < len(units) - 1:
            size_bytes /= 1024.0
            i += 1
        return f"{size_bytes:.1f} {units[i]}"

    # ── 按钮事件 ──────────────────────────────────────────────

    def _on_open(self):
        if self._current_project_id:
            project = self._project_manager.get_project(self._current_project_id)
            if project:
                QMessageBox.information(self, "编辑项目",
                    f"正在编辑项目: {project.metadata.name}")

    def _on_edit(self):
        if self._current_project_id:
            project = self._project_manager.get_project(self._current_project_id)
            if project:
                QMessageBox.information(self, "编辑项目",
                    f"正在编辑项目: {project.metadata.name}")

    def _on_settings(self):
        if self._current_project_id:
            project = self._project_manager.get_project(self._current_project_id)
            if project and self._settings_manager:
                dialog = ProjectSettingsDialog(project, self._settings_manager, self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    self._project_manager.save_project(self._current_project_id)
                    QMessageBox.information(self, "成功", "项目设置已保存！")

    def _on_export(self):
        if self._current_project_id:
            from PySide6.QtWidgets import QFileDialog
            path, _ = QFileDialog.getSaveFileName(
                self, "导出项目", "", "SceneFab项目包 (*.zip)"
            )
            if path:
                self._project_manager.export_project(self._current_project_id, path, True)
                QMessageBox.information(self, "成功", "项目导出成功！")

    def _on_delete(self):
        if self._current_project_id:
            project = self._project_manager.get_project(self._current_project_id)
            if project:
                reply = QMessageBox.question(
                    self, "确认删除",
                    f"确定要删除项目 '{project.metadata.name}' 吗？\n此操作不可撤销！",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    if self._project_manager.delete_project(self._current_project_id):
                        QMessageBox.information(self, "成功", "项目删除成功！")
                        self.clear()
