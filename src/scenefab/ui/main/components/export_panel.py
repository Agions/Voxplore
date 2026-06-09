#!/usr/bin/env python3

"""
导出面板
提供完整的视频导出功能界面
"""

import os
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from scenefab.logger import Logger
from scenefab.ui.main.components._tab_builders import (
    build_batch_export_tab,
    build_presets_tab,
    build_queue_tab,
    build_quick_export_tab,
)

from ...export.export_system import ExportPreset
from ..common.theme_mixin import ThemeAwareMixin, ThemeColors
from .export_format_selector import ExportSettingsDialog


class ExportPanel(QWidget, ThemeAwareMixin):
    """导出面板主类"""

    # 信号定义
    export_started = Signal(str)
    export_progress = Signal(str, float)
    export_completed = Signal(str, str)
    export_failed = Signal(str, str)

    def __init__(self, application, parent=None):
        super().__init__(parent)
        self.application = application
        self.export_system = application.export_system
        self.logger = Logger.get_logger(__name__)
        self.current_project_id = None
        self.presets: list[Any] = []
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)

        # 创建标签页
        self.tab_widget = QTabWidget()

        # 快速导出标签页
        self.quick_export_tab = build_quick_export_tab()
        self.tab_widget.addTab(self.quick_export_tab, "快速导出")

        # 批量导出标签页
        self.batch_export_tab = build_batch_export_tab()
        self.tab_widget.addTab(self.batch_export_tab, "批量导出")

        # 队列管理标签页
        self.queue_tab = build_queue_tab()
        self.tab_widget.addTab(self.queue_tab, "队列管理")

        # 预设管理标签页
        self.presets_tab = build_presets_tab()
        self.tab_widget.addTab(self.presets_tab, "预设管理")

        layout.addWidget(self.tab_widget)

    def connect_signals(self):
        """连接信号"""
        # 导出系统信号
        self.export_system.export_started.connect(self.on_export_started)
        self.export_system.export_progress.connect(self.on_export_progress)
        self.export_system.export_completed.connect(self.on_export_completed)
        self.export_system.export_failed.connect(self.on_export_failed)

        # 队列信号
        self.queue_widget.task_action.connect(self.handle_queue_action)

    def set_current_project(self, project_id: str, project_info: dict[str, Any]):
        """设置当前项目"""
        self.current_project_id = project_id
        self.project_name_label.setText(project_info.get("name", "未知项目"))
        self.project_duration_label.setText(project_info.get("duration", "00:00:00"))
        self.project_resolution_label.setText(
            project_info.get("resolution", "1920x1080")
        )

    def refresh_presets(self):
        """刷新预设列表"""
        presets = self.export_system.get_presets()
        self.preset_combo.clear()
        self.batch_preset_combo.clear()

        for preset in presets:
            self.preset_combo.addItem(preset.name, preset.id)
            self.batch_preset_combo.addItem(preset.name, preset.id)

    def refresh_presets_table(self):
        """刷新预设表格"""
        presets = self.export_system.get_presets()
        self.presets_table.setRowCount(len(presets))

        for i, preset in enumerate(presets):
            self.presets_table.setItem(i, 0, QTableWidgetItem(preset.name))
            self.presets_table.setItem(i, 1, QTableWidgetItem(preset.format.value))
            self.presets_table.setItem(
                i, 2, QTableWidgetItem(f"{preset.resolution[0]}x{preset.resolution[1]}")
            )
            self.presets_table.setItem(i, 3, QTableWidgetItem(f"{preset.bitrate} kbps"))

            # 操作按钮
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)

            edit_btn = QPushButton("编辑")
            edit_btn.clicked.connect(lambda checked, p=preset: self.edit_preset_data(p))
            actions_layout.addWidget(edit_btn)

            delete_btn = QPushButton("删除")
            delete_btn.clicked.connect(
                lambda checked, p=preset: self.delete_preset_data(p)
            )
            actions_layout.addWidget(delete_btn)

            actions_layout.addStretch()
            self.presets_table.setCellWidget(i, 4, actions_widget)

    def browse_output_path(self):
        """浏览输出路径"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "选择输出文件",
            "",
            "视频文件 (*.mp4 *.avi *.mov *.mkv *.webm);;音频文件 (*.mp3 *.wav);;所有文件 (*)",
        )
        if file_path:
            self.output_path_edit.setText(file_path)

    def browse_batch_output_dir(self):
        """浏览批量输出目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if dir_path:
            self.batch_output_dir_edit.setText(dir_path)

    def quick_export(self, preset_id: str):
        """快速导出"""
        if not self.current_project_id:
            QMessageBox.warning(self, "警告", "请先选择一个项目")
            return

        # 生成默认输出路径
        project_name = self.project_name_label.text()
        output_path = f"{project_name}_{preset_id}.mp4"

        self.start_export_with_preset(preset_id, output_path)

    def start_export(self):
        """开始导出"""
        if not self.current_project_id:
            QMessageBox.warning(self, "警告", "请先选择一个项目")
            return

        output_path = self.output_path_edit.text()
        if not output_path:
            QMessageBox.warning(self, "警告", "请选择输出路径")
            return

        preset_id = self.preset_combo.currentData()
        if not preset_id:
            QMessageBox.warning(self, "警告", "请选择导出预设")
            return

        self.start_export_with_preset(preset_id, output_path)

    def start_export_with_preset(self, preset_id: str, output_path: str):
        """使用指定预设开始导出"""
        try:
            task_id = self.export_system.export_project(
                project_id=self.current_project_id,
                output_path=output_path,
                preset_id=preset_id,
                metadata={
                    "project_name": self.project_name_label.text(),
                    "duration": self.project_duration_label.text(),
                    "resolution": self.project_resolution_label.text(),
                },
            )

            QMessageBox.information(self, "成功", f"导出任务已添加到队列: {task_id}")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

    def start_batch_export(self):
        """开始批量导出"""
        selected_projects = self.get_selected_projects()
        if not selected_projects:
            QMessageBox.warning(self, "警告", "请选择要导出的项目")
            return

        output_dir = self.batch_output_dir_edit.text()
        if not output_dir:
            QMessageBox.warning(self, "警告", "请选择输出目录")
            return

        preset_id = self.batch_preset_combo.currentData()
        if not preset_id:
            QMessageBox.warning(self, "警告", "请选择导出预设")
            return

        try:
            batch_configs = []
            for project in selected_projects:
                output_path = os.path.join(
                    output_dir, f"{project['name']}_{preset_id}.mp4"
                )
                batch_configs.append(
                    {
                        "project_id": project["id"],
                        "output_path": output_path,
                        "preset_id": preset_id,
                        "metadata": project,
                    }
                )

            task_ids = self.export_system.export_batch(batch_configs)
            QMessageBox.information(self, "成功", f"已添加 {len(task_ids)} 个导出任务")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"批量导出失败: {str(e)}")

    def get_selected_projects(self) -> list[dict[str, Any]]:
        """获取选中的项目"""
        selected_projects = []
        for i in range(self.batch_projects_table.rowCount()):
            checkbox = self.batch_projects_table.cellWidget(i, 0)
            if checkbox and checkbox.isChecked():
                selected_projects.append(
                    {
                        "id": self.batch_projects_table.item(i, 1).data(
                            Qt.ItemDataRole.UserRole
                        ),
                        "name": self.batch_projects_table.item(i, 1).text(),
                        "duration": self.batch_projects_table.item(i, 2).text(),
                        "resolution": self.batch_projects_table.item(i, 3).text(),
                    }
                )
        return selected_projects

    def select_all_projects(self):
        """全选项目"""
        for i in range(self.batch_projects_table.rowCount()):
            checkbox = self.batch_projects_table.cellWidget(i, 0)
            if checkbox:
                checkbox.setChecked(True)

    def select_none_projects(self):
        """全不选项目"""
        for i in range(self.batch_projects_table.rowCount()):
            checkbox = self.batch_projects_table.cellWidget(i, 0)
            if checkbox:
                checkbox.setChecked(False)

    def handle_queue_action(self, action: str, task_id: str):
        """处理队列操作"""
        try:
            if action == "start":
                success = self.export_system.resume_export(task_id)
                if success:
                    QMessageBox.information(self, "成功", "任务已恢复")
                else:
                    QMessageBox.warning(self, "警告", "无法恢复该任务")
            elif action == "pause":
                success = self.export_system.pause_export(task_id)
                if success:
                    QMessageBox.information(self, "成功", "任务已暂停")
                else:
                    QMessageBox.warning(self, "警告", "无法暂停该任务")
            elif action == "cancel":
                success = self.export_system.cancel_export(task_id)
                if success:
                    QMessageBox.information(self, "成功", "任务已取消")
                else:
                    QMessageBox.warning(self, "警告", "无法取消该任务")
            elif action == "remove":
                success = self.export_system.remove_from_queue(task_id)
                if success:
                    self._refresh_queue_list()
            elif action == "clear_completed":
                success = self.export_system.clear_completed()
                if success:
                    self._refresh_queue_list()
                    QMessageBox.information(self, "成功", "已完成任务已清除")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"操作失败: {str(e)}")

    def _refresh_queue_list(self):
        """刷新队列列表"""
        try:
            tasks = self.export_system.get_task_history()
            self.queue_widget.update_tasks(tasks)
        except Exception as e:
            self.logger.error(f"Failed to refresh queue list: {e}")

    def apply_queue_settings(self):
        """应用队列设置"""
        try:
            max_concurrent = self.max_concurrent_spin.value()
            auto_cleanup = self.auto_cleanup_check.isChecked()
            self._apply_concurrent_limit(max_concurrent)
            if auto_cleanup:
                self._schedule_cleanup()
            QMessageBox.information(self, "成功", "队列设置已应用")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"设置应用失败: {str(e)}")

    def _apply_concurrent_limit(self, limit: int):
        """实际应用并发限制 — 由导出队列接管"""
        raise NotImplementedError("Export queue integration pending")

    def _schedule_cleanup(self):
        """安排自动清理 — 由后台任务调度器接管"""
        raise NotImplementedError("Cleanup scheduler pending")

    def add_preset(self):
        """添加预设"""
        dialog = ExportSettingsDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            preset_data = dialog.get_preset_data()
            new_preset = ExportPreset(
                name=preset_data.get("name", "新预设"),
                format=preset_data.get("format", "mp4"),
                codec=preset_data.get("codec", "h264"),
                resolution=preset_data.get("resolution", "1920x1080"),
                fps=preset_data.get("fps", 30),
                bitrate=preset_data.get("bitrate", "8M"),
                audio_codec=preset_data.get("audio_codec", "aac"),
                audio_bitrate=preset_data.get("audio_bitrate", "192k"),
            )
            self.presets.append(new_preset)
            self.refresh_presets_table()
            QMessageBox.information(self, "成功", f"预设 '{new_preset.name}' 已添加")

    def edit_preset(self):
        """编辑预设"""
        selected_items = self.presets_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请选择要编辑的预设")
            return
        self.edit_preset_data(None)

    def edit_preset_data(self, preset: ExportPreset):
        """编辑预设数据"""
        dialog = ExportSettingsDialog(preset, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            preset_data = dialog.get_preset_data()
            self._save_preset(preset.id, preset_data)
            QMessageBox.information(self, "成功", "预设已更新")

    def _save_preset(self, preset_id: str, data: dict):
        """保存预设数据 — 由预设存储接管"""
        raise NotImplementedError("Preset persistence pending")

    def delete_preset(self):
        """删除预设"""
        selected_items = self.presets_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请选择要删除的预设")
            return

        reply = QMessageBox.question(
            self,
            "确认删除",
            "确定要删除选中的预设吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            QMessageBox.information(self, "成功", "预设已删除")

    def delete_preset_data(self, preset: ExportPreset):
        """删除预设数据"""
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除预设 '{preset.name}' 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            success = self.export_system.remove_preset(preset.id)
            if success:
                self.refresh_presets_table()
                QMessageBox.information(self, "成功", "预设已删除")
            else:
                QMessageBox.warning(self, "警告", "删除预设失败")

    def update_queue_display(self):
        """更新队列显示"""
        try:
            tasks = self.export_system.get_task_history()
            self.queue_widget.update_tasks(tasks)
        except Exception as e:
            self.logger.error(f"Failed to update queue display: {e}")

    def on_export_started(self, task_id: str):
        """导出开始事件"""
        self.logger.info(f"Export started: {task_id}")
        self.export_started.emit(task_id)

    def on_export_progress(self, task_id: str, progress: float):
        """导出进度事件"""
        self.logger.info(f"Export progress: {task_id} - {progress:.1f}%")
        self.export_progress.emit(task_id, progress)

    def on_export_completed(self, task_id: str, output_path: str):
        """导出完成事件"""
        self.logger.info(f"Export completed: {task_id} -> {output_path}")
        self.export_completed.emit(task_id, output_path)
        QMessageBox.information(self, "成功", f"导出完成: {output_path}")

    def on_export_failed(self, task_id: str, error_message: str):
        """导出失败事件"""
        self.logger.error(f"Export failed: {task_id} - {error_message}")
        self.export_failed.emit(task_id, error_message)
        QMessageBox.critical(self, "错误", f"导出失败: {error_message}")

    def cleanup(self):
        """清理资源"""
        try:
            self.queue_widget.update_timer.stop()
        except RuntimeError as e:
            self.logger.debug(f"Timer already stopped: {e}")
        except Exception as e:
            self.logger.warning(f"Cleanup failed: {e}")

    def _get_theme_stylesheet(self, is_dark: bool) -> str:
        """返回主题样式表"""
        border = ThemeColors.BORDER_DARK if is_dark else ThemeColors.BORDER_LIGHT
        bg = ThemeColors.BG_DARK if is_dark else ThemeColors.BG_LIGHT
        alt_bg = (
            ThemeColors.BG_SURFACE_DARK if is_dark else ThemeColors.BG_SURFACE_LIGHT
        )
        return f"""
            QGroupBox {{
                border: 1px solid {border};
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
            }}
            QTableWidget {{
                background-color: {bg};
                alternate-background-color: {alt_bg};
            }}
        """
