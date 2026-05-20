"""
页面基类 - 所有页面的基类
提供统一的页面生命周期管理
"""

from typing import Dict, Any
from typing import Any as TypingAny

from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Signal


class BasePage(QWidget):
    """页面基类"""

    # 信号定义
    page_loaded = Signal()                    # 页面加载完成
    page_activated = Signal()                 # 页面激活
    page_deactivated = Signal()              # 页面停用
    status_changed = Signal(str)              # 状态变化
    error_occurred = Signal(str, str)         # 错误发生
    action_requested = Signal(str, object)    # 请求执行操作

    def __init__(self, page_id: str, title: str, application):
        super().__init__()

        self.page_id = page_id
        self.title = title
        self.application = application
        self.is_loaded = False
        self.is_active = False
        self.page_state = {}

        # 核心服务
        self.logger = application.get_service_by_name("logger")
        self.config_manager = application.get_service_by_name("config_manager")
        self.event_bus = application.get_service_by_name("event_bus")
        self.error_handler = application.get_service_by_name("error_handler")

        # 初始化UI
        self._setup_ui()
        self._create_layout()

        # 连接信号
        self._connect_signals()

    def _setup_ui(self) -> None:
        """设置UI"""
        self.setObjectName(f"{self.page_id}_page")
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(0)
        self.setLayout(self.main_layout)

    def _create_layout(self) -> None:
        """创建布局"""
        # 子类可以重写此方法来添加特定布局
        pass

    def _connect_signals(self) -> None:
        """连接信号"""
        # 监听应用程序事件
        if hasattr(self.application, 'state_changed'):
            self.application.state_changed.connect(self._on_application_state_changed)

        # 监听配置变化
        if self.config_manager and hasattr(self.config_manager, 'add_watcher'):
            self.config_manager.add_watcher(self._on_config_changed)

    def initialize(self) -> bool:
        """初始化页面"""
        # 子类必须重写此方法
        raise NotImplementedError("Subclasses must implement initialize()")

    def create_content(self) -> None:
        """创建页面内容"""
        # 子类必须重写此方法
        raise NotImplementedError("Subclasses must implement create_content()")

    def load(self) -> bool:
        """加载页面"""
        try:
            if not self.is_loaded:
                # 初始化页面
                if not self.initialize():
                    return False

                # 创建内容
                self.create_content()

                # 设置页面为已加载
                self.is_loaded = True

                # 发送加载完成信号
                self.page_loaded.emit()

                self.logger.info(f"Page '{self.title}' loaded successfully")
                return True

            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to load page '{self.title}': {str(e)}")
            return False

    def activate(self) -> None:
        """激活页面"""
        if not self.is_active:
            # 加载页面（如果未加载）
            if not self.load():
                return

            # 恢复页面状态
            self.restore_state()

            # 设置页面为激活状态
            self.is_active = True

            # 发送激活信号
            self.page_activated.emit()

            self.logger.info(f"Page '{self.title}' activated")

    def deactivate(self) -> None:
        """停用页面"""
        if self.is_active:
            # 保存页面状态
            self.save_state()

            # 设置页面为停用状态
            self.is_active = False

            # 发送停用信号
            self.page_deactivated.emit()

            self.logger.info(f"Page '{self.title}' deactivated")

    def save_state(self) -> None:
        """保存页面状态"""
        # 子类可以重写此方法来保存特定状态
        pass

    def restore_state(self) -> None:
        """恢复页面状态"""
        # 子类可以重写此方法来恢复特定状态
        pass

    def unload(self) -> None:
        """卸载页面"""
        if self.is_loaded:
            # 停用页面
            self.deactivate()

            # 清理资源
            self.cleanup()

            # 设置页面为未加载
            self.is_loaded = False

            self.logger.info(f"Page '{self.title}' unloaded")

    def cleanup(self) -> None:
        """清理资源"""
        # 子类可以重写此方法来清理特定资源
        pass

    def update_status(self, message: str) -> None:
        """更新状态"""
        self.status_changed.emit(message)

    def show_error(self, message: str, details: str = "") -> None:
        """显示错误"""
        self.error_occurred.emit(message, details)

    def request_action(self, action: str, data: Any = None) -> None:
        """请求执行操作"""
        self.action_requested.emit(action, data)

    def get_page_id(self) -> str:
        """获取页面ID"""
        return self.page_id

    def get_title(self) -> str:
        """获取页面标题"""
        return self.title

    def is_page_loaded(self) -> bool:
        """检查页面是否已加载"""
        return self.is_loaded

    def is_page_active(self) -> bool:
        """检查页面是否激活"""
        return self.is_active

    def get_state(self) -> Dict[str, TypingAny]:
        """获取页面状态"""
        return self.page_state.copy()

    def set_state(self, state: Dict[str, TypingAny]) -> None:
        """设置页面状态"""
        self.page_state = state.copy()

    def _on_application_state_changed(self, state) -> None:
        """应用程序状态变化处理"""
        # 子类可以重写此方法来响应应用程序状态变化
        pass

    def _on_config_changed(self, key: str, value) -> None:
        """配置变化处理"""
        # 子类可以重写此方法来响应配置变化
        pass

    def emit_event(self, event_type: str, data: TypingAny = None) -> None:
        """发送事件"""
        if self.event_bus:
            # 使用emit方法，保持API一致性
            self.event_bus.emit(event_type, data)

    def on_event(self, event_type: str, handler) -> None:
        """监听事件"""
        if self.event_bus and hasattr(self.event_bus, 'subscribe'):
            self.event_bus.subscribe(event_type, handler)

    def off_event(self, event_type: str, handler) -> None:
        """取消监听事件"""
        if self.event_bus and hasattr(self.event_bus, 'unsubscribe'):
            self.event_bus.unsubscribe(event_type, handler)

    def get_service(self, service_type: type):
        """获取服务"""
        return self.application.get_service(service_type)

    def get_config_value(self, key: str, default = None):
        """获取配置值"""
        if self.config_manager:
            return self.config_manager.get_value(key, default)
        return default

    def set_config_value(self, key: str, value: TypingAny) -> None:
        """设置配置值"""
        if self.config_manager:
            self.config_manager.set_value(key, value)

    def log_info(self, message: str) -> None:
        """记录信息日志"""
        if self.logger:
            self.logger.info(f"[{self.title}] {message}")

    def log_warning(self, message: str) -> None:
        """记录警告日志"""
        if self.logger:
            self.logger.warning(f"[{self.title}] {message}")

    def log_error(self, message: str) -> None:
        """记录错误日志"""
        if self.logger:
            self.logger.error(f"[{self.title}] {message}")

    def add_widget_to_main_layout(self, widget) -> None:
        """添加窗口部件到主布局"""
        self.main_layout.addWidget(widget)

    def add_layout_to_main_layout(self, layout) -> None:
        """添加布局到主布局"""
        self.main_layout.addLayout(layout)

    def clear_main_layout(self) -> None:
        """清空主布局"""
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def set_main_layout_margins(self, left: int, top: int, right: int, bottom: int) -> None:
        """设置主布局边距"""
        self.main_layout.setContentsMargins(left, top, right, bottom)

    def set_main_layout_spacing(self, spacing: int) -> None:
        """设置主布局间距"""
        self.main_layout.setSpacing(spacing)

    def show_loading_overlay(self, message: str = "加载中...") -> None:
        """显示加载覆盖层"""
        # 子类可以重写此方法来实现加载覆盖层
        self.update_status(message)

    def hide_loading_overlay(self) -> None:
        """隐藏加载覆盖层"""
        # 子类可以重写此方法来隐藏加载覆盖层
        self.update_status("就绪")

    def handle_error(self, error: Exception, context: str = "") -> None:
        """处理错误"""
        from ....utils.error_handler import ErrorInfo as UIErrorInfo
        error_message = f"Error in {self.title}"
        if context:
            error_message += f" ({context})"

        error_info = UIErrorInfo(
            error_type="ui",
            severity="medium",
            message=f"{error_message}: {str(error)}",
            exception=error
        )
        self.error_handler.handle_error(error_info)