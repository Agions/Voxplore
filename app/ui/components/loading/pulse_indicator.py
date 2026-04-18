#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
脉冲动画指示器组件 (Pulse Indicator)
用于显示加载状态的脉冲动画效果
"""

from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout, 
    QSizePolicy
)
from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, 
    QPoint
)
from PySide6.QtGui import QPainter, QColor, QPen, QBrush


class PulseIndicator(QFrame):
    """
    脉冲动画指示器
    显示加载中的脉冲效果
    """
    
    def __init__(self, size=50, color=None, parent=None):
        super().__init__(parent)
        self._size = size
        self._color = color or QColor(99, 102, 241)  # 默认使用主题色
        self._pulse_radius = 0
        self._max_radius = size // 2
        self._animation_phase = 0
        self._dots = []
        self._init_ui()
    
    def _init_ui(self):
        self.setFixedSize(self._size, self._size)
        
        # 启动脉冲动画
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_pulse)
        self._timer.start(50)
        
        # 创建中心点
        self._center_dot = QLabel("●", self)
        self._center_dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._center_dot.setStyleSheet(f"color: {self._color.name()}; font-size: {self._size//3}px;")
        self._center_dot.setFixedSize(self._size, self._size)
    
    def _update_pulse(self):
        self._animation_phase += 0.1
        if self._animation_phase > 2 * 3.14159:
            self._animation_phase = 0
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center = self.rect().center()
        
        # 绘制脉冲圆环
        pulse_opacity = (1 - self._animation_phase / (2 * 3.14159)) * 0.5
        radius = self._max_radius * (self._animation_phase / (2 * 3.14159))
        
        # 外圈脉冲
        pen = QPen(QColor(self._color.red(), self._color.green(), self._color.blue(), int(255 * pulse_opacity)))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawEllipse(center, int(radius), int(radius))
        
        # 第二层脉冲
        if radius > self._max_radius * 0.5:
            inner_pulse_opacity = pulse_opacity * 0.6
            pen2 = QPen(QColor(self._color.red(), self._color.green(), self._color.blue(), int(255 * inner_pulse_opacity)))
            pen2.setWidth(2)
            painter.setPen(pen2)
            painter.drawEllipse(center, int(radius * 0.6), int(radius * 0.6))


class SpinnerIndicator(QFrame):
    """
    旋转加载指示器
    显示旋转的加载动画
    """
    
    def __init__(self, size=40, color=None, parent=None):
        super().__init__(parent)
        self._size = size
        self._color = color or QColor(99, 102, 241)
        self._rotation = 0
        self._init_ui()
    
    def _init_ui(self):
        self.setFixedSize(self._size, self._size)
        
        # 启动旋转动画
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_rotation)
        self._timer.start(30)
    
    def _update_rotation(self):
        self._rotation += 10
        if self._rotation >= 360:
            self._rotation = 0
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        _center = self.rect().center()
        
        # 绘制旋转的弧线
        pen = QPen(self._color)
        pen.setWidth(3)
        pen.setCapStyle(Qt.PenCapStyle.Round)
        pen.setBrush(QBrush(self._color))
        painter.setPen(pen)
        
        # 绘制弧线形成旋转效果
        rect = self.rect().adjusted(4, 4, -4, -4)
        
        # 使用多个弧形模拟旋转
        for i in range(3):
            start_angle = (self._rotation + i * 120) * 16
            span_angle = 90 * 16
            alpha = 255 - i * 60
            pen.setColor(QColor(self._color.red(), self._color.green(), self._color.blue(), alpha))
            painter.setPen(pen)
            painter.drawArc(rect, start_angle, span_angle)


class BouncingDots(QWidget):
    """
    弹跳点动画
    显示三个弹跳的点
    """
    
    def __init__(self, dot_size=8, color=None, parent=None):
        super().__init__(parent)
        self._dot_size = dot_size
        self._color = color or QColor(99, 102, 241)
        self._phases = [0, 0, 0]
        self._init_ui()
    
    def _init_ui(self):
        self.setFixedHeight(self._dot_size * 3)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        
        # 启动动画
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_dots)
        self._timer.start(50)
    
    def _update_dots(self):
        for i in range(3):
            self._phases[i] += 0.3
            if self._phases[i] > 2 * 3.14159:
                self._phases[i] -= 2 * 3.14159
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        total_width = self._dot_size * 5
        self.setFixedWidth(total_width)
        
        center_y = self.height() // 2
        
        for i in range(3):
            offset = int((self._dot_size * 1.5) * (0.5 + 0.5 * -abs(self._phases[i] % (2 * 3.14159) - 3.14159) / 3.14159))
            x = self._dot_size + i * (self._dot_size * 2)
            y = center_y - offset
            
            painter.setBrush(QBrush(self._color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPoint(x, y), self._dot_size // 2, self._dot_size // 2)


class LoadingOverlay(QFrame):
    """
    加载遮罩层
    显示在内容上方的半透明加载状态
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        # 设置半透明背景
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background-color: rgba(10, 10, 15, 0.7);")
        
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)
        
        # 添加脉冲指示器
        self._pulse = PulseIndicator(size=60)
        layout.addWidget(self._pulse)
        
        # 添加加载文字
        self._label = QLabel("加载中...")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("""
            color: #8B949E;
            font-size: 14px;
            font-weight: 500;
        """)
        layout.addWidget(self._label)
        
        # 隐藏遮罩层
        self.hide()
    
    def show_loading(self, message="加载中..."):
        """显示加载遮罩"""
        self._label.setText(message)
        self.show()
        
        # 添加淡入效果
        self.setWindowOpacity(0)
        self._fade_in = QPropertyAnimation(self, b"windowOpacity")
        self._fade_in.setDuration(200)
        self._fade_in.setStartValue(0)
        self._fade_in.setEndValue(1)
        self._fade_in.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._fade_in.start()
    
    def hide_loading(self):
        """隐藏加载遮罩"""
        # 添加淡出效果
        self._fade_out = QPropertyAnimation(self, b"windowOpacity")
        self._fade_out.setDuration(200)
        self._fade_out.setStartValue(1)
        self._fade_out.setEndValue(0)
        self._fade_out.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._fade_out.finished.connect(self.hide)
        self._fade_out.start()


class InlineLoader(QWidget):
    """
    行内加载指示器
    用于嵌入到文本或按钮中
    """
    
    def __init__(self, size=16, color=None, parent=None):
        super().__init__(parent)
        self._size = size
        self._color = color or QColor(99, 102, 241)
        self._init_ui()
    
    def _init_ui(self):
        self.setFixedSize(self._size, self._size)
        
        # 旋转动画
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(60)
        
        self._angle = 0
    
    def _tick(self):
        self._angle = (self._angle + 30) % 360
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        _center = self.rect().center()
        
        # 绘制弧形
        pen = QPen(self._color)
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.Round)
        painter.setPen(pen)
        
        rect = self.rect().adjusted(2, 2, -2, -2)
        painter.drawArc(rect, self._angle * 16, 180 * 16)


class LoadingButton(QFrame):
    """
    加载按钮
    带加载状态的按钮组件
    """
    
    def __init__(self, text="加载中", parent=None):
        super().__init__(parent)
        self._text = text
        self._init_ui()
    
    def _init_ui(self):
        self.setFixedHeight(36)
        self.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6366F1,
                    stop:1 #8B5CF6);
                border-radius: 8px;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(8)
        
        # 加载指示器
        self._loader = InlineLoader(size=14, color=QColor(255, 255, 255))
        layout.addWidget(self._loader)
        
        # 文字
        self._label = QLabel(self._text)
        self._label.setStyleSheet("color: white; font-weight: 600; font-size: 13px;")
        layout.addWidget(self._label)
