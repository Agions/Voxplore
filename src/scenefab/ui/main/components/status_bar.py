"""
状态栏组件 - 显示应用程序状态信息
"""

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLabel, QProgressBar, QStatusBar

from ..common.theme_mixin import ThemeAwareMixin, ThemeColors


class StatusBar(QStatusBar, ThemeAwareMixin):
    """状态栏组件"""

    def __init__(self):
        super().__init__()

        self.status_label = None
        self.memory_label = None
        self.project_label = None
        self.progress_bar = None
        self.progress_timer = None
        self.permanent_widgets = []

        self._setup_ui()
        self._setup_timers()

    def _setup_ui(self) -> None:
        """设置UI"""
        # 设置状态栏属性
        self.setObjectName("status_bar")
        self.setSizeGripEnabled(False)

        # 创建状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("status_text")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 12px;
                padding: 2px 8px;
            }
        """)
        self.addWidget(self.status_label)

        # 添加分隔符
        self._add_separator()

        # 创建项目标签
        self.project_label = QLabel("未打开项目")
        self.project_label.setObjectName("project_info")
        self.project_label.setStyleSheet("""
            QLabel {
                color: #CCCCCC;
                font-size: 11px;
                padding: 2px 8px;
            }
        """)
        self.addPermanentWidget(self.project_label)

        # 添加分隔符
        self._add_separator()

        # 创建内存标签
        self.memory_label = QLabel("内存: -- MB")
        self.memory_label.setObjectName("memory_info")
        self.memory_label.setStyleSheet("""
            QLabel {
                color: #CCCCCC;
                font-size: 11px;
                padding: 2px 8px;
            }
        """)
        self.addPermanentWidget(self.memory_label)

        # 创建进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(100)
        self.progress_bar.setMaximumHeight(15)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 3px;
                text-align: center;
                font-size: 10px;
                background-color: #333333;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
                border-radius: 2px;
            }
        """)
        self.addPermanentWidget(self.progress_bar)

    def _add_separator(self) -> None:
        """添加分隔符"""
        separator = QLabel("|")
        separator.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 11px;
                padding: 0 4px;
            }
        """)
        self.addPermanentWidget(separator)
        self.permanent_widgets.append(separator)

    def _setup_timers(self) -> None:
        """设置定时器"""
        # 状态消息定时器
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._clear_temporary_status)

    def update_status(self, message: str, duration: int = 0) -> None:
        """更新状态信息"""
        if self.status_label:
            self.status_label.setText(message)

        if duration > 0:
            self.status_timer.start(duration)

    def _clear_temporary_status(self) -> None:
        """清除临时状态"""
        self.status_timer.stop()
        if self.status_label:
            self.status_label.setText("就绪")

    def update_project_info(self, project_name: str) -> None:
        """更新项目信息"""
        if self.project_label:
            self.project_label.setText(f"项目: {project_name}")

    def update_memory_usage(self, memory_mb: float) -> None:
        """更新内存使用信息"""
        if self.memory_label:
            self.memory_label.setText(f"内存: {memory_mb:.0f} MB")

    def show_progress(self, maximum: int = 100) -> None:
        """显示进度条"""
        if self.progress_bar:
            self.progress_bar.setValue(0)
            self.progress_bar.setMaximum(maximum)
            self.progress_bar.setVisible(True)

    def update_progress(self, value: int) -> None:
        """更新进度"""
        if self.progress_bar:
            self.progress_bar.setValue(value)

    def hide_progress(self) -> None:
        """隐藏进度条"""
        if self.progress_bar:
            self.progress_bar.setVisible(False)

    def set_permanent_message(self, message: str) -> None:
        """设置永久消息"""
        # 移除现有永久消息
        for widget in self.permanent_widgets:
            if isinstance(widget, QLabel) and widget not in [
                self.project_label,
                self.memory_label,
            ]:
                self.removeWidget(widget)
                widget.deleteLater()

        # 添加新消息
        label = QLabel(message)
        label.setStyleSheet("""
            QLabel {
                color: #CCCCCC;
                font-size: 11px;
                padding: 2px 8px;
            }
        """)
        self.addPermanentWidget(label)
        self.permanent_widgets.append(label)

    def show_error(self, message: str) -> None:
        """显示错误信息"""
        if self.status_label:
            self.status_label.setText(f"错误: {message}")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #FF5252;
                    font-size: 12px;
                    padding: 2px 8px;
                    font-weight: bold;
                }
            """)

        # 3秒后恢复正常
        QTimer.singleShot(3000, self._restore_normal_style)

    def show_warning(self, message: str) -> None:
        """显示警告信息"""
        if self.status_label:
            self.status_label.setText(f"警告: {message}")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #FFC107;
                    font-size: 12px;
                    padding: 2px 8px;
                    font-weight: bold;
                }
            """)

        # 3秒后恢复正常
        QTimer.singleShot(3000, self._restore_normal_style)

    def show_success(self, message: str) -> None:
        """显示成功信息"""
        if self.status_label:
            self.status_label.setText(f"成功: {message}")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #4CAF50;
                    font-size: 12px;
                    padding: 2px 8px;
                    font-weight: bold;
                }
            """)

        # 3秒后恢复正常
        QTimer.singleShot(3000, self._restore_normal_style)

    def _restore_normal_style(self) -> None:
        """恢复正常样式"""
        if self.status_label:
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #FFFFFF;
                    font-size: 12px;
                    padding: 2px 8px;
                }
            """)

    def _get_theme_stylesheet(self, is_dark: bool) -> str:
        """返回主题样式表"""
        bg = ThemeColors.BG_DARK if is_dark else ThemeColors.BG_SURFACE_LIGHT
        text = ThemeColors.TEXT_DARK if is_dark else ThemeColors.TEXT_LIGHT
        secondary = (
            ThemeColors.TEXT_SECONDARY_DARK
            if is_dark
            else ThemeColors.TEXT_SECONDARY_LIGHT
        )
        border = ThemeColors.BORDER_DARK if is_dark else ThemeColors.BORDER_LIGHT
        return f"""
            QStatusBar {{
                background-color: {bg};
                color: {text};
                border-top: 1px solid {border};
            }}
            QStatusBar QLabel {{
                font-size: 11px;
                padding: 2px 8px;
                color: {secondary};
            }}
            QStatusBar QLabel#status_text {{
                font-size: 12px;
                color: {text};
            }}
        """

    def clear_all_messages(self) -> None:
        """清除所有消息"""
        self.update_status("就绪")
        self.hide_progress()

    def get_current_status(self) -> str:
        """获取当前状态"""
        if self.status_label:
            return self.status_label.text()
        return ""

    def resizeEvent(self, event) -> None:
        """大小改变事件"""
        super().resizeEvent(event)

        # 自动调整进度条宽度
        if self.progress_bar and self.progress_bar.isVisible():
            available_width = self.width() - 200  # 为其他标签留出空间
            self.progress_bar.setFixedWidth(min(150, available_width))
