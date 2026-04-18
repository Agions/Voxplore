"""
首次使用引导 - 欢迎页面
介绍 Voxplore 的核心功能
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QPainter, QLinearGradient, QColor

# 色彩系统
COLORS = {
    "primary": "#6366F1",
    "primary_end": "#8B5CF6",
    "primary_light": "#818CF8",
    "accent": "#06B6D4",
    "background": "#0A0A0F",
    "surface": "#12121A",
    "card": "#1A1A24",
    "card_elevated": "#22222E",
    "text": "#E6EDF3",
    "text_secondary": "#C9D1D9",
    "text_tertiary": "#8B949E",
    "border": "#30363D",
    "success": "#238636",
}


class GradientLogoWidget(QWidget):
    """渐变 Logo 组件"""
    
    def __init__(self, size: int = 100, parent=None):
        super().__init__(parent)
        self.logo_size = size
        self.setFixedSize(size, size)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center = self.rect().center()
        radius = self.logo_size // 2 - 5
        
        # 渐变背景
        gradient = QLinearGradient(
            center.x() - radius, center.y() - radius,
            center.x() + radius, center.y() + radius
        )
        gradient.setColorAt(0, QColor(COLORS["primary"]))
        gradient.setColorAt(0.5, QColor(COLORS["primary_end"]))
        gradient.setColorAt(1, QColor(COLORS["accent"]))
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawEllipse(center, radius, radius)
        
        # Logo 文字
        painter.setPen(QColor("#FFFFFF"))
        font = QFont("Arial", int(radius * 0.45), QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignCenter,
            "CF"
        )


class FeatureCard(QWidget):
    """功能介绍卡片"""
    
    def __init__(self, icon: str, title: str, description: str, parent=None):
        super().__init__(parent)
        self._icon = icon
        self._title = title
        self._description = description
        self._setup_ui()
        
    def _setup_ui(self):
        self.setFixedHeight(100)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS["card"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 12px;
                padding: 16px;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)
        
        # 图标区域
        icon_label = QLabel(self._icon)
        icon_label.setStyleSheet("font-size: 28px; background: transparent;")
        layout.addWidget(icon_label)
        
        # 文字内容
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        
        title_label = QLabel(self._title)
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setWeight(QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet(f"color: {COLORS['text']}; background: transparent;")
        text_layout.addWidget(title_label)
        
        desc_label = QLabel(self._description)
        desc_label.setWordWrap(True)
        desc_font = QFont()
        desc_label.setFont(desc_font)
        desc_label.setStyleSheet(f"color: {COLORS['text_tertiary']}; background: transparent;")
        text_layout.addWidget(desc_label)
        
        layout.addLayout(text_layout)
        layout.addStretch()
        
    def enterEvent(self, event):
        """鼠标悬停效果"""
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS["card_elevated"]};
                border: 1px solid {COLORS["primary"]};
                border-radius: 12px;
                padding: 16px;
            }}
        """)
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        """鼠标离开效果"""
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS["card"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 12px;
                padding: 16px;
            }}
        """)
        super().leaveEvent(event)


class WelcomeScreen(QWidget):
    """欢迎页面 - 首次使用引导的起始页"""
    
    # 信号定义
    get_started = Signal()  # 开始使用信号
    skip = Signal()  # 跳过信号
    
    def __init__(self, app_name: str = "Voxplore", version: str = "v2.0.0", parent=None):
        super().__init__(parent)
        self._app_name = app_name
        self._version = version
        self._setup_ui()
        
    def _setup_ui(self):
        """设置 UI"""
        self.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {COLORS["background"]},
                    stop:0.5 {COLORS["surface"]},
                    stop:1 {COLORS["background"]});
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # 顶部 Logo 和标题
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.setSpacing(16)
        
        # Logo
        self.logo = GradientLogoWidget(80)
        header_layout.addWidget(self.logo)
        
        # 应用名称
        name_label = QLabel(self._app_name)
        name_font = QFont()
        name_font.setPointSize(28)
        name_font.setWeight(QFont.Weight.Bold)
        name_label.setFont(name_font)
        name_label.setStyleSheet(f"color: {COLORS['text']}; background: transparent;")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(name_label)
        
        # 副标题
        subtitle = QLabel("智能视频创作平台")
        subtitle_font = QFont()
        subtitle_font.setPointSize(14)
        subtitle.setFont(subtitle_font)
        subtitle.setStyleSheet(f"color: {COLORS['text_tertiary']}; background: transparent;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(subtitle)
        
        layout.addWidget(header_widget)
        
        # 功能介绍区域
        features_label = QLabel("核心功能")
        features_font = QFont()
        features_font.setPointSize(16)
        features_font.setWeight(QFont.Weight.Bold)
        features_label.setFont(features_font)
        features_label.setStyleSheet(f"color: {COLORS['text']}; background: transparent;")
        layout.addWidget(features_label)
        
        # 功能卡片列表
        features_layout = QVBoxLayout()
        features_layout.setSpacing(12)
        
        self.features = [
            ("🎬", "智能剪辑", "AI 自动识别精彩片段，智能剪辑"),
            ("📝", "脚本生成", "根据视频内容自动生成解说脚本"),
            ("🎤", "语音合成", "多风格 AI 配音，支持多种音色"),
            ("📤", "多格式导出", "支持 Premiere、剪映、DaVinci 等主流软件"),
        ]
        
        for icon, title, desc in self.features:
            card = FeatureCard(icon, title, desc)
            features_layout.addWidget(card)
            
        layout.addLayout(features_layout)
        
        layout.addStretch()
        
        # 按钮区域
        button_layout = QVBoxLayout()
        button_layout.setSpacing(12)
        
        # 开始使用按钮
        self.start_btn = QPushButton("开始使用")
        self.start_btn.setCursor(Qt.CursorShape.PointingHand)
        self.start_btn.setFixedHeight(48)
        self.start_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {COLORS["primary"]},
                    stop:1 {COLORS["primary_end"]});
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 15px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {COLORS["primary_light"]},
                    stop:1 {COLORS["primary_end"]});
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4F46E5,
                    stop:1 #7C3AED);
            }}
        """)
        self.start_btn.clicked.connect(self.get_started.emit)
        button_layout.addWidget(self.start_btn)
        
        # 跳过按钮
        self.skip_btn = QPushButton("暂时跳过")
        self.skip_btn.setCursor(Qt.CursorShape.PointingHand)
        self.skip_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLORS["text_tertiary"]};
                border: none;
                font-size: 13px;
            }}
            QPushButton:hover {{
                color: {COLORS["text_secondary"]};
            }}
        """)
        self.skip_btn.clicked.connect(self.skip.emit)
        button_layout.addWidget(self.skip_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        layout.addLayout(button_layout)
        
        # 版本信息
        version_label = QLabel(f"版本 {self._version}")
        version_label.setStyleSheet(f"""
            color: {COLORS["text_tertiary"]};
            font-size: 11px;
            background: transparent;
        """)
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)
        
    def animate_in(self):
        """入场动画"""
        self.setWindowOpacity(0)
        animation = QPropertyAnimation(self, b"windowOpacity")
        animation.setDuration(500)
        animation.setStartValue(0)
        animation.setEndValue(1)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        animation.start()
