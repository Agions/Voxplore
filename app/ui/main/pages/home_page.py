#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Voxplore 首页 - 模板选择式设计
简洁、美观、以创作流程为核心
"""

from typing import List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QFrame, QScrollArea, QPushButton
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QCursor

from .base_page import BasePage
from app.ui.components.empty_state import MacEmptyStateV2
from app.ui.components.design_system import Colors


class TemplateCard(QFrame):
    """模板卡片 - 精美设计"""
    clicked = Signal(str)  # template_id

    def __init__(self, template_id: str, icon: str, title: str,
                 description: str, parent=None):
        super().__init__(parent)
        self._template_id = template_id
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedSize(240, 200)
        self.setObjectName("templateCard")
        self.setStyleSheet("""
            #templateCard {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #161B22, stop:1 #0D1117);
                border: 1px solid #21262D;
                border-radius: 16px;
            }
            #templateCard:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1C2128, stop:1 #161B22);
                border-color: #388BFD;
                border-width: 2px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(12)

        # 图标容器 - 带背景
        icon_container = QFrame()
        icon_container.setFixedSize(64, 64)
        icon_container.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #388BFD, stop:1 #79C0FF);
                border-radius: 14px;
            }
        """)
        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)

        icon_label = QLabel(icon)
        icon_label.setFont(QFont("", 32))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_layout.addWidget(icon_label)

        layout.addWidget(icon_container)
        layout.addSpacing(4)

        # 标题
        title_label = QLabel(title)
        title_label.setFont(QFont("", 16, QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {Colors.TextPrimary};")
        layout.addWidget(title_label)

        # 描述
        desc_label = QLabel(description)
        desc_label.setFont(QFont("", 12))
        desc_label.setStyleSheet(f"color: {Colors.TextSecondary}; line-height: 1.4;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        layout.addStretch()

        # 底部提示
        hint_label = QLabel("点击开始 →")
        hint_label.setFont(QFont("", 11))
        hint_label.setStyleSheet(f"color: {Colors.TextMuted};")
        layout.addWidget(hint_label)

    def mousePressEvent(self, event):
        self.clicked.emit(self._template_id)
        super().mousePressEvent(event)


class RecentProjectItem(QFrame):
    """最近项目条目 - 优化设计"""
    clicked = Signal(str)

    def __init__(self, name: str, path: str, date: str = "", parent=None):
        super().__init__(parent)
        self._path = path
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedHeight(56)
        self.setStyleSheet("""
            QFrame {
                background: #161B22;
                border: 1px solid #21262D;
                border-radius: 10px;
                padding: 8px 16px;
            }
            QFrame:hover {
                background: #1C2128;
                border-color: #388BFD;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(16)

        # 图标
        icon = QLabel("📄")
        icon.setFont(QFont("", 20))
        layout.addWidget(icon)

        # 项目信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        name_label = QLabel(name)
        name_label.setFont(QFont("", 14, QFont.Weight.Bold))
        name_label.setStyleSheet(f"color: {Colors.TextPrimary};")
        info_layout.addWidget(name_label)

        # 路径显示（简化）
        from pathlib import Path
        path_label = QLabel(str(Path(path).parent.name))
        path_label.setStyleSheet(f"color: {Colors.TextMuted}; font-size: 12px;")
        info_layout.addWidget(path_label)

        layout.addLayout(info_layout)
        layout.addStretch()

        # 日期标签
        if date:
            date_label = QLabel(date)
            date_label.setFont(QFont("", 12))
            date_label.setStyleSheet(f"color: {Colors.TextSecondary};")
            layout.addWidget(date_label)

        # 箭头图标
        arrow = QLabel("→")
        arrow.setFont(QFont("", 16))
        arrow.setStyleSheet(f"color: {Colors.TextMuted};")
        layout.addWidget(arrow)

    def mousePressEvent(self, event):
        self.clicked.emit(self._path)
        super().mousePressEvent(event)


class HomePage(BasePage):
    """首页 - 模板选择式设计"""

    # 信号
    template_selected = Signal(str)   # template_id
    project_opened = Signal(str)      # project_path

    TEMPLATES = [
        ("emotional_monologue", "🎭", "第一人称解说",
         "上传视频，AI 代入主角视角，一键生成配音解说"),
    ]

    def __init__(self, application):
        super().__init__("home", "首页", application)
        self.logger = application.get_service(type(application.logger))

    def initialize(self) -> bool:
        try:
            self.logger.info("初始化首页页面")
            return True
        except Exception as e:
            self.logger.error(f"初始化首页失败: {e}")
            return False

    def create_content(self) -> None:
        """创建首页内容"""
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background: {Colors.BgBase}; }}")
        content = QWidget()
        content.setStyleSheet(f"background: {Colors.BgBase};")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(48, 40, 48, 40)
        layout.setSpacing(0)

        # ── 标题区 ──
        header = self._create_header()
        layout.addWidget(header)
        layout.addSpacing(32)

        # ── 模板网格 ──
        templates_label = QLabel("选择创作模板")
        templates_label.setFont(QFont("", 14, QFont.Weight.Bold))
        templates_label.setStyleSheet(f"color: {Colors.TextSecondary}; margin-bottom: 4px;")
        layout.addWidget(templates_label)
        layout.addSpacing(16)

        grid = self._create_template_grid()
        layout.addLayout(grid)
        layout.addSpacing(40)

        # ── 分隔线 ──
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {Colors.BorderDefault};")
        layout.addWidget(line)
        layout.addSpacing(24)

        # ── 最近项目 ──
        recent_section = self._create_recent_section()
        layout.addWidget(recent_section)

        layout.addStretch()

        scroll.setWidget(content)
        self.main_layout.addWidget(scroll)

    def _create_header(self) -> QWidget:
        """标题区 - 优化设计"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # 主标题
        title = QLabel("欢迎使用 Voxplore")
        title.setFont(QFont("", 32, QFont.Weight.Bold))
        title.setStyleSheet("""
            color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #F0F6FC, stop:1 #C9D1D9);
        """)
        layout.addWidget(title)

        # 副标题
        subtitle = QLabel("AI 驱动的专业视频创作工具")
        subtitle.setFont(QFont("", 18))
        subtitle.setStyleSheet(f"color: {Colors.TextSecondary};")
        layout.addWidget(subtitle)

        # 分隔线
        layout.addSpacing(8)
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 transparent, stop:0.5 oklch(0.24 0.01 250), stop:1 transparent); max-height: 1px;")
        layout.addWidget(separator)

        return widget

    def _create_template_grid(self) -> QGridLayout:
        """模板卡片网格"""
        grid = QGridLayout()
        grid.setSpacing(16)

        for i, (tid, icon, title, desc) in enumerate(self.TEMPLATES):
            card = TemplateCard(tid, icon, title, desc)
            card.clicked.connect(self._on_template_clicked)
            row = i // 3
            col = i % 3
            grid.addWidget(card, row, col)

        return grid

    def _create_recent_section(self) -> QWidget:
        """最近项目区"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        label = QLabel("最近项目")
        label.setFont(QFont("", 16, QFont.Weight.Bold))
        label.setStyleSheet(f"color: {Colors.TextPrimary};")
        header_row.addWidget(label)
        header_row.addStretch()

        # 查看全部按钮
        view_all_btn = QPushButton("查看全部 →")
        view_all_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {Colors.Primary};
                border: none;
                font-size: 14px;
                font-weight: 600;
                padding: 4px 8px;
            }}
            QPushButton:hover {{
                color: {Colors.PrimaryHover};
                text-decoration: underline;
            }}
        """)
        view_all_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        view_all_btn.clicked.connect(self._on_view_all_projects)
        header_row.addWidget(view_all_btn)
        layout.addLayout(header_row)

        # 最近项目列表
        recent = self._get_recent_projects()
        if recent:
            for name, path, date in recent[:5]:
                item = RecentProjectItem(name, path, date)
                item.clicked.connect(self._on_open_recent)
                layout.addWidget(item)
        else:
            # 空状态 - 使用统一组件 MacEmptyStateV2
            empty_state = MacEmptyStateV2(
                icon_type="projects",
                title="还没有项目",
                description="选择上方的模板开始创作吧 ✨",
            )
            layout.addWidget(empty_state)

        return widget

    def _get_recent_projects(self) -> List:
        """获取最近项目"""
        try:
            config_manager = self.application.get_service_by_name("config_manager")
            if config_manager:
                files = config_manager.get_value("recent_files", [])
                if files:
                    from pathlib import Path
                    return [
                        (Path(f).stem, f, "")
                        for f in files[:5]
                        if isinstance(f, str)
                    ]
        except PermissionError as e:
            self.logger.warning(f"Permission denied accessing templates: {e}")
        except Exception as e:
            self.logger.debug(f"Template loading error: {e}")
        return []

    def _on_template_clicked(self, template_id: str):
        """模板点击处理"""
        self.logger.info(f"选择模板: {template_id}")
        self.template_selected.emit(template_id)

        if not hasattr(self, 'application'):
            return

        main_window = self.application.get_service_by_name("main_window")
        if not main_window or not hasattr(main_window, 'switch_to_page'):
            return

        from app.ui.main.main_window import PageType

        # 根据模板类型跳转到对应页面
        # 统一跳转到 AI 创作页面
        main_window.switch_to_page(PageType.AI_VIDEO_CREATOR)

    def _on_open_recent(self, path: str):
        """打开最近项目"""
        self.logger.info(f"打开最近项目: {path}")
        self.project_opened.emit(path)

        # 切换到项目编辑页面
        if hasattr(self, 'application'):
            main_window = self.application.get_service_by_name("main_window")
            if main_window and hasattr(main_window, 'switch_to_page'):
                from app.ui.main.main_window import PageType
                main_window.switch_to_page(PageType.VIDEO_EDITOR)

    def _on_view_all_projects(self):
        """查看全部项目"""
        self.logger.info("切换到项目管理页面")
        if hasattr(self, 'application'):
            main_window = self.application.get_service_by_name("main_window")
            if main_window and hasattr(main_window, 'switch_to_page'):
                from app.ui.main.main_window import PageType
                main_window.switch_to_page(PageType.PROJECTS)

    def on_activated(self) -> None:
        """页面激活"""
        # 刷新最近项目列表
        self._load_recent_projects()
        self._load_templates()

    def on_deactivated(self) -> None:
        """页面停用"""
        # 保存页面状态
        self._save_page_state()
