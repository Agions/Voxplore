#!/usr/bin/env python3

"""
项目列表面板 - 独立的列表展示组件
从 projects_page.py 拆分出来
"""

import logging

from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from scenefab.project_manager import ProjectStatus, ProjectType

from ....components import (
    MacElevatedCard,
    MacScrollArea,
    MacSearchBox,
)
from .project_cards import ProjectCard

logger = logging.getLogger(__name__)


class ProjectsListPanel(QWidget):
    """
    项目列表面板
    负责项目列表展示、搜索过滤、项目卡片网格
    """

    # 信号
    project_selected = None  # 初始化时设置
    project_edit_requested = None
    project_export_requested = None
    project_delete_requested = None

    def __init__(self, project_manager, parent=None):
        super().__init__(parent)
        self._project_manager = project_manager
        self._project_cards = {}
        self._signals_initialized = False
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 卡片容器
        card = MacElevatedCard()
        card.layout().setSpacing(12)

        # 过滤区域
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(8)

        self._search_box = MacSearchBox("🔍 搜索项目...")
        self._search_box.searchRequested.connect(self._on_filter_changed)
        filter_layout.addWidget(self._search_box, 1)

        self._type_filter = QComboBox()
        self._type_filter.setProperty("class", "input")
        self._type_filter.setMinimumWidth(120)
        self._type_filter.addItem("全部类型")
        for pt in ProjectType:
            self._type_filter.addItem(pt.value)
        self._type_filter.currentTextChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self._type_filter)

        self._status_filter = QComboBox()
        self._status_filter.setProperty("class", "input")
        self._status_filter.setMinimumWidth(120)
        self._status_filter.addItem("全部状态")
        for status in ProjectStatus:
            self._status_filter.addItem(status.value)
        self._status_filter.currentTextChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self._status_filter)

        card.layout().addWidget(filter_layout)

        # 项目网格
        self._scroll_area = MacScrollArea()
        self._grid_widget = QWidget()
        self._grid_widget.setProperty("class", "grid")
        self._grid_layout = QGridLayout(self._grid_widget)
        self._grid_layout.setSpacing(12)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._scroll_area.setWidget(self._grid_widget)
        card.layout().addWidget(self._scroll_area, 1)

        layout.addWidget(card)

    def _on_filter_changed(self):
        """过滤项目"""
        search_text = ""
        if hasattr(self, '_search_box') and self._search_box:
            search_text = self._search_box.input.text().lower()

        type_filter = self._type_filter.currentText()
        status_filter = self._status_filter.currentText()

        for project_id, card in self._project_cards.items():
            project = card.project
            matches = True

            if search_text:
                matches = (
                    search_text in project.metadata.name.lower() or
                    search_text in project.metadata.description.lower()
                )

            if matches and type_filter != "全部类型":
                matches = project.metadata.project_type.value == type_filter

            if matches and status_filter != "全部状态":
                matches = project.metadata.status.value == status_filter

            card.setVisible(matches)

    # ── 公开方法 ──────────────────────────────────────────────

    def load_projects(self):
        """加载项目列表"""
        self._project_cards.clear()
        self._clear_grid()

        if not self._project_manager:
            self._add_empty_spacer()
            return

        try:
            projects = self._project_manager.get_all_projects()
        except Exception as e:
            logger.debug(f"Failed to load projects: {e}")
            self._add_empty_spacer()
            return

        row, col = 0, 0
        for project in projects:
            card = ProjectCard(project)

            # 连接信号
            card.clicked.connect(self._emit_project_selected)
            card.edit_clicked.connect(self._emit_edit)
            card.export_clicked.connect(self._emit_export)
            card.delete_clicked.connect(self._emit_delete)

            self._grid_layout.addWidget(card, row, col)
            self._project_cards[project.id] = card

            col += 1
            if col >= 2:
                col = 0
                row += 1

        if not self._project_cards:
            self._add_empty_spacer()

    def _clear_grid(self):
        """清空网格"""
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.spacerItem():
                self._grid_layout.removeItem(item.spacerItem())

    def _add_empty_spacer(self):
        """添加空白间隔"""
        self._grid_layout.addItem(
            QSpacerItem(1, 1, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding),
            0, 0
        )

    def _emit_project_selected(self, project_id: str):
        """发射项目选中信号"""
        if self.project_selected:
            self.project_selected.emit(project_id)

    def _emit_edit(self, project_id: str):
        if self.project_edit_requested:
            self.project_edit_requested.emit(project_id)

    def _emit_export(self, project_id: str):
        if self.project_export_requested:
            self.project_export_requested.emit(project_id)

    def _emit_delete(self, project_id: str):
        if self.project_delete_requested:
            self.project_delete_requested.emit(project_id)
