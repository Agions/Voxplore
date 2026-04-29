#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
导出统计部件

显示导出任务的统计信息：总任务数、处理中、已完成、失败数。
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import logging

from app.ui.components.design_system import Colors
from app.services.export.batch_export_manager import ExportStatus

logger = logging.getLogger(__name__)


class ExportStatisticsWidget(QWidget):
    """导出统计部件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.total_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.processing_tasks = 0
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 总任务数
        self.total_widget = self.create_stat_widget("总任务数", "0", Colors.TextMuted)
        layout.addWidget(self.total_widget)

        # 处理中
        self.processing_widget = self.create_stat_widget("处理中", "0", Colors.Primary)
        layout.addWidget(self.processing_widget)

        # 已完成
        self.completed_widget = self.create_stat_widget("已完成", "0", Colors.Success)
        layout.addWidget(self.completed_widget)

        # 失败
        self.failed_widget = self.create_stat_widget("失败", "0", Colors.Error)
        layout.addWidget(self.failed_widget)

    def create_stat_widget(self, title: str, value: str, color: str) -> QWidget:
        """创建统计部件"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        # 数值
        value_label = QLabel(value)
        value_font = QFont()
        value_font.setBold(True)
        value_font.setPointSize(16)
        value_label.setFont(value_font)
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setStyleSheet(f"color: {color};")

        # 标题
        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(f"color: {Colors.TextMuted}; font-size: 12px;")

        layout.addWidget(value_label)
        layout.addWidget(title_label)

        widget.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 6px;
            }
        """)

        return widget

    def update_statistics(self, tasks):
        """更新统计信息"""
        self.total_tasks = len(tasks)
        self.processing_tasks = len([t for t in tasks if t.status == ExportStatus.PROCESSING])
        self.completed_tasks = len([t for t in tasks if t.status == ExportStatus.COMPLETED])
        self.failed_tasks = len([t for t in tasks if t.status == ExportStatus.FAILED])

        self.total_widget.findChild(QLabel).setText(str(self.total_tasks))
        self.processing_widget.findChildren(QLabel)[0].setText(str(self.processing_tasks))
        self.completed_widget.findChildren(QLabel)[0].setText(str(self.completed_tasks))
        self.failed_widget.findChildren(QLabel)[0].setText(str(self.failed_tasks))