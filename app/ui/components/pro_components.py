#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
专业 UI 组件库
视频创作应用专用组件
"""

from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QFrame, QVBoxLayout, 
    QHBoxLayout, QLineEdit
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QCursor, QPainter, QLinearGradient, QColor


class GradientButton(QPushButton):
    """渐变按钮 - 专业设计"""
    
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setObjectName("gradientButton")
        self._setup_style()
        
    def _setup_style(self):
        self.setStyleSheet("""
            #gradientButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7C3AED,
                    stop:0.5 #8B5CF6,
                    stop:1 #A855F7);
                color: white;
                border: none;
                border-radius: 12px;
                padding: 14px 28px;
                font-weight: 600;
                font-size: 14px;
                box-shadow: 0 4px 14px rgba(124, 58, 237, 0.35);
            }
            #gradientButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #8B5CF6,
                    stop:0.5 #A78BFA,
                    stop:1 #C084FC);
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(124, 58, 237, 0.5);
            }
            #gradientButton:pressed {
                transform: translateY(0);
                box-shadow: 0 2px 8px rgba(124, 58, 237, 0.3);
            }
        """)


class GlassCard(QFrame):
    """玻璃拟态卡片"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("glassCard")
        self.setStyleSheet("""
            #glassCard {
                background: rgba(28, 28, 40, 0.7);
                backdrop-filter: blur(20px);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 20px;
                padding: 20px;
            }
            #glassCard:hover {
                border-color: rgba(124, 58, 237, 0.3);
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            }
        """)


class StatCard(QFrame):
    """统计卡片 - 显示指标"""
    
    def __init__(self, icon: str, value: str, label: str, parent=None):
        super().__init__(parent)
        self._setup_ui(icon, value, label)
        
    def _setup_ui(self, icon: str, value: str, label: str):
        self.setFixedSize(160, 100)
        self.setStyleSheet("""
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
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # 图标
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 24px; background: transparent;")
        layout.addWidget(icon_label)
        
        # 值
        value_label = QLabel(value)
        value_label.setFont(QFont("", 24, QFont.Weight.Bold))
        value_label.setStyleSheet("color: #FFFFFF; background: transparent;")
        layout.addWidget(value_label)
        
        # 标签
        label_widget = QLabel(label)
        label_widget.setFont(QFont("", 12))
        label_widget.setStyleSheet("color: #A1A1AA; background: transparent;")
        layout.addWidget(label_widget)


class ProgressRing(QWidget):
    """环形进度条"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self._max = 100
        self.setFixedSize(80, 80)
        
    def setValue(self, value: int):
        self._value = value
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        radius = min(w, h) // 2 - 8
        
        # 背景圆
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(40, 40, 55))
        painter.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)
        
        # 进度圆
        if self._value > 0:
            gradient = QLinearGradient(cx - radius, cy - radius, cx + radius, cy + radius)
            gradient.setColorAt(0, QColor("#7C3AED"))
            gradient.setColorAt(1, QColor("#A855F7"))
            
            painter.setPen(QColor("#7C3AED"))
            painter.setBrush(gradient)
            
            # 绘制弧形
            angle = 360 * self._value / self._max
            rect_x = cx - radius
            rect_y = cy - radius
            painter.drawPie(rect_x, rect_y, radius * 2, radius * 2, 
                          90 * 16, int(angle * 16))


class LoadingOverlay(QFrame):
    """加载遮罩层"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        
    def _setup_ui(self):
        self.setObjectName("loadingOverlay")
        self.setStyleSheet("""
            #loadingOverlay {
                background: rgba(10, 10, 15, 0.85);
                border-radius: 16px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)
        
        # 加载动画
        self.spinner = QLabel("◌")
        self.spinner.setFont(QFont("", 36))
        self.spinner.setStyleSheet("""
            color: #7C3AED;
            background: transparent;
        """)
        layout.addWidget(self.spinner)
        
        # 文本
        self.text_label = QLabel("加载中...")
        self.text_label.setFont(QFont("", 14))
        self.text_label.setStyleSheet("color: #A1A1AA; background: transparent;")
        layout.addWidget(self.text_label)
        
        # 启动旋转动画
        self._start_rotation()
        
    def _start_rotation(self):
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._timer.start(50)
        
    def _rotate(self):
        self._angle = (self._angle + 10) % 360
        self.spinner.setTransform(self.spinner.transform().rotate(10))
        
    def setText(self, text: str):
        self.text_label.setText(text)


class StepIndicator(QWidget):
    """步骤指示器"""
    
    stepChanged = Signal(int)
    
    def __init__(self, steps: list, parent=None):
        super().__init__(parent)
        self._steps = steps
        self._current_step = 0
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        for i, step in enumerate(self._steps):
            # 步骤节点
            node = QFrame()
            node.setFixedSize(32, 32)
            node.setStyleSheet("""
                QFrame {
                    background: #7C3AED;
                    border-radius: 16px;
                    color: white;
                }
            """)
            node_layout = QVBoxLayout(node)
            node_layout.setContentsMargins(0, 0, 0, 0)
            node_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            num_label = QLabel(str(i + 1))
            num_label.setStyleSheet("background: transparent; color: white; font-weight: bold;")
            node_layout.addWidget(num_label)
            
            layout.addWidget(node)
            
            # 连接线 (除了最后一个)
            if i < len(self._steps) - 1:
                line = QFrame()
                line.setFixedHeight(3)
                line.setStyleSheet("""
                    QFrame {
                        background: #3F3F5A;
                        border-radius: 2px;
                    }
                """)
                layout.addWidget(line, 1)
                
        layout.addStretch()
        
    def setCurrentStep(self, step: int):
        self._current_step = step
        self.stepChanged.emit(step)
        self.update()


class SearchBar(QLineEdit):
    """专业搜索栏"""
    
    def __init__(self, placeholder: str = "搜索...", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setObjectName("searchBar")
        self.setStyleSheet("""
            #searchBar {
                background: rgba(20, 20, 30, 0.9);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                padding: 12px 16px 12px 40px;
                color: #FAFAFA;
                font-size: 14px;
            }
            #searchBar:hover {
                border-color: rgba(255, 255, 255, 0.15);
            }
            #searchBar:focus {
                border-color: #7C3AED;
                box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.15);
            }
            #searchBar::placeholder {
                color: #6B7280;
            }
        """)
        self.setMinimumHeight(44)


class TabBar(QWidget):
    """专业标签栏"""
    
    tabChanged = Signal(int)
    
    def __init__(self, tabs: list, parent=None):
        super().__init__(parent)
        self._tabs = tabs
        self._active_index = 0
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        for i, tab in enumerate(self._tabs):
            btn = QPushButton(tab)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setCheckable(True)
            btn.setObjectName(f"tab_{i}")
            
            if i == 0:
                btn.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 rgba(124, 58, 237, 0.2),
                            stop:1 rgba(168, 85, 247, 0.2));
                        border: 1px solid rgba(124, 58, 237, 0.4);
                        border-radius: 10px;
                        padding: 10px 20px;
                        color: #FFFFFF;
                        font-weight: 600;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        border: none;
                        border-radius: 10px;
                        padding: 10px 20px;
                        color: #A1A1AA;
                    }
                    QPushButton:hover {
                        background: rgba(255, 255, 255, 0.05);
                        color: #FFFFFF;
                    }
                """)
            
            btn.clicked.connect(lambda checked, idx=i: self._on_tab_clicked(idx))
            layout.addWidget(btn)
            
        layout.addStretch()
        
    def _on_tab_clicked(self, index: int):
        self._active_index = index
        self.tabChanged.emit(index)
        # 更新样式
        for i in range(self.layout().count() - 1):  # 不包括 stretch
            btn = self.layout().itemAt(i).widget()
            if isinstance(btn, QPushButton):
                if i == index:
                    btn.setStyleSheet("""
                        QPushButton {
                            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 rgba(124, 58, 237, 0.2),
                                stop:1 rgba(168, 85, 247, 0.2));
                            border: 1px solid rgba(124, 58, 237, 0.4);
                            border-radius: 10px;
                            padding: 10px 20px;
                            color: #FFFFFF;
                            font-weight: 600;
                        }
                    """)
                else:
                    btn.setStyleSheet("""
                        QPushButton {
                            background: transparent;
                            border: none;
                            border-radius: 10px;
                            padding: 10px 20px;
                            color: #A1A1AA;
                        }
                        QPushButton:hover {
                            background: rgba(255, 255, 255, 0.05);
                            color: #FFFFFF;
                        }
                    """)


class Badge(QFrame):
    """徽章/标签"""
    
    def __init__(self, text: str, color: str = "#7C3AED", parent=None):
        super().__init__(parent)
        self._setup_ui(text, color)
        
    def _setup_ui(self, text: str, color: str):
        self.setStyleSheet(f"""
            QFrame {{
                background: {color}22;
                border: 1px solid {color}44;
                border-radius: 6px;
                padding: 4px 8px;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)
        
        label = QLabel(text)
        label.setFont(QFont("", 11))
        label.setStyleSheet(f"color: {color}; background: transparent;")
        layout.addWidget(label)
