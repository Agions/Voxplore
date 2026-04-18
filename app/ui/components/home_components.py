#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
首页组件 - 专业视频创作应用
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QPushButton
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QCursor

from ..pro_components import GradientButton


class QuickActionCard(QFrame):
    """快捷操作卡片"""
    clicked = Signal(str)
    
    def __init__(self, icon: str, title: str, description: str, action_id: str, parent=None):
        super().__init__(parent)
        self._action_id = action_id
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedSize(280, 120)
        self._setup_ui(icon, title, description)
        
    def _setup_ui(self, icon: str, title: str, description: str):
        self.setStyleSheet("""
            QFrame {
                background: linear-gradient(145deg, #1A1A24 0%, #16161F 100%);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 18px;
                padding: 20px;
            }
            QFrame:hover {
                border-color: rgba(124, 58, 237, 0.4);
                transform: translateY(-4px);
                box-shadow: 0 12px 32px rgba(0, 0, 0, 0.4);
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # 图标和标题行
        header = QHBoxLayout()
        
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("", 28))
        icon_label.setStyleSheet("background: transparent;")
        header.addWidget(icon_label)
        
        header.addStretch()
        
        arrow = QLabel("→")
        arrow.setFont(QFont("", 18))
        arrow.setStyleSheet("color: #6B7280; background: transparent;")
        header.addWidget(arrow)
        
        layout.addLayout(header)
        
        # 标题
        title_label = QLabel(title)
        title_label.setFont(QFont("", 16, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #FFFFFF; background: transparent;")
        layout.addWidget(title_label)
        
        # 描述
        desc_label = QLabel(description)
        desc_label.setFont(QFont("", 12))
        desc_label.setStyleSheet("color: #9CA3AF; background: transparent;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._action_id)
        super().mousePressEvent(event)


class ProjectPreviewCard(QFrame):
    """项目预览卡片"""
    clicked = Signal(str)
    
    def __init__(self, project_data: dict, parent=None):
        super().__init__(parent)
        self._project_data = project_data
        self._project_id = project_data.get("id", "")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedSize(300, 220)
        self._setup_ui()
        
    def _setup_ui(self):
        self.setStyleSheet("""
            QFrame {
                background: linear-gradient(180deg, #1A1A28 0%, #12121C 100%);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 20px;
                overflow: hidden;
            }
            QFrame:hover {
                border-color: rgba(124, 58, 237, 0.3);
                transform: translateY(-4px) scale(1.02);
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 缩略图区域
        thumbnail = QFrame()
        thumbnail.setFixedHeight(140)
        thumbnail.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #1E1E2E,
                stop:1 #2A2A3E);
        """)
        
        # 视频时长标签
        duration = QLabel("02:35")
        duration.setFont(QFont("", 10))
        duration.setStyleSheet("""
            color: white;
            background: rgba(0, 0, 0, 0.7);
            padding: 4px 8px;
            border-radius: 4px;
        """)
        duration.setParent(thumbnail)
        duration.move(220, 110)
        
        layout.addWidget(thumbnail)
        
        # 信息区域
        info = QWidget()
        info.setStyleSheet("background: transparent; padding: 16px;")
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(6)
        
        # 项目名
        name = self._project_data.get("name", "未命名项目")
        name_label = QLabel(name)
        name_label.setFont(QFont("", 14, QFont.Weight.SemiBold))
        name_label.setStyleSheet("color: #FFFFFF; background: transparent;")
        info_layout.addWidget(name_label)
        
        # 时间和状态
        meta = QHBoxLayout()
        
        time_label = QLabel("2小时前")
        time_label.setFont(QFont("", 11))
        time_label.setStyleSheet("color: #6B7280; background: transparent;")
        meta.addWidget(time_label)
        
        meta.addStretch()
        
        status = QLabel("✓ 已完成")
        status.setFont(QFont("", 11))
        status.setStyleSheet("color: #10B981; background: transparent;")
        meta.addWidget(status)
        
        info_layout.addLayout(meta)
        
        layout.addWidget(info)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._project_id)
        super().mousePressEvent(event)


class FeatureShowcase(QFrame):
    """功能展示卡片"""
    
    def __init__(self, icon: str, title: str, features: list, parent=None):
        super().__init__(parent)
        self._setup_ui(icon, title, features)
        
    def _setup_ui(self, icon: str, title: str, features: list):
        self.setFixedSize(380, 280)
        self.setStyleSheet("""
            QFrame {
                background: rgba(26, 26, 40, 0.6);
                backdrop-filter: blur(20px);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 24px;
                padding: 24px;
            }
            QFrame:hover {
                border-color: rgba(124, 58, 237, 0.2);
                box-shadow: 0 0 40px rgba(124, 58, 237, 0.1);
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # 头部
        header = QHBoxLayout()
        
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("", 32))
        icon_label.setStyleSheet("background: transparent;")
        header.addWidget(icon_label)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("", 20, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #FFFFFF; background: transparent;")
        header.addWidget(title_label)
        
        header.addStretch()
        
        layout.addLayout(header)
        
        # 功能列表
        for feature in features:
            feature_item = QHBoxLayout()
            feature_item.setSpacing(12)
            
            check = QLabel("✓")
            check.setFont(QFont("", 14))
            check.setStyleSheet("color: #10B981; background: transparent;")
            feature_item.addWidget(check)
            
            feature_label = QLabel(feature)
            feature_label.setFont(QFont("", 13))
            feature_label.setStyleSheet("color: #D1D5DB; background: transparent;")
            feature_item.addWidget(feature_label)
            
            feature_item.addStretch()
            
            layout.addLayout(feature_item)
        
        layout.addStretch()


class AIPowerBadge(QFrame):
    """AI能力徽章"""
    
    def __init__(self, title: str, description: str, parent=None):
        super().__init__(parent)
        self._setup_ui(title, description)
        
    def _setup_ui(self, title: str, description: str):
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(124, 58, 237, 0.15),
                    stop:1 rgba(6, 182, 212, 0.15));
                border: 1px solid rgba(124, 58, 237, 0.3);
                border-radius: 12px;
                padding: 16px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        title_label = QLabel(f"⚡ {title}")
        title_label.setFont(QFont("", 14, QFont.Weight.SemiBold))
        title_label.setStyleSheet("color: #A78BFA; background: transparent;")
        layout.addWidget(title_label)
        
        desc_label = QLabel(description)
        desc_label.setFont(QFont("", 12))
        desc_label.setStyleSheet("color: #9CA3AF; background: transparent;")
        layout.addWidget(desc_label)


class WelcomeHeader(QWidget):
    """欢迎头部组件"""
    
    def __init__(self, user_name: str = "", parent=None):
        super().__init__(parent)
        self._setup_ui(user_name)
        
    def _setup_ui(self, user_name: str):
        self.setMinimumHeight(200)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 32, 48, 32)
        layout.setSpacing(16)
        
        # 欢迎文字
        welcome = QLabel(f"欢迎回来{', ' + user_name if user_name else ''} 👋")
        welcome.setFont(QFont("", 14))
        welcome.setStyleSheet("color: #9CA3AF; background: transparent;")
        layout.addWidget(welcome)
        
        # 主标题
        title = QLabel("Voxplore")
        title.setFont(QFont("", 42, QFont.Weight.Bold))
        title.setStyleSheet("""
            color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #A78BFA,
                stop:0.5 #8B5CF6,
                stop:1 #7C3AED);
            background: transparent;
        """)
        layout.addWidget(title)
        
        # 副标题
        subtitle = QLabel("AI 驱动的专业视频创作平台")
        subtitle.setFont(QFont("", 18))
        subtitle.setStyleSheet("color: #D1D5DB; background: transparent;")
        layout.addWidget(subtitle)
        
        # 快捷操作
        actions = QHBoxLayout()
        actions.setSpacing(16)
        
        new_btn = GradientButton("➕ 新建项目")
        new_btn.setStyleSheet(new_btn.styleSheet() + " padding: 14px 28px;")
        actions.addWidget(new_btn)
        
        import_btn = QPushButton("📂 导入素材")
        import_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        import_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 14px;
                padding: 14px 28px;
                color: #D1D5DB;
                font-size: 14px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
                border-color: rgba(255, 255, 255, 0.2);
            }
        """)
        actions.addWidget(import_btn)
        
        layout.addLayout(actions)
        
        layout.addStretch()


class StatsRow(QWidget):
    """统计数据行"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(24)
        
        # 项目数
        projects_card = self._create_stat_card("🎬", "128", "项目总数")
        layout.addWidget(projects_card)
        
        # AI 创作
        ai_card = self._create_stat_card("🤖", "856", "AI 创作")
        layout.addWidget(ai_card)
        
        # 导出视频
        exports_card = self._create_stat_card("📤", "234", "已导出")
        layout.addWidget(exports_card)
        
        # 使用时长
        time_card = self._create_stat_card("⏱️", "48h", "创作时长")
        layout.addWidget(time_card)
        
        layout.addStretch()
        
    def _create_stat_card(self, icon: str, value: str, label: str) -> QFrame:
        card = QFrame()
        card.setFixedSize(180, 100)
        card.setStyleSheet("""
            QFrame {
                background: linear-gradient(145deg, #1A1A24 0%, #16161F 100%);
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 16px;
                padding: 16px;
            }
            QFrame:hover {
                border-color: rgba(124, 58, 237, 0.3);
                transform: translateY(-2px);
            }
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(8)
        
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("", 20))
        icon_label.setStyleSheet("background: transparent;")
        layout.addWidget(icon_label)
        
        value_label = QLabel(value)
        value_label.setFont(QFont("", 28, QFont.Weight.Bold))
        value_label.setStyleSheet("color: #FFFFFF; background: transparent;")
        layout.addWidget(value_label)
        
        label_widget = QLabel(label)
        label_widget.setFont(QFont("", 12))
        label_widget.setStyleSheet("color: #6B7280; background: transparent;")
        layout.addWidget(label_widget)
        
        return card
