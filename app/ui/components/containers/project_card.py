#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
项目管理页面 - 项目卡片组件
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QCursor


class ProjectCard(QFrame):
    """项目卡片 - 显示项目信息"""
    
    clicked = Signal(str)  # project_id
    deleted = Signal(str)  # project_id
    
    def __init__(self, project_data: dict, parent=None):
        super().__init__(parent)
        self._project_data = project_data
        self._project_id = project_data.get("id", "")
        
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedSize(280, 220)
        self.setObjectName("projectCard")
        self._setup_style()
        self._setup_ui()
        
    def _setup_style(self):
        """设置样式"""
        self.setStyleSheet("""
            #projectCard {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1A1A24, stop:1 #12121A);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
            }
            #projectCard:hover {
                border-color: #6366F1;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #22222E, stop:1 #1A1A24);
            }
        """)
        
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # 缩略图
        thumbnail = self._create_thumbnail()
        layout.addWidget(thumbnail)
        
        # 项目信息
        info = self._create_info()
        layout.addWidget(info)
        
        layout.addStretch()
        
    def _create_thumbnail(self) -> QFrame:
        """创建缩略图"""
        frame = QFrame()
        frame.setFixedSize(248, 120)
        frame.setStyleSheet("""
            QFrame {
                background: #0A0A0F;
                border-radius: 12px;
            }
        """)
        
        # 尝试加载缩略图
        thumbnail_path = self._project_data.get("thumbnail_path")
        if thumbnail_path:
            # 实际应该加载图片
            pass
            
        # 放置图标
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        
        icon_label = QLabel("🎬")
        icon_label.setFont(QFont("", 36))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("background: transparent;")
        layout.addWidget(icon_label)
        
        return frame
        
    def _create_info(self) -> QWidget:
        """创建项目信息"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # 项目名称
        name = self._project_data.get("name", "未命名项目")
        name_label = QLabel(name)
        name_label.setFont(QFont("", 14, QFont.Weight.Bold))
        name_label.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(name_label)
        
        # 描述
        description = self._project_data.get("description", "")
        if description:
            desc_label = QLabel(description[:50] + "..." if len(description) > 50 else description)
            desc_label.setFont(QFont("", 12))
            desc_label.setStyleSheet("color: #71717A;")
            layout.addWidget(desc_label)
        
        # 时间信息
        time_info = self._project_data.get("modified_at", "")
        if time_info:
            time_label = QLabel(f"修改于: {time_info}")
            time_label.setFont(QFont("", 11))
            time_label.setStyleSheet("color: #52525B;")
            layout.addWidget(time_label)
            
        return widget
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._project_id)
        super().mousePressEvent(event)


class ProjectCardCompact(QFrame):
    """紧凑型项目卡片 - 列表视图"""
    
    clicked = Signal(str)
    
    def __init__(self, project_data: dict, parent=None):
        super().__init__(parent)
        self._project_data = project_data
        self._project_id = project_data.get("id", "")
        
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMinimumHeight(60)
        self.setObjectName("projectCardCompact")
        self._setup_style()
        self._setup_ui()
        
    def _setup_style(self):
        self.setStyleSheet("""
            #projectCardCompact {
                background: transparent;
                border-bottom: 1px solid rgba(255, 255, 255, 0.06);
            }
            #projectCardCompact:hover {
                background: rgba(99, 102, 241, 0.1);
            }
        """)
        
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)
        
        # 图标
        icon = QLabel("🎬")
        icon.setFont(QFont("", 20))
        layout.addWidget(icon)
        
        # 信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        name = self._project_data.get("name", "未命名")
        name_label = QLabel(name)
        name_label.setFont(QFont("", 13, QFont.Weight.Medium))
        name_label.setStyleSheet("color: #FFFFFF;")
        info_layout.addWidget(name_label)
        
        desc = self._project_data.get("description", "")
        if desc:
            desc_label = QLabel(desc[:40])
            desc_label.setFont(QFont("", 11))
            desc_label.setStyleSheet("color: #71717A;")
            info_layout.addWidget(desc_label)
            
        layout.addLayout(info_layout)
        layout.addStretch()
        
        # 箭头
        arrow = QLabel("›")
        arrow.setFont(QFont("", 18))
        arrow.setStyleSheet("color: #52525B;")
        layout.addWidget(arrow)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._project_id)
        super().mousePressEvent(event)
