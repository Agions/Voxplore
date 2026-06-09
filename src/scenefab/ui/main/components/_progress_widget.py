#!/usr/bin/env python3

"""
导出进度监控组件
提供实时导出进度监控和状态显示
"""

import time

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from scenefab.logger import Logger

from ...components.design_system import Colors
from ...export.export_system import ExportStatus, ExportTask


class ExportProgressWidget(QWidget):
    """导出进度部件"""

    task_clicked = Signal(str)

    def __init__(self, task: ExportTask, parent=None):
        super().__init__(parent)
        self.task = task
        self.logger = Logger.get_logger(__name__)
        self.setup_ui()
        self.update_display()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # 任务信息
        info_layout = QHBoxLayout()

        # 任务名称
        name_label = QLabel(self._get_task_name())
        name_font = QFont()
        name_font.setBold(True)
        name_label.setFont(name_font)

        # 状态标签
        status_label = QLabel(self.task.status.value)
        status_label.setStyleSheet(
            f"background-color: {self._get_status_color()}; "
            f"color: white; padding: 2px 8px; border-radius: 4px;"
        )

        info_layout.addWidget(name_label)
        info_layout.addStretch()
        info_layout.addWidget(status_label)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(int(self.task.progress))

        # 详细信息
        details_layout = QHBoxLayout()

        # 开始时间
        start_time_text = (
            self._format_time(self.task.started_at)
            if self.task.started_at
            else "未开始"
        )
        start_label = QLabel(f"开始: {start_time_text}")

        # 预计剩余时间
        eta_text = self._calculate_eta()
        eta_label = QLabel(f"剩余: {eta_text}")

        # 输出路径
        output_path = self.task.output_path
        if len(output_path) > 30:
            output_path = "..." + output_path[-27:]
        output_label = QLabel(f"输出: {output_path}")
        output_label.setWordWrap(True)

        details_layout.addWidget(start_label)
        details_layout.addWidget(eta_label)
        details_layout.addWidget(output_label)
        details_layout.addStretch()

        # 错误信息
        if self.task.status == ExportStatus.FAILED and self.task.error_message:
            error_label = QLabel(f"错误: {self.task.error_message}")
            error_label.setStyleSheet(
                f"color: {Colors.Error}; background-color: {Colors.ErrorSubtle}; "
                "padding: 5px; border-radius: 3px;"
            )
            error_label.setWordWrap(True)
            layout.addWidget(error_label)

        layout.addLayout(info_layout)
        layout.addWidget(self.progress_bar)
        layout.addLayout(details_layout)

        # 设置样式
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                margin: 5px;
            }
            QWidget:hover {
                background-color: #e9ecef;
            }
        """)

        # 启用鼠标悬停效果
        self.setMouseTracking(True)

    def update_display(self):
        """更新显示"""
        self.progress_bar.setValue(int(self.task.progress))

        # 更新状态标签
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if item.layout():
                for j in range(item.layout().count()):
                    sub_item = item.layout().itemAt(j)
                    if isinstance(sub_item.widget(), QLabel):
                        label = sub_item.widget()
                        if "开始:" in label.text():
                            start_time_text = (
                                self._format_time(self.task.started_at)
                                if self.task.started_at
                                else "未开始"
                            )
                            label.setText(f"开始: {start_time_text}")
                        elif "剩余:" in label.text():
                            eta_text = self._calculate_eta()
                            label.setText(f"剩余: {eta_text}")

    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.task_clicked.emit(self.task.id)

    def _get_task_name(self) -> str:
        """获取任务名称"""
        project_name = self.task.metadata.get("project_name", "未知项目")
        return f"{project_name} ({self.task.preset.name})"

    def _get_status_color(self) -> str:
        """获取状态颜色"""
        colors = {
            ExportStatus.PENDING: Colors.TextMuted,
            ExportStatus.QUEUED: Colors.Warning,
            ExportStatus.PROCESSING: Colors.Primary,
            ExportStatus.COMPLETED: Colors.Success,
            ExportStatus.FAILED: Colors.Error,
            ExportStatus.CANCELLED: Colors.TextMuted,
        }
        return colors.get(self.task.status, Colors.TextMuted)

    def _format_time(self, timestamp: float | None) -> str:
        """格式化时间"""
        if not timestamp:
            return ""
        return time.strftime("%H:%M:%S", time.localtime(timestamp))

    def _calculate_eta(self) -> str:
        """计算预计剩余时间"""
        if self.task.status != ExportStatus.PROCESSING or not self.task.started_at:
            return "未知"

        elapsed_time = time.time() - self.task.started_at
        if elapsed_time <= 0 or self.task.progress <= 0:
            return "未知"

        total_estimated_time = elapsed_time / (self.task.progress / 100)
        remaining_time = total_estimated_time - elapsed_time

        if remaining_time < 0:
            return "即将完成"

        return self._format_duration(remaining_time)

    def _format_duration(self, seconds: float) -> str:
        """格式化持续时间"""
        if seconds < 60:
            return f"{int(seconds)}秒"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}分{secs}秒"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}小时{minutes}分"
