#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Emotion Curve Widget
情感曲线组件 - 自定义绘制的情感强度曲线 widget

功能:
- 使用 bezier 曲线绘制平滑的情感曲线
- 暗色渐变背景
- 曲线颜色根据情感类型变化
- 时间轴和强度轴网格线
- 可拖拽的当前位置指示器
- 悬停时显示精确数值提示
- 平滑动画效果
"""

from typing import List, Optional

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QSize, Qt, Signal, QPoint, QRect, QPropertyAnimation
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QLinearGradient,
    QPainterPath, QMouseEvent
)


class EmotionCurveWidget(QWidget):
    """
    情感曲线绘制组件
    
    显示一条随时间变化的情感强度曲线。
    支持平滑动画、自定义颜色和交互。
    
    Signals:
        curve_changed: 当曲线数据改变时发射 (List[float])
        position_changed: 当拖拽位置改变时发射 (float, 0.0-1.0)
    """
    
    curve_changed = Signal(list)
    position_changed = Signal(float)
    
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        curve_color: str = "#FF9E64",
        background_gradient: bool = True,
    ):
        """
        初始化情感曲线 widget
        
        Args:
            parent: 父 widget
            curve_color: 曲线颜色 (hex)
            background_gradient: 是否使用背景渐变
        """
        super().__init__(parent)
        
        # 曲线数据 (11个点: 0%, 10%, ... 100%)
        self._curve: List[float] = [0.5] * 11
        
        # 颜色
        self._curve_color = QColor(curve_color)
        self._background_color = QColor("#0D1117")
        self._grid_color = QColor("#1E293B")
        self._text_color = QColor("#94A3B8")
        
        # 背景渐变
        self._use_background_gradient = background_gradient
        self._gradient_top = QColor("#0D1117")
        self._gradient_bottom = QColor("#1a1a2e")
        
        # 当前位置指示器 (0.0 - 1.0)
        self._current_position: float = 0.0
        
        # 拖拽状态
        self._is_dragging: bool = False
        
        # 动画
        self._animation: Optional[QPropertyAnimation] = None
        self._animated_curve: List[float] = self._curve.copy()
        
        # 悬停状态
        self._hover_point: Optional[QPoint] = None
        self._hover_index: Optional[int] = None
        
        # 尺寸提示
        self.setMinimumSize(400, 120)
        self.setMaximumSize(1000, 200)
        self.setSizePolicy(Qt.Horizontal, Qt.MinimumExpanding)
        self.setCursor(Qt.PointingHandCursor)
        
        # 启用鼠标追踪
        self.setMouseTracking(True)
        
        # 网格线
        self._show_time_grid = True
        self._show_intensity_grid = True
        
    @property
    def curve(self) -> List[float]:
        """获取当前曲线数据"""
        return self._curve.copy()
    
    @curve.setter
    def curve(self, new_curve: List[float]):
        """
        设置曲线数据
        
        Args:
            new_curve: 新的曲线数据 (11个点, 0.0-1.0)
        """
        if len(new_curve) != 11:
            raise ValueError("Curve must have exactly 11 points (0%, 10%, ... 100%)")
        
        # 确保值在有效范围内
        self._curve = [max(0.0, min(1.0, v)) for v in new_curve]
        
        # 更新动画曲线
        self._animated_curve = self._curve.copy()
        
        # 发射信号
        self.curve_changed.emit(self._curve)
        self.update()
    
    @property
    def curve_color(self) -> QColor:
        """获取曲线颜色"""
        return self._curve_color
    
    @curve_color.setter
    def curve_color(self, color: QColor):
        """设置曲线颜色"""
        self._curve_color = color
        self.update()
    
    @property
    def current_position(self) -> float:
        """获取当前位置 (0.0 - 1.0)"""
        return self._current_position
    
    @current_position.setter
    def current_position(self, pos: float):
        """
        设置当前位置
        
        Args:
            pos: 位置 (0.0 - 1.0)
        """
        self._current_position = max(0.0, min(1.0, pos))
        self.position_changed.emit(self._current_position)
        self.update()
    
    def set_curve_from_preset(self, curve_template: List[float], color: str):
        """
        从预设设置曲线
        
        Args:
            curve_template: 预设曲线模板
            color: 曲线颜色 (hex)
        """
        self._curve_color = QColor(color)
        if len(curve_template) == 11:
            self.curve = curve_template
        else:
            # 需要插值
            interpolated = self._interpolate_to_11_points(curve_template)
            self.curve = interpolated
    
    def _interpolate_to_11_points(self, curve: List[float]) -> List[float]:
        """将任意长度的曲线插值到11个点"""
        if len(curve) == 11:
            return curve
        
        result = []
        for i in range(11):
            t = i / 10.0 * (len(curve) - 1)
            idx = int(t)
            frac = t - idx
            
            if idx >= len(curve) - 1:
                result.append(curve[-1])
            else:
                val = curve[idx] * (1 - frac) + curve[idx + 1] * frac
                result.append(max(0.0, min(1.0, val)))
        
        return result
    
    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        w = self.width()
        h = self.height()
        
        # 边距
        margin_left = 40
        margin_right = 20
        margin_top = 15
        margin_bottom = 25
        
        # 绘制背景
        self._draw_background(painter, w, h)
        
        # 绘制网格
        if self._show_time_grid:
            self._draw_time_grid(painter, w, h, margin_left, margin_right, margin_top, margin_bottom)
        
        if self._show_intensity_grid:
            self._draw_intensity_grid(painter, w, h, margin_left, margin_right, margin_top, margin_bottom)
        
        # 绘制曲线
        self._draw_curve(
            painter, w, h, margin_left, margin_right, margin_top, margin_bottom
        )
        
        # 绘制当前位置指示器
        self._draw_position_indicator(
            painter, w, h, margin_left, margin_right, margin_top, margin_bottom
        )
        
        # 绘制时间标签
        self._draw_time_labels(painter, w, h, margin_left, margin_right, margin_top, margin_bottom)
        
        # 绘制强度标签
        self._draw_intensity_labels(painter, w, h, margin_left, margin_right, margin_top, margin_bottom)
        
        # 绘制悬停提示
        if self._hover_point is not None and self._hover_index is not None:
            self._draw_hover_tooltip(painter)
    
    def _draw_background(self, painter: QPainter, w: int, h: int):
        """绘制背景"""
        if self._use_background_gradient:
            gradient = QLinearGradient(0, 0, 0, h)
            gradient.setColorAt(0, self._gradient_top)
            gradient.setColorAt(1, self._gradient_bottom)
            painter.fillRect(0, 0, w, h, gradient)
        else:
            painter.fillRect(0, 0, w, h, self._background_color)
    
    def _draw_time_grid(
        self, painter: QPainter, w: int, h: int,
        margin_left: int, margin_right: int, margin_top: int, margin_bottom: int
    ):
        """绘制时间网格"""
        plot_width = w - margin_left - margin_right
        
        painter.setPen(QPen(self._grid_color, 1, Qt.DashLine))
        
        # 垂直网格线 (每10%)
        for i in range(11):
            x = margin_left + i * plot_width / 10
            painter.drawLine(int(x), margin_top, int(x), h - margin_bottom)
    
    def _draw_intensity_grid(
        self, painter: QPainter, w: int, h: int,
        margin_left: int, margin_right: int, margin_top: int, margin_bottom: int
    ):
        """绘制强度网格"""
        plot_height = h - margin_top - margin_bottom
        
        painter.setPen(QPen(self._grid_color, 1, Qt.DashLine))
        
        # 水平网格线 (每25%)
        for i in range(5):
            y = margin_top + i * plot_height / 4
            painter.drawLine(margin_left, int(y), w - margin_right, int(y))
    
    def _draw_curve(
        self, painter: QPainter, w: int, h: int,
        margin_left: int, margin_right: int, margin_top: int, margin_bottom: int
    ):
        """绘制平滑 bezier 曲线"""
        plot_width = w - margin_left - margin_right
        plot_height = h - margin_top - margin_bottom
        
        # 创建路径
        path = QPainterPath()
        
        points = []
        for i, value in enumerate(self._animated_curve):
            x = margin_left + i * plot_width / 10
            # Y 坐标：值越大越靠上 (invert)
            y = margin_top + (1.0 - value) * plot_height
            points.append(QPoint(int(x), int(y)))
        
        # 使用 bezier 曲线连接点
        if points:
            path.moveTo(points[0])
            
            # 使用 cubicTo 创建平滑曲线
            for i in range(len(points) - 1):
                p0 = points[i]
                p1 = points[i + 1]
                
                # 控制点偏移量
                dx = (p1.x() - p0.x()) / 3
                
                cp1 = QPoint(p0.x() + dx, p0.y())
                cp2 = QPoint(p1.x() - dx, p1.y())
                
                path.cubicTo(cp1, cp2, p1)
        
        # 绘制曲线
        pen = QPen(self._curve_color, 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(path)
        
        # 绘制曲线下的渐变填充
        self._draw_curve_fill(painter, path, points, w, h, margin_left, margin_right, margin_top, margin_bottom)
        
        # 绘制数据点
        painter.setPen(Qt.NoPen)
        brush = QBrush(self._curve_color)
        painter.setBrush(brush)
        
        for pt in points:
            # 大点
            painter.drawEllipse(pt, 4, 4)
    
    def _draw_curve_fill(
        self, painter: QPainter, path: QPainterPath, points: List[QPoint],
        w: int, h: int,
        margin_left: int, margin_right: int, margin_top: int, margin_bottom: int
    ):
        """绘制曲线下的渐变填充"""
        if not points:
            return
        
        # 创建闭合路径
        fill_path = QPainterPath(path)
        
        # 闭合到 X 轴
        fill_path.lineTo(points[-1].x(), h - margin_bottom)
        fill_path.lineTo(points[0].x(), h - margin_bottom)
        fill_path.closeSubpath()
        
        # 创建渐变
        gradient = QLinearGradient(0, margin_top, 0, h - margin_bottom)
        color = self._curve_color
        gradient.setColorAt(0, color.lighter(150).alpha(80))
        gradient.setColorAt(1, color.darker(150).alpha(40))
        
        painter.fillPath(fill_path, gradient)
    
    def _draw_position_indicator(
        self, painter: QPainter, w: int, h: int,
        margin_left: int, margin_right: int, margin_top: int, margin_bottom: int
    ):
        """绘制当前位置指示器"""
        plot_width = w - margin_left - margin_right
        plot_height = h - margin_top - margin_bottom
        
        # 计算指示器位置
        x = int(margin_left + self._current_position * plot_width)
        
        # 插值获取 Y 值
        idx = self._current_position * 10
        lower_idx = int(idx)
        upper_idx = min(lower_idx + 1, 10)
        frac = idx - lower_idx
        
        if lower_idx < len(self._animated_curve) and upper_idx < len(self._animated_curve):
            value = self._animated_curve[lower_idx] * (1 - frac) + self._animated_curve[upper_idx] * frac
        else:
            value = 0.5
        
        y = int(margin_top + (1.0 - value) * plot_height)
        
        # 绘制垂直线
        pen = QPen(self._curve_color.lighter(130), 1, Qt.DashLine)
        painter.setPen(pen)
        painter.drawLine(x, margin_top, x, h - margin_bottom)
        
        # 绘制圆形指示器
        painter.setPen(Qt.NoPen)
        brush = QBrush(self._curve_color)
        painter.setBrush(brush)
        painter.drawEllipse(QPoint(x, y), 6, 6)
        
        # 内圆
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.drawEllipse(QPoint(x, y), 3, 3)
    
    def _draw_time_labels(
        self, painter: QPainter, w: int, h: int,
        margin_left: int, margin_right: int, margin_top: int, margin_bottom: int
    ):
        """绘制时间标签"""
        painter.setPen(QPen(self._text_color, 9))
        
        # 只绘制首尾和中间点
        labels = [0, 5, 10]
        plot_width = w - margin_left - margin_right
        
        for i in labels:
            x = int(margin_left + i * plot_width / 10)
            painter.drawText(x - 10, h - 5, 20, 14, Qt.AlignCenter, f"{i*10}%")
    
    def _draw_intensity_labels(
        self, painter: QPainter, w: int, h: int,
        margin_left: int, margin_right: int, margin_top: int, margin_bottom: int
    ):
        """绘制强度标签"""
        painter.setPen(QPen(self._text_color, 9))
        
        plot_height = h - margin_top - margin_bottom
        
        # 高 (top)
        y = margin_top
        painter.drawText(margin_left - 35, y - 5, 30, 14, Qt.AlignRight, "高")
        
        # 中 (middle)
        y = margin_top + plot_height // 2
        painter.drawText(margin_left - 35, y - 5, 30, 14, Qt.AlignRight, "中")
        
        # 低 (bottom)
        y = h - margin_bottom
        painter.drawText(margin_left - 35, y - 5, 30, 14, Qt.AlignRight, "低")
    
    def _draw_hover_tooltip(self, painter: QPainter):
        """绘制悬停提示"""
        if self._hover_point is None or self._hover_index is None:
            return
        
        if self._hover_index >= len(self._animated_curve):
            return
        
        value = self._animated_curve[self._hover_index]
        
        text = f"{self._hover_index * 10}%: {value:.2f}"
        
        # 绘制简单提示框
        painter.setPen(QPen(QColor("#F1F5F9"), 1))
        rect = QRect(self._hover_point.x() - 30, self._hover_point.y() - 25, 60, 20)
        painter.fillRect(rect, QColor("#1E293B"))
        painter.drawRect(rect)
        
        painter.setPen(QPen(QColor("#F1F5F9"), 9))
        painter.drawText(rect, Qt.AlignCenter, text)
    
    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            self._is_dragging = True
            self._update_position_from_mouse(event.pos())
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动事件"""
        pos = event.pos()
        
        if self._is_dragging:
            self._update_position_from_mouse(pos)
        else:
            # 更新悬停状态
            self._update_hover_state(pos)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            self._is_dragging = False
    
    def leaveEvent(self, event):
        """鼠标离开事件"""
        self._hover_point = None
        self._hover_index = None
        self.update()
    
    def _update_position_from_mouse(self, pos: QPoint):
        """根据鼠标位置更新当前位置"""
        margin_left = 40
        margin_right = 20
        plot_width = self.width() - margin_left - margin_right
        
        # 计算相对位置
        rel_x = pos.x() - margin_left
        new_position = rel_x / plot_width
        new_position = max(0.0, min(1.0, new_position))
        
        if abs(new_position - self._current_position) > 0.01:
            self._current_position = new_position
            self.position_changed.emit(self._current_position)
            self.update()
    
    def _update_hover_state(self, pos: QPoint):
        """更新悬停状态"""
        margin_left = 40
        margin_right = 20
        margin_top = 15
        margin_bottom = 25
        
        # 检查是否在绘图区域内
        if (pos.x() < margin_left or pos.x() > self.width() - margin_right or
            pos.y() < margin_top or pos.y() > self.height() - margin_bottom):
            if self._hover_point is not None:
                self._hover_point = None
                self._hover_index = None
                self.update()
            return
        
        # 计算悬停的索引
        plot_width = self.width() - margin_left - margin_right
        rel_x = pos.x() - margin_left
        idx = int(round(rel_x / plot_width * 10))
        idx = max(0, min(10, idx))
        
        # 更新状态
        if self._hover_point is None or self._hover_index != idx:
            self._hover_point = pos
            self._hover_index = idx
            self.update()
    
    def sizeHint(self) -> QSize:
        """尺寸提示"""
        return QSize(600, 150)
    
    def minimumSizeHint(self) -> QSize:
        """最小尺寸提示"""
        return QSize(400, 120)
