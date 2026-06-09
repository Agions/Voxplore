#!/usr/bin/env python3

"""
导出进度监控组件
提供实时导出进度监控和状态显示
"""

import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QGroupBox,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from scenefab.logger import Logger
from scenefab.services.export import ExportStatus, ExportTask
from scenefab.ui.common.theme_mixin import ThemeAwareMixin, ThemeColors
from scenefab.ui.main.components._progress_widget import ExportProgressWidget

from ...main.components.export_stats import ExportStatisticsWidget
from ...main.components.monitor_widgets import PerformanceChart


class ExportMonitorWidget(QWidget, ThemeAwareMixin):
    """导出监控主部件"""

    def __init__(self, export_system, parent=None):
        super().__init__(parent)
        self.export_system = export_system
        self.logger = Logger.get_logger(__name__)
        self.tasks: list[ExportTask] = []
        self.active_task_widgets: dict[str, ExportProgressWidget] = {}
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

        self.speed_chart = PerformanceChart("导出速度", max_value=50)
        self.speed_chart.setMinimumHeight(150)
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
            active_tasks = [
                t
                for t in tasks
                if t.status.value in ["processing", "queued", "pending"]
            ]

            # 更新统计信息
            self.statistics_widget.update_statistics(tasks)

            # 更新活动任务显示
            self.update_active_tasks(active_tasks)

            # 更新速度图表
            self.update_speed_chart(active_tasks)

        except Exception as e:
            self.logger.error(f"Failed to update monitor display: {e}")

    def update_active_tasks(self, tasks: list[ExportTask]):
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

    def update_speed_chart(self, tasks: list[ExportTask]):
        """更新速度图表"""
        # 计算总体导出速度
        total_speed = 0
        active_count = 0

        for task in tasks:
            if task.status == ExportStatus.PROCESSING and task.started_at:  # type: ignore[attr-defined]
                elapsed_time = time.time() - task.started_at
                if elapsed_time > 0 and task.progress > 0:
                    # 简化的速度计算（假设平均文件大小）
                    estimated_size = 100  # MB (假设值)
                    processed_size = estimated_size * (task.progress / 100)
                    speed = processed_size / elapsed_time  # MB/s
                    total_speed += speed  # type: ignore[assignment]
                    active_count += 1

        # 添加到速度历史
        self.speed_chart.add_data_point(total_speed)

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
        except RuntimeError as e:
            self.logger.debug(f"Timer already stopped: {e}")
        except Exception as e:
            self.logger.warning(f"Cleanup failed: {e}")

    def _get_theme_stylesheet(self, is_dark: bool) -> str:
        """返回主题样式表"""
        border = ThemeColors.BORDER_DARK if is_dark else ThemeColors.BORDER_LIGHT
        text = ThemeColors.TEXT_DARK if is_dark else ThemeColors.TEXT_LIGHT
        progress_bg = (
            ThemeColors.BG_ELEVATED_DARK if is_dark else ThemeColors.BG_SURFACE_LIGHT
        )
        return f"""
            QGroupBox {{
                border: 1px solid {border};
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
                color: {text};
            }}
            QProgressBar {{
                border: 1px solid {border};
                border-radius: 4px;
                text-align: center;
                background-color: {progress_bg};
            }}
            QProgressBar::chunk {{
                background-color: #388BFD;
            }}
        """
