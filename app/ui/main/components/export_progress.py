#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
导出进度组件
显示导出队列和任务状态
"""

from typing import List, Optional
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QPushButton, QTableWidget, QTableWidgetItem)
from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QColor

from ....export.export_system import ExportTask
from ....core.logger import Logger


class ExportQueueWidget(QWidget):
    """导出队列部件"""

    task_selected = Signal(str)
    task_action = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = Logger.get_logger(__name__)
        self.tasks: List[ExportTask] = []
        self.setup_ui()
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_queue_display)
        self.update_timer.start(1000)

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 队列状态
        status_layout = QHBoxLayout()
        self.queue_status_label = QLabel("队列状态: 0个任务")
        self.clear_completed_btn = QPushButton("清除已完成")
        self.clear_completed_btn.clicked.connect(self.clear_completed)
        status_layout.addWidget(self.queue_status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.clear_completed_btn)

        # 任务表格
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(6)
        self.task_table.setHorizontalHeaderLabels([
            "任务ID", "项目名称", "状态", "进度", "输出路径", "操作"
        ])
        self.task_table.horizontalHeader().setStretchLastSection(True)
        self.task_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.task_table.itemSelectionChanged.connect(self.on_task_selected)

        # 操作按钮
        actions_layout = QHBoxLayout()
        self.start_btn = QPushButton("开始")
        self.pause_btn = QPushButton("暂停")
        self.cancel_btn = QPushButton("取消")
        self.remove_btn = QPushButton("移除")

        self.start_btn.clicked.connect(lambda: self.task_action.emit("start", ""))
        self.pause_btn.clicked.connect(lambda: self.task_action.emit("pause", ""))
        self.cancel_btn.clicked.connect(lambda: self.task_action.emit("cancel", ""))
        self.remove_btn.clicked.connect(lambda: self.task_action.emit("remove", ""))

        actions_layout.addWidget(self.start_btn)
        actions_layout.addWidget(self.pause_btn)
        actions_layout.addWidget(self.cancel_btn)
        actions_layout.addWidget(self.remove_btn)

        layout.addLayout(status_layout)
        layout.addWidget(self.task_table)
        layout.addLayout(actions_layout)

    def update_tasks(self, tasks: List[ExportTask]):
        """更新任务列表"""
        self.tasks = tasks
        self.update_queue_display()

    def update_queue_display(self):
        """更新队列显示"""
        self.task_table.setRowCount(len(self.tasks))

        for i, task in enumerate(self.tasks):
            # 任务ID
            self.task_table.setItem(i, 0, QTableWidgetItem(task.id[:8] + "..."))

            # 项目名称
            project_name = task.metadata.get("project_name", "未知项目")
            self.task_table.setItem(i, 1, QTableWidgetItem(project_name))

            # 状态
            status_item = QTableWidgetItem(task.status.value)
            status_item.setBackground(self.get_status_color(task.status))
            self.task_table.setItem(i, 2, status_item)

            # 进度
            progress_item = QTableWidgetItem(f"{task.progress:.1f}%")
            self.task_table.setItem(i, 3, progress_item)

            # 输出路径
            output_path = task.output_path
            if len(output_path) > 50:
                output_path = "..." + output_path[-47:]
            self.task_table.setItem(i, 4, QTableWidgetItem(output_path))

            # 操作按钮
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)

            if task.status.value in ["pending", "queued"]:
                start_btn = QPushButton("开始")
                start_btn.clicked.connect(lambda checked, tid=task.id: self.task_action.emit("start", tid))
                actions_layout.addWidget(start_btn)

            if task.status.value == "processing":
                pause_btn = QPushButton("暂停")
                pause_btn.clicked.connect(lambda checked, tid=task.id: self.task_action.emit("pause", tid))
                actions_layout.addWidget(pause_btn)

                cancel_btn = QPushButton("取消")
                cancel_btn.clicked.connect(lambda checked, tid=task.id: self.task_action.emit("cancel", tid))
                actions_layout.addWidget(cancel_btn)

            if task.status.value in ["completed", "failed"]:
                remove_btn = QPushButton("移除")
                remove_btn.clicked.connect(lambda checked, tid=task.id: self.task_action.emit("remove", tid))
                actions_layout.addWidget(remove_btn)

            actions_layout.addStretch()
            self.task_table.setCellWidget(i, 5, actions_widget)

        # 更新状态标签
        pending_count = len([t for t in self.tasks if t.status.value in ["pending", "queued"]])
        processing_count = len([t for t in self.tasks if t.status.value == "processing"])
        completed_count = len([t for t in self.tasks if t.status.value == "completed"])
        failed_count = len([t for t in self.tasks if t.status.value == "failed"])

        status_text = f"队列状态: {len(self.tasks)}个任务 | "
        status_text += f"待处理: {pending_count} | 处理中: {processing_count} | "
        status_text += f"已完成: {completed_count} | 失败: {failed_count}"
        self.queue_status_label.setText(status_text)

    def get_status_color(self, status) -> QColor:
        """获取状态颜色"""
        colors = {
            "pending": QColor(200, 200, 200),
            "queued": QColor(255, 200, 0),
            "processing": QColor(0, 150, 255),
            "completed": QColor(0, 200, 0),
            "failed": QColor(255, 0, 0),
            "cancelled": QColor(150, 150, 150)
        }
        return colors.get(status.value, QColor(200, 200, 200))

    def on_task_selected(self):
        """任务选择事件"""
        selected_items = self.task_table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            if row < len(self.tasks):
                self.task_selected.emit(self.tasks[row].id)

    def clear_completed(self):
        """清除已完成的任务"""
        self.task_action.emit("clear_completed", "")

    def get_selected_task_id(self) -> Optional[str]:
        """获取选中的任务ID"""
        selected_items = self.task_table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            if row < len(self.tasks):
                return self.tasks[row].id
        return None
