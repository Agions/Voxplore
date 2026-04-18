#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Voxplore 应用启动器
负责应用程序的启动、初始化和运行
"""

import sys
import os
import traceback
from typing import List, Optional

# 自动检测无头环境，设置 Qt 平台
def _setup_headless_platform():
    """检测无头环境并设置合适的 Qt 平台。"""
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        os.environ.setdefault("QT_LOGGING_TO_STDOUT", "1")

_setup_headless_platform()

from PySide6.QtWidgets import QApplication, QSplashScreen, QMessageBox
from PySide6.QtCore import QThread, Qt
from PySide6.QtGui import QPixmap, QPainter, QFont, QColor

from .core.config_manager import ConfigManager
from .core.logger import Logger
from .core.icon_manager import init_icon_manager
from .core.project_manager import ProjectManager
from .core.project_template_manager import ProjectTemplateManager
from .core.project_settings_manager import ProjectSettingsManager
from .utils.error_handler import show_error_dialog
from .ui.main.main_window import MainWindow
from .core.application import ApplicationState


class SplashScreen(QSplashScreen):
    """启动画面"""

    def __init__(self):
        # 创建启动画面
        splash_pixmap = QPixmap(600, 400)
        splash_pixmap.fill(QColor("#1a1a1a"))

        painter = QPainter(splash_pixmap)
        painter.setPen(QColor("#00BCD4"))

        # 绘制Logo
        logo_font = QFont("Arial", 48, QFont.Weight.Bold)
        painter.setFont(logo_font)
        painter.drawText(splash_pixmap.rect(),
                        int(Qt.AlignmentFlag.AlignCenter), "Voxplore")

        # 绘制版本信息
        version_font = QFont("Arial", 14)
        painter.setFont(version_font)
        painter.setPen(QColor("#B0BEC5"))
        version_rect = splash_pixmap.rect().adjusted(0, 100, 0, -100)
        painter.drawText(version_rect,
                        int(Qt.AlignmentFlag.AlignCenter), "专业AI视频编辑器 v2.0.0")

        # 绘制加载信息
        loading_font = QFont("Arial", 12)
        painter.setFont(loading_font)
        painter.setPen(QColor("#90A4AE"))
        loading_rect = splash_pixmap.rect().adjusted(0, 150, 0, -50)
        painter.drawText(loading_rect,
                        int(Qt.AlignmentFlag.AlignCenter), "正在加载组件...")

        painter.end()

        super().__init__(splash_pixmap)
        self.setFixedSize(600, 400)


class ApplicationLauncher:
    """应用程序启动器"""

    def __init__(self):
        self.main_window: Optional[MainWindow] = None
        self.splash_screen: Optional[SplashScreen] = None
        self.logger: Optional[Logger] = None
        self.config_manager: Optional[ConfigManager] = None

    def launch(self, argv: List[str]) -> int:
        """启动应用程序"""
        try:
            # 确保QApplication已经创建
            app = QApplication.instance()
            if not app:
                app = QApplication(argv)

            # 显示启动画面
            self.splash_screen = SplashScreen()
            self.splash_screen.show()

            # 处理Qt事件
            app.processEvents()

            # 初始化日志系统
            self._initialize_logging()

            # 创建应用配置
            config = self._create_application_config()

            # 保存配置管理器
            self.config_manager = config

            # 初始化项目管理系统
            self._initialize_project_management()

            # 创建主窗口
            self._create_main_window()

            # 连接信号
            self._connect_signals()

            # 启动应用程序
            self._start_application()

            # 隐藏启动画面，显示主窗口
            if self.splash_screen:
                self.splash_screen.finish(self.main_window)

            if self.main_window:
                self.main_window.show()

            # 运行应用程序
            return self._run_application()

        except Exception as e:
            self._handle_launch_error(e)
            return 1

    def _initialize_logging(self) -> None:
        """初始化日志系统"""
        try:
            # 创建日志管理器
            self.logger = Logger("Voxplore")

            self.logger.info("初始化日志系统")

            # 简化的错误处理
            import sys
            def handle_exception(exc_type, exc_value, exc_traceback):
                self.logger.error(f"未捕获的异常: {exc_value}")
                show_error_dialog(None, "错误", f"应用程序遇到错误: {exc_value}")

            sys.excepthook = handle_exception

        except Exception as e:
            print(f"Failed to initialize logging: {e}")
            # 使用print作为最后的日志手段
            traceback.print_exc()

    def _create_application_config(self) -> ConfigManager:
        """创建应用程序配置"""
        config = ConfigManager()

        # 初始化图标管理器
        init_icon_manager()

        return config

    def _initialize_project_management(self) -> None:
        """初始化项目管理系统"""
        try:
            if self.splash_screen:
                self.splash_screen.showMessage("正在初始化项目管理系统...",
                                           int(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter),
                                           QColor("#FFFFFF"))

            # 创建项目管理器
            self.project_manager = ProjectManager(self.config_manager)

            # 创建模板管理器
            self.template_manager = ProjectTemplateManager(self.config_manager)

            # 创建设置管理器
            self.settings_manager = ProjectSettingsManager(self.config_manager)

            self.logger.info("Project management system initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize project management: {e}")
            raise

    def _initialize_application(self, argv: List[str]) -> bool:
        """初始化应用程序"""
        try:
            if self.splash_screen:
                self.splash_screen.showMessage("正在初始化应用程序核心...",
                                           int(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter),
                                           QColor("#FFFFFF"))

            # 初始化应用程序
            if not self.application.initialize(argv):
                self.logger.error("Failed to initialize application")
                return False

            # 等待初始化完成
            if not self._wait_for_application_ready():
                self.logger.error("Application initialization timeout")
                return False

            self.logger.info("Application initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize application: {e}")
            self.logger.error(traceback.format_exc())
            return False

    def _create_main_window(self) -> None:
        """创建主窗口"""
        try:
            if self.splash_screen:
                self.splash_screen.showMessage("正在创建用户界面...",
                                           int(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter),
                                           QColor("#FFFFFF"))

            # 创建简化版主窗口
            self.main_window = MainWindow()

            self.logger.info("Main window created successfully")

        except Exception as e:
            self.logger.error(f"Failed to create main window: {e}")
            self.logger.error(traceback.format_exc())
            raise

    def _connect_signals(self) -> None:
        """连接信号"""
        if not self.application:
            return

        # 应用程序状态信号
        self.application.state_changed.connect(self._on_application_state_changed)

        # 应用程序错误信号
        self.application.error_occurred.connect(self._on_application_error)

        # 主窗口信号（如果存在）
        if self.main_window:
            self.main_window.error_occurred.connect(self._on_window_error)

    def _start_application(self) -> None:
        """启动应用程序"""
        try:
            if self.splash_screen:
                self.splash_screen.showMessage("正在启动应用程序...",
                                           int(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter),
                                           QColor("#FFFFFF"))

            # 启动应用程序
            if not self.application.start():
                self.logger.error("Failed to start application")
                raise RuntimeError("Failed to start application")

            self.logger.info("Application started successfully")

        except Exception as e:
            self.logger.error(f"Failed to start application: {e}")
            raise

    def _run_application(self) -> int:
        """运行应用程序"""
        try:
            self.logger.info("Starting application main loop")

            # 运行应用程序
            exit_code = self.application.run()

            self.logger.info(f"Application exited with code: {exit_code}")
            return exit_code

        except Exception as e:
            self.logger.error(f"Error running application: {e}")
            self.logger.error(traceback.format_exc())
            return 1

    def _wait_for_application_ready(self, timeout: int = 30) -> bool:
        """等待应用程序就绪"""
        import time

        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.application and self.application.is_ready():
                return True

            # 处理Qt事件
            app = QApplication.instance()
            if app:
                app.processEvents()

            # 短暂等待
            QThread.msleep(100)

        return False

    def _on_application_state_changed(self, state: ApplicationState) -> None:
        """应用程序状态变化处理"""
        state_messages = {
            ApplicationState.INITIALIZING: "正在初始化...",
            ApplicationState.STARTING: "正在启动...",
            ApplicationState.READY: "应用程序已就绪",
            ApplicationState.RUNNING: "正在运行",
            ApplicationState.PAUSED: "已暂停",
            ApplicationState.SHUTTING_DOWN: "正在关闭...",
            ApplicationState.ERROR: "发生错误"
        }

        message = state_messages.get(state, f"状态: {state.value}")

        if self.logger:
            self.logger.info(f"Application state changed to: {state.value}")

        if self.splash_screen:
            self.splash_screen.showMessage(message,
                                       int(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter),
                                       QColor("#FFFFFF"))

    def _on_application_error(self, error_type: str, error_message: str) -> None:
        """应用程序错误处理"""
        if self.logger:
            self.logger.error(f"Application error: {error_type} - {error_message}")

    def _on_window_error(self, error_type: str, error_message: str) -> None:
        """窗口错误处理"""
        if self.logger:
            self.logger.error(f"Window error: {error_type} - {error_message}")

    def _on_error_occurred(self, error_info) -> None:
        """错误处理"""
        if self.logger:
            self.logger.error(f"Error occurred: {error_info.error_type} - {error_info.message}")

    def _handle_launch_error(self, error: Exception) -> None:
        """处理启动错误"""
        error_msg = f"Failed to launch application: {str(error)}"

        if self.logger:
            self.logger.error(error_msg)
            self.logger.error(traceback.format_exc())
        else:
            print(error_msg)
            traceback.print_exc()

        # 尝试显示错误对话框
        try:
            app = QApplication.instance()
            if app:
                QMessageBox.critical(None, "启动失败",
                                   f"应用程序启动失败：\n\n{str(error)}\n\n请检查日志文件获取详细信息。")
        except Exception:
            self.logger.debug("Operation failed")


def main() -> int:
    """主函数"""
    try:
        # 检查Python版本
        if sys.version_info < (3, 8):
            print("Error: Python 3.8 or higher is required")
            return 1

        # 创建Qt应用程序
        qt_app = QApplication(sys.argv)
        qt_app.setApplicationName("Voxplore")
        qt_app.setApplicationVersion("2.0.0")
        qt_app.setOrganizationName("Agions")

        # 设置应用程序样式
        qt_app.setStyle("Fusion")

        # 创建并运行启动器
        launcher = ApplicationLauncher()
        exit_code = launcher.launch(sys.argv)

        # 清理资源
        if launcher.application:
            launcher.application.shutdown()

        return exit_code

    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        return 0

    except Exception as e:
        print(f"Fatal error: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)