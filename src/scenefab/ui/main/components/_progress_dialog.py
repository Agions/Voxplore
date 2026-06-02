#!/usr/bin/env python3

"""
导出进度监控组件
提供实时导出进度监控和状态显示
"""

import time
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from scenefab.logger import Logger
from scenefab.ui.main.components._monitor_widget import ExportMonitorWidget

from ...components.design_system import Colors
from ...export.export_system import ExportStatus, ExportTask
from ...main.components.export_stats import ExportStatisticsWidget
from ...main.components.monitor_widgets import PerformanceChart


class ExportProgressDialog(QDialog):
    """导出进度对话框"""

    def __init__(self, export_system, parent=None):
        super().__init__(parent)
        self.export_system = export_system
        self.logger = Logger.get_logger(__name__)
        self.setup_ui()
        self.setup_signals()

    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("导出进度")
        self.setMinimumSize(600, 400)
        self.setModal(False)

        layout = QVBoxLayout(self)

        # 监控部件
        self.monitor_widget = ExportMonitorWidget(self.export_system)
        layout.addWidget(self.monitor_widget)

        # 操作按钮
        button_layout = QHBoxLayout()

        self.hide_btn = QPushButton("隐藏")
        self.hide_btn.clicked.connect(self.hide)

        self.cancel_all_btn = QPushButton("取消全部")
        self.cancel_all_btn.clicked.connect(self.cancel_all_tasks)

        button_layout.addStretch()
        button_layout.addWidget(self.hide_btn)
        button_layout.addWidget(self.cancel_all_btn)

        layout.addLayout(button_layout)

    def setup_signals(self):
        """设置信号连接"""
        # 连接导出系统信号
        self.export_system.export_started.connect(self.on_export_started)
        self.export_system.export_progress.connect(self.on_export_progress)
        self.export_system.export_completed.connect(self.on_export_completed)
        self.export_system.export_failed.connect(self.on_export_failed)

    def on_export_started(self, task_id: str):
        """导出开始事件"""
        self.show()
        self.raise_()
        self.activateWindow()

    def on_export_progress(self, task_id: str, progress: float):
        """导出进度事件"""
        # 更新进度条
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(int(progress * 100))
        if hasattr(self, 'progress_label'):
            self.progress_label.setText(f"{int(progress * 100)}%")

    def on_export_completed(self, task_id: str, output_path: str):
        """导出完成事件"""
        # 检查是否所有任务都已完成
        try:
            tasks = self.export_system.get_task_history()
            active_tasks = [t for t in tasks if t.status.value in ["processing", "queued", "pending"]]

            if not active_tasks:
                # 所有任务完成，显示完成通知
                self.show_completion_notification()
        except Exception as e:
            self.logger.error(f"Failed to check completion status: {e}")

    def on_export_failed(self, task_id: str, error_message: str):
        """导出失败事件"""
        # 显示错误通知
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(
            self,
            "导出失败",
            f"任务 {task_id} 导出失败：\n{error_message}"
        )
        # 更新状态显示
        if hasattr(self, 'status_label'):
            self.status_label.setText("导出失败")
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(0)

    def cancel_all_tasks(self):
        """取消所有任务"""
        reply = self.logger.question(
            "确认取消", "确定要取消所有导出任务吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                tasks = self.export_system.get_task_history()
                cancelled_count = 0

                for task in tasks:
                    if task.status.value in ["processing", "queued", "pending"]:
                        if self.export_system.cancel_export(task.id):
                            cancelled_count += 1

                QMessageBox.information(self, "成功", f"已取消 {cancelled_count} 个任务")

            except Exception as e:
                QMessageBox.critical(self, "错误", f"取消任务失败: {str(e)}")

    def show_completion_notification(self):
        """显示完成通知"""
        try:
            tasks = self.export_system.get_task_history()
            completed_count = len([t for t in tasks if t.status.value == "completed"])
            failed_count = len([t for t in tasks if t.status.value == "failed"])

            message = f"导出完成！\\n成功: {completed_count} 个任务"
            if failed_count > 0:
                message += f"\\n失败: {failed_count} 个任务"

            QMessageBox.information(self, "导出完成", message)

        except Exception as e:
            self.logger.error(f"Failed to show completion notification: {e}")

    def cleanup(self):
        """清理资源"""
        self.monitor_widget.cleanup()
