#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI监控面板 - 可复用组件
"""

from typing import Dict, Any
from datetime import datetime, timedelta

from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QPixmap, QColor, QCursor, QPen, QBrush, QPainter, QPainterPath

from ....core.icon_manager import get_icon
from ....services import ServiceStatus


class ServiceStatusWidget(QWidget):
    """服务状态部件"""

    def __init__(self, service_name: str, status: ServiceStatus, health_data: Dict[str, Any]):
        super().__init__()
        self.service_name = service_name
        self.status = status
        self.health_data = health_data
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 状态指示器
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(12, 12)
        self._update_status_indicator()
        layout.addWidget(self.status_indicator)

        # 服务名称
        name_label = QLabel(self.service_name)
        name_label.setProperty("class", "service-name")
        layout.addWidget(name_label)

        # 状态文本
        self.status_label = QLabel(self._get_status_text())
        self.status_label.setProperty("class", "service-status")
        layout.addWidget(self.status_label)

        layout.addStretch()

        # 响应时间
        if self.health_data.get("response_time"):
            response_time = self.health_data["response_time"]
            time_label = QLabel(f"{response_time:.1f}ms")
            time_label.setProperty("class", "response-time")
            layout.addWidget(time_label)

        # 错误率
        if self.health_data.get("error_rate"):
            error_rate = self.health_data["error_rate"]
            error_label = QLabel(f"错误率: {error_rate:.1%}")
            # 根据错误率设置样式级别
            if error_rate > 0.1:
                error_label.setProperty("class", "error-rate high")
            elif error_rate > 0.05:
                error_label.setProperty("class", "error-rate medium")
            else:
                error_label.setProperty("class", "error-rate low")
            layout.addWidget(error_label)

    def _update_status_indicator(self):
        """更新状态指示器"""
        color_map = {
            ServiceStatus.ACTIVE: "#52c41a",
            ServiceStatus.INACTIVE: "#888888",
            ServiceStatus.ERROR: "#ff4d4f",
            ServiceStatus.MAINTENANCE: "#faad14"
        }

        color = color_map.get(self.status, "#888888")
        pixmap = QPixmap(12, 12)
        pixmap.fill(QColor("transparent"))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(color), 2))
        painter.setBrush(QBrush(QColor(color)))
        painter.drawEllipse(1, 1, 10, 10)
        painter.end()

        self.status_indicator.setPixmap(pixmap)

    def _get_status_text(self) -> str:
        """获取状态文本"""
        status_text_map = {
            ServiceStatus.ACTIVE: "正常运行",
            ServiceStatus.INACTIVE: "未激活",
            ServiceStatus.ERROR: "错误",
            ServiceStatus.MAINTENANCE: "维护中"
        }
        return status_text_map.get(self.status, "未知")

    def update_status(self, status: ServiceStatus, health_data: Dict[str, Any]):
        """更新状态"""
        self.status = status
        self.health_data = health_data
        self._update_status_indicator()
        self.status_label.setText(self._get_status_text())


class PerformanceChart(QWidget):
    """性能图表"""

    def __init__(self, title: str, max_value: float = 100):
        super().__init__()
        self.title = title
        self.max_value = max_value
        self.data_points = []
        self.max_points = 50
        self.setFixedSize(300, 100)

    def add_data_point(self, value: float):
        """添加数据点"""
        self.data_points.append(value)
        if len(self.data_points) > self.max_points:
            self.data_points.pop(0)
        self.update()

    def clear_data(self):
        """清除数据"""
        self.data_points.clear()
        self.update()

    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制背景
        painter.fillRect(self.rect(), QColor("#1a1a1a"))

        # 绘制标题
        painter.setPen(QPen(QColor("#ffffff"), 1))
        painter.drawText(5, 15, self.title)

        # 绘制网格
        painter.setPen(QPen(QColor("#404040"), 1))
        for i in range(0, 5):
            y = 25 + i * 15
            painter.drawLine(5, y, self.width() - 5, y)

        # 绘制数据线
        if len(self.data_points) > 1:
            painter.setPen(QPen(QColor("#1890ff"), 2))

            path = QPainterPath()
            for i, value in enumerate(self.data_points):
                x = 5 + (i / (self.max_points - 1)) * (self.width() - 10)
                y = 90 - (value / self.max_value) * 60

                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)

            painter.drawPath(path)

            # 绘制数据点
            painter.setPen(QPen(QColor("#1890ff"), 1))
            painter.setBrush(QBrush(QColor("#1890ff")))
            for i, value in enumerate(self.data_points):
                x = 5 + (i / (self.max_points - 1)) * (self.width() - 10)
                y = 90 - (value / self.max_value) * 60
                painter.drawEllipse(QPoint(x, y), 2, 2)

        # 绘制当前值
        if self.data_points:
            current_value = self.data_points[-1]
            painter.setPen(QPen(QColor("#ffffff"), 1))
            painter.drawText(self.width() - 50, 15, f"{current_value:.1f}")


class AlertWidget(QWidget):
    """告警部件"""

    alert_clicked = Signal(object)  # AlertData

    def __init__(self, alert):
        super().__init__()
        self.alert = alert
        self._init_ui()

    def _init_ui(self):
        """初始化UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 告警图标
        icon_name = {
            "info": "info",
            "warning": "warning",
            "error": "error",
            "critical": "critical"
        }.get(self.alert.level, "info")

        icon_label = QLabel()
        icon_label.setPixmap(get_icon(icon_name, 16).pixmap(16, 16))
        layout.addWidget(icon_label)

        # 告警信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        # 服务名称和级别
        header_layout = QHBoxLayout()
        service_label = QLabel(self.alert.service_name)
        service_label.setProperty("class", "alert-service")
        header_layout.addWidget(service_label)

        level_label = QLabel(self.alert.level.upper())
        level_label.setProperty("class", f"alert-level {self.alert.level}")
        header_layout.addWidget(level_label)

        header_layout.addStretch()

        # 时间
        time_label = QLabel(self._format_time(self.alert.timestamp))
        time_label.setProperty("class", "alert-time")
        header_layout.addWidget(time_label)

        info_layout.addLayout(header_layout)

        # 消息
        message_label = QLabel(self.alert.message)
        message_label.setProperty("class", "alert-message")
        message_label.setWordWrap(True)
        info_layout.addWidget(message_label)

        layout.addLayout(info_layout)
        layout.addStretch()

        # 状态指示器
        if self.alert.resolved:
            resolved_label = QLabel("已解决")
            resolved_label.setProperty("class", "alert-resolved")
            layout.addWidget(resolved_label)

        # 鼠标样式
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.mousePressEvent = self._on_clicked

    def _format_time(self, timestamp: float) -> str:
        """格式化时间"""
        dt = datetime.fromtimestamp(timestamp)
        now = datetime.now()
        delta = now - dt

        if delta < timedelta(minutes=1):
            return "刚刚"
        elif delta < timedelta(hours=1):
            return f"{delta.seconds // 60}分钟前"
        elif delta < timedelta(days=1):
            return f"{delta.seconds // 3600}小时前"
        else:
            return dt.strftime("%Y-%m-%d %H:%M")

    def _on_clicked(self, event):
        """点击处理"""
        self.alert_clicked.emit(self.alert)
