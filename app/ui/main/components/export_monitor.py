#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
导出进度监控组件
提供实时导出进度监控和状态显示
"""

import time
from typing import Dict, List, Optional
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QPushButton, QProgressBar, QSplitter, QGroupBox,
                            QScrollArea, QDialog, QMessageBox)
from PySide6.QtCore import Qt, QTimer, Signal, QRect
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QPoint

from ...export.export_system import ExportTask, ExportStatus
from ...core.logger import Logger


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
        status_label.setStyleSheet(f"background-color: {self._get_status_color()}; "
                                  f"color: white; padding: 2px 8px; border-radius: 4px;")

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
        start_time_text = self._format_time(self.task.started_at) if self.task.started_at else "未开始"
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
            error_label.setStyleSheet("color: red; background-color: #ffeeee; "
                                   "padding: 5px; border-radius: 3px;")
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
                            start_time_text = self._format_time(self.task.started_at) if self.task.started_at else "未开始"
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
            ExportStatus.PENDING: "#6c757d",
            ExportStatus.QUEUED: "#ffc107",
            ExportStatus.PROCESSING: "#007bff",
            ExportStatus.COMPLETED: "#28a745",
            ExportStatus.FAILED: "#dc3545",
            ExportStatus.CANCELLED: "#6c757d"
        }
        return colors.get(self.task.status, "#6c757d")

    def _format_time(self, timestamp: Optional[float]) -> str:
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


class ExportStatisticsWidget(QWidget):
    """导出统计部件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = Logger.get_logger(__name__)
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
        self.total_widget = self.create_stat_widget("总任务数", "0", "#6c757d")
        layout.addWidget(self.total_widget)

        # 处理中
        self.processing_widget = self.create_stat_widget("处理中", "0", "#007bff")
        layout.addWidget(self.processing_widget)

        # 已完成
        self.completed_widget = self.create_stat_widget("已完成", "0", "#28a745")
        layout.addWidget(self.completed_widget)

        # 失败
        self.failed_widget = self.create_stat_widget("失败", "0", "#dc3545")
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
        title_label.setStyleSheet("color: #6c757d; font-size: 12px;")

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

    def update_statistics(self, tasks: List[ExportTask]):
        """更新统计信息"""
        self.total_tasks = len(tasks)
        self.processing_tasks = len([t for t in tasks if t.status == ExportStatus.PROCESSING])
        self.completed_tasks = len([t for t in tasks if t.status == ExportStatus.COMPLETED])
        self.failed_tasks = len([t for t in tasks if t.status == ExportStatus.FAILED])

        self.total_widget.findChild(QLabel).setText(str(self.total_tasks))
        self.processing_widget.findChildren(QLabel)[0].setText(str(self.processing_tasks))
        self.completed_widget.findChildren(QLabel)[0].setText(str(self.completed_tasks))
        self.failed_widget.findChildren(QLabel)[0].setText(str(self.failed_tasks))


class ExportSpeedChart(QWidget):
    """导出速度图表"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = Logger.get_logger(__name__)
        self.speed_history = []
        self.max_history_points = 100
        self.setMinimumHeight(150)

    def add_speed_point(self, speed: float):
        """添加速度点"""
        self.speed_history.append(speed)
        if len(self.speed_history) > self.max_history_points:
            self.speed_history.pop(0)
        self.update()

    def clear_history(self):
        """清除历史记录"""
        self.speed_history.clear()
        self.update()

    def paintEvent(self, event):
        """绘制事件"""
        if not self.speed_history:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 获取绘制区域
        rect = self.rect()
        margin = 20
        chart_rect = QRect(margin, margin, rect.width() - 2 * margin, rect.height() - 2 * margin)

        # 绘制背景
        painter.fillRect(chart_rect, QColor(248, 249, 250))
        painter.setPen(QPen(QColor(222, 226, 230), 1))
        painter.drawRect(chart_rect)

        if len(self.speed_history) < 2:
            return

        # 计算缩放
        max_speed = max(self.speed_history) if self.speed_history else 1
        min_speed = min(self.speed_history) if self.speed_history else 0
        speed_range = max_speed - min_speed if max_speed != min_speed else 1

        # 绘制速度曲线
        painter.setPen(QPen(QColor(0, 123, 255), 2))

        points = []
        for i, speed in enumerate(self.speed_history):
            x = chart_rect.left() + (i / (len(self.speed_history) - 1)) * chart_rect.width()
            y = chart_rect.bottom() - ((speed - min_speed) / speed_range) * chart_rect.height()
            points.append(QPoint(int(x), int(y)))

        for i in range(len(points) - 1):
            painter.drawLine(points[i], points[i + 1])

        # 绘制当前速度值
        if self.speed_history:
            current_speed = self.speed_history[-1]
            painter.setPen(QPen(QColor(0, 123, 255), 1))
            painter.setFont(QFont("Arial", 10))
            painter.drawText(chart_rect.right() - 100, chart_rect.top() + 20,
                           f"当前速度: {current_speed:.1f} MB/s")


class ExportMonitorWidget(QWidget):
    """导出监控主部件"""

    def __init__(self, export_system, parent=None):
        super().__init__(parent)
        self.export_system = export_system
        self.logger = Logger.get_logger(__name__)
        self.tasks: List[ExportTask] = []
        self.active_task_widgets: Dict[str, ExportProgressWidget] = {}
        self.setup_ui()
        self.setup_timer()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 统计信息
        self.statistics_widget = ExportStatisticsWidget()
        layout.addWidget(self.statistics_widget)

        # 分割器
        splitter = QSplitter(Qt.Orientation.Vertical)

        # 活动任务区域
        active_group = QGroupBox("活动任务")
        active_layout = QVBoxLayout(active_group)

        self.active_tasks_scroll = QScrollArea()
        self.active_tasks_scroll.setWidgetResizable(True)
        self.active_tasks_widget = QWidget()
        self.active_tasks_layout = QVBoxLayout(self.active_tasks_widget)
        self.active_tasks_layout.setContentsMargins(0, 0, 0, 0)
        self.active_tasks_layout.addStretch()

        self.active_tasks_scroll.setWidget(self.active_tasks_widget)
        active_layout.addWidget(self.active_tasks_scroll)

        # 速度图表
        speed_group = QGroupBox("导出速度")
        speed_layout = QVBoxLayout(speed_group)

        self.speed_chart = ExportSpeedChart()
        speed_layout.addWidget(self.speed_chart)

        # 添加到分割器
        splitter.addWidget(active_group)
        splitter.addWidget(speed_group)

        # 设置分割器比例
        splitter.setSizes([400, 150])

        layout.addWidget(splitter)

    def setup_timer(self):
        """设置定时器"""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(1000)  # 每秒更新一次

    def update_display(self):
        """更新显示"""
        try:
            # 获取任务列表
            tasks = self.export_system.get_task_history()

            # 过滤出活动任务（处理中、排队中、待处理）
            active_tasks = [t for t in tasks if t.status.value in ["processing", "queued", "pending"]]

            # 更新统计信息
            self.statistics_widget.update_statistics(tasks)

            # 更新活动任务显示
            self.update_active_tasks(active_tasks)

            # 更新速度图表
            self.update_speed_chart(active_tasks)

        except Exception as e:
            self.logger.error(f"Failed to update monitor display: {e}")

    def update_active_tasks(self, tasks: List[ExportTask]):
        """更新活动任务显示"""
        # 创建任务ID到任务的映射
        current_task_ids = {task.id for task in tasks}
        existing_task_ids = set(self.active_task_widgets.keys())

        # 移除已完成的任务部件
        for task_id in existing_task_ids - current_task_ids:
            widget = self.active_task_widgets.pop(task_id, None)
            if widget:
                self.active_tasks_layout.removeWidget(widget)
                widget.deleteLater()

        # 添加新任务部件
        for task in tasks:
            if task.id not in self.active_task_widgets:
                widget = ExportProgressWidget(task)
                widget.task_clicked.connect(self.on_task_clicked)
                self.active_task_widgets[task.id] = widget

                # 插入到布局中（在拉伸之前）
                self.active_tasks_layout.insertWidget(
                    self.active_tasks_layout.count() - 1, widget
                )
            else:
                # 更新现有部件
                widget = self.active_task_widgets[task.id]
                widget.task = task
                widget.update_display()

    def update_speed_chart(self, tasks: List[ExportTask]):
        """更新速度图表"""
        # 计算总体导出速度
        total_speed = 0
        active_count = 0

        for task in tasks:
            if task.status == ExportStatus.PROCESSING and task.started_at:
                elapsed_time = time.time() - task.started_at
                if elapsed_time > 0 and task.progress > 0:
                    # 简化的速度计算（假设平均文件大小）
                    estimated_size = 100  # MB (假设值)
                    processed_size = estimated_size * (task.progress / 100)
                    speed = processed_size / elapsed_time  # MB/s
                    total_speed += speed
                    active_count += 1

        # 添加到速度历史
        self.speed_chart.add_speed_point(total_speed)

    def on_task_clicked(self, task_id: str):
        """任务点击事件"""
        # 查找任务详情
        task = None
        for t in self.tasks:
            if t.id == task_id:
                task = t
                break

        if task:
            self.show_task_details(task)

    def show_task_details(self, task: ExportTask):
        """显示任务详情"""
        # 这里可以实现任务详情对话框
        self.logger.info(f"Show task details: {task.id}")

    def cleanup(self):
        """清理资源"""
        try:
            self.update_timer.stop()
        except Exception:
            self.logger.debug("Operation failed")

    def update_theme(self, is_dark: bool = True):
        """更新主题"""
        if is_dark:
            self.setStyleSheet("""
                QGroupBox {
                    border: 1px solid #3a3a3a;
                    border-radius: 4px;
                    margin-top: 8px;
                    padding-top: 8px;
                    color: #ffffff;
                }
                QProgressBar {
                    border: 1px solid #3a3a3a;
                    border-radius: 4px;
                    text-align: center;
                    background-color: #2d2d2d;
                }
                QProgressBar::chunk {
                    background-color: #2962FF;
                }
            """)
        else:
            self.setStyleSheet("""
                QGroupBox {
                    border: 1px solid #d0d0d0;
                    border-radius: 4px;
                    margin-top: 8px;
                    padding-top: 8px;
                    color: #000000;
                }
                QProgressBar {
                    border: 1px solid #d0d0d0;
                    border-radius: 4px;
                    text-align: center;
                    background-color: #f5f5f5;
                }
                QProgressBar::chunk {
                    background-color: #2196F3;
                }
            """)


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