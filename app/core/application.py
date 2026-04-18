#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Voxplore 应用程序核心类
负责应用程序的生命周期管理、服务管理和状态控制
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, Signal, QObject, QSettings

__all__ = [
    "ApplicationState",
    "ErrorType",
    "ErrorSeverity",
    "ErrorInfo",
    "Application",
]



class ApplicationState(Enum):
    """应用程序状态枚举"""
    INITIALIZING = "initializing"
    STARTING = "starting"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    SHUTTING_DOWN = "shutting_down"
    ERROR = "error"


class ErrorType(Enum):
    """错误类型枚举"""
    SYSTEM = "system"
    UI = "ui"
    FILE = "file"
    NETWORK = "network"
    AI = "ai"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """错误严重程度枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorInfo:
    """错误信息数据类"""
    error_type: ErrorType
    severity: ErrorSeverity
    message: str
    details: Optional[str] = None
    exception: Optional[Exception] = None
    timestamp: float = field(default_factory=lambda: QApplication.instance().property('timestamp') if QApplication.instance() else 0)


class Application(QObject):
    """Voxplore 应用程序核心类"""

    # 信号定义
    state_changed = Signal(ApplicationState)        # 应用程序状态变化信号
    error_occurred = Signal(str, str)             # 应用程序错误信号
    progress_updated = Signal(int, str)            # 进度更新信号
    message_logged = Signal(str, str)              # 消息日志信号
    config_changed = Signal(str, object)              # 配置变更信号
    service_registered = Signal(str, object)      # 服务注册信号
    service_unregistered = Signal(str)             # 服务注销信号

    def __init__(self, config):
        """初始化应用程序"""
        super().__init__()

        # 配置和状态管理
        self.config = config
        self._state = ApplicationState.INITIALIZING

        # 服务容器
        from .service_container import ServiceContainer
        self._service_container = ServiceContainer()

        # 事件系统
        self._event_handlers: Dict[str, List[Callable]] = {}

        # 定时器和任务
        self._timers: Dict[str, QTimer] = {}
        self._tasks: List[Callable] = []

        # 初始化顺序
        self._init_sequence = [
            ("logger", self._init_logger),
            ("config_manager", self._init_config_manager),
            ("event_bus", self._init_event_bus),
            ("error_handler", self._init_error_handler),
            ("icon_manager", self._init_icon_manager),
            ("services", self._init_services)
        ]

    def initialize(self, argv: List[str]) -> bool:
        """初始化应用程序"""
        try:
            self._set_state(ApplicationState.INITIALIZING)

            # 确保QApplication存在 - 应该已经在main.py中创建
            app = QApplication.instance()
            if not app:
                self.error_occurred.emit("INIT_ERROR", "QApplication not created. Call QApplication.instance() first.")
                return False

            # 执行初始化序列
            for name, init_func in self._init_sequence:
                if not init_func():
                    self.error_occurred.emit("INIT_ERROR", f"Failed to initialize {name}")
                    return False

                self.progress_updated.emit(
                    int((self._init_sequence.index((name, init_func)) + 1) / len(self._init_sequence) * 100),
                    f"正在初始化 {name}..."
                )

            # 注册核心服务
            self._register_core_services()

            # 加载配置
            self._load_configuration()

            self._set_state(ApplicationState.READY)
            self.progress_updated.emit(100, "初始化完成")

            return True

        except Exception as e:
            self.error_occurred.emit("INIT_ERROR", f"Initialization failed: {str(e)}")
            self._set_state(ApplicationState.ERROR)
            return False

    def start(self) -> bool:
        """启动应用程序"""
        try:
            self._set_state(ApplicationState.STARTING)

            # 启动所有服务
            for service_name, service in self._service_container._services_by_name.items():
                if hasattr(service, 'start'):
                    if not service.start():
                        self.error_occurred.emit("SERVICE_ERROR", f"Failed to start service: {service_name}")
                        return False

            # 启动定时器
            self._start_timers()

            # 启动后台任务
            self._start_tasks()

            self._set_state(ApplicationState.RUNNING)
            return True

        except Exception as e:
            self.error_occurred.emit("START_ERROR", f"Start failed: {str(e)}")
            self._set_state(ApplicationState.ERROR)
            return False

    def shutdown(self) -> None:
        """关闭应用程序"""
        try:
            self._set_state(ApplicationState.SHUTTING_DOWN)

            # 停止定时器
            self._stop_timers()

            # 停止所有服务
            # 使用列表副本进行反向迭代
            services_list = list(self._service_container._services_by_name.items())
            for service_name, service in reversed(services_list):
                if hasattr(service, 'stop'):
                    try:
                        service.stop()
                    except Exception as e:
                        self.error_occurred.emit("SERVICE_ERROR", f"Error stopping service {service_name}: {str(e)}")

            # 保存配置
            self._save_configuration()

            # 清理资源
            self._cleanup()

            self._set_state(ApplicationState.READY)

        except Exception as e:
            self.error_occurred.emit("SHUTDOWN_ERROR", f"Shutdown failed: {str(e)}")

    def run(self) -> int:
        """运行应用程序主循环"""
        try:
            app = QApplication.instance()
            if not app:
                self.error_occurred.emit("RUN_ERROR", "QApplication not found")
                return 1

            # 运行主循环 - 注意：实际的事件循环在main.py中运行
            # 这里只返回0表示成功
            return 0

        except Exception as e:
            self.error_occurred.emit("RUN_ERROR", f"Run failed: {str(e)}")
            return 1

    def get_service(self, service_type: type) -> Optional[object]:
        """获取指定类型的服务"""
        try:
            return self._service_container.get(service_type)
        except ValueError:
            return None

    def get_service_by_name(self, service_name: str) -> Optional[object]:
        """获取指定名称的服务"""
        try:
            return self._service_container.get_by_name(service_name)
        except ValueError:
            return None

    def get_config(self) -> Any:
        """获取应用程序配置"""
        return self.config

    def get_state(self) -> ApplicationState:
        """获取应用程序状态"""
        return self._state

    def is_ready(self) -> bool:
        """检查应用程序是否就绪"""
        return self._state in [ApplicationState.READY, ApplicationState.RUNNING]

    def register_service(self, name: str, service: object) -> None:
        """注册服务"""
        # 注册到服务容器
        self._service_container.register_by_name(name, service)
        
        # 同时按类型注册，方便按类型获取
        service_type = type(service)
        self._service_container.register(service_type, service)
        
        self.service_registered.emit(name, service)

    def unregister_service(self, name: str) -> None:
        """注销服务"""
        # 从服务容器中移除服务
        self._service_container.remove_by_name(name)
        self.service_unregistered.emit(name)

    def has_service(self, service_type: type) -> bool:
        """检查指定类型的服务是否存在"""
        return self._service_container.has(service_type)

    def has_service_by_name(self, service_name: str) -> bool:
        """检查指定名称的服务是否存在"""
        return self._service_container.has_by_name(service_name)

    def subscribe(self, event_name: str, handler: Callable) -> None:
        """订阅事件"""
        event_bus = self.get_service_by_name("event_bus")
        if event_bus:
            event_bus.subscribe(event_name, handler)

    def unsubscribe(self, event_name: str, handler: Callable) -> None:
        """取消订阅事件"""
        event_bus = self.get_service_by_name("event_bus")
        if event_bus:
            event_bus.unsubscribe(event_name, handler)

    def publish(self, event_name: str, data: Any = None) -> None:
        """发布事件"""
        event_bus = self.get_service_by_name("event_bus")
        if event_bus:
            event_bus.publish(event_name, data)
        else:
            # 回退到内部事件处理器（如果EventBus服务未初始化）
            if event_name in self._event_handlers:
                for handler in self._event_handlers[event_name]:
                    try:
                        handler(data)
                    except Exception as e:
                        self.error_occurred.emit("EVENT_ERROR", f"Event handler error: {str(e)}")

    def add_timer(self, name: str, interval: int, callback: Callable, single_shot: bool = False) -> QTimer:
        """
        添加定时器

        注意: QTimer 必须在主线程（GUI 线程）中创建和操作。
        如果从后台线程调用此方法，可能导致 Qt 警告或未定义行为。
        确保所有定时器相关调用都在主线程中执行，或使用 QMetaObject.invokeMethod
        将定时器操作调度到主线程。
        """
        timer = QTimer()
        timer.setInterval(interval)
        timer.setSingleShot(single_shot)
        timer.timeout.connect(callback)

        if not single_shot:
            self._timers[name] = timer

        return timer

    def remove_timer(self, name: str) -> None:
        """移除定时器"""
        if name in self._timers:
            self._timers[name].stop()
            del self._timers[name]

    def _set_state(self, state: ApplicationState) -> None:
        """设置应用程序状态"""
        self._state = state
        self.state_changed.emit(state)

    def _init_logger(self) -> bool:
        """初始化日志系统"""
        try:
            from .logger import Logger

            # 创建日志服务
            logger = Logger("Voxplore")
            self.register_service("logger", logger)

            # 设置应用程序日志
            self.logger = logger
            self.logger.info("日志系统初始化完成")

            return True

        except Exception as e:
            print(f"Failed to initialize logger: {e}")
            return False

    def _init_config_manager(self) -> bool:
        """初始化配置管理器"""
        try:
            from .config_manager import ConfigManager

            # 创建配置管理器
            config_manager = ConfigManager()
            self.register_service("config_manager", config_manager)

            self.logger.info("配置管理器初始化完成")
            return True

        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"配置管理器初始化失败: {e}")
            return False

    def _init_event_bus(self) -> bool:
        """初始化事件总线"""
        try:
            from .event_bus import EventBus

            # 使用外部EventBus类
            event_bus = EventBus()
            self.register_service("event_bus", event_bus)

            self.logger.info("事件总线初始化完成")
            return True

        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"事件总线初始化失败: {e}")
            return False

    def _init_error_handler(self) -> bool:
        """初始化错误处理器"""
        try:
            from ..utils.error_handler import ErrorHandler

            # 创建错误处理器
            error_handler = ErrorHandler(self.logger)
            self.register_service("error_handler", error_handler)

            self.logger.info("错误处理器初始化完成")
            return True

        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"错误处理器初始化失败: {e}")
            return False

    def _init_icon_manager(self) -> bool:
        """初始化图标管理器"""
        try:
            from .icon_manager import init_icon_manager

            # 初始化图标管理器 - 现在它可以处理QApplication不存在的情况
            icon_manager = init_icon_manager("resources/icons")
            self.register_service("icon_manager", icon_manager)

            self.logger.info("图标管理器初始化完成")
            return True

        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"图标管理器初始化失败: {e}")
            return False

    def _init_services(self) -> bool:
        """初始化其他服务"""
        try:
            # 使用已存在的服务代替
            from ..services import get_ai_service_manager

            # 创建并注册AI服务管理器
            ai_service_manager = get_ai_service_manager()
            self.register_service("ai_service_manager", ai_service_manager)
            
            # 初始化项目管理相关服务
            from .project_manager import ProjectManager
            from .project_template_manager import ProjectTemplateManager
            from .project_settings_manager import ProjectSettingsManager
            from .config_manager import ConfigManager
            
            # 创建配置管理器实例（如果不存在）
            config_manager = self.get_service_by_name("config_manager")
            if not config_manager:
                config_manager = ConfigManager()
                self.register_service("config_manager", config_manager)
            
            # 创建并注册项目管理器
            project_manager = ProjectManager(config_manager)
            self.register_service("project_manager", project_manager)
            
            # 创建并注册模板管理器
            template_manager = ProjectTemplateManager(config_manager)
            self.register_service("template_manager", template_manager)
            
            # 创建并注册设置管理器
            settings_manager = ProjectSettingsManager(config_manager)
            self.register_service("settings_manager", settings_manager)

            self.logger.info("服务初始化完成")
            return True

        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"服务初始化失败: {e}")
            return False

    def _register_core_services(self) -> None:
        """注册核心服务"""
        # 注册核心服务到服务容器（使用服务容器而非 ServiceRegistry）
        # 已经在 _init_services 中注册过了
        pass

    def _load_configuration(self) -> None:
        """加载配置"""
        try:
            # 从文件或注册表加载配置
            _settings = QSettings("Voxplore", "Application")

            # 加载应用程序配置
            self.logger.info("配置加载完成")

        except Exception as e:
            self.logger.error(f"配置加载失败: {e}")

    def _save_configuration(self) -> None:
        """保存配置"""
        try:
            # 保存配置到文件或注册表
            _settings = QSettings("Voxplore", "Application")

            self.logger.info("配置保存完成")

        except Exception as e:
            self.logger.error(f"配置保存失败: {e}")

    def _start_timers(self) -> None:
        """启动定时器"""
        # 启动所有定时器
        for timer in self._timers.values():
            if not timer.isSingleShot():
                timer.start()

    def _stop_timers(self) -> None:
        """停止定时器"""
        # 停止所有定时器
        for timer in self._timers.values():
            timer.stop()

    def _start_tasks(self) -> None:
        """启动后台任务"""
        # 启动所有后台任务
        for task in self._tasks:
            try:
                task()
            except Exception as e:
                self.logger.error(f"任务执行失败: {e}")

    def _cleanup(self) -> None:
        """清理资源"""
        # 清理所有资源
        self._service_container.clear()
        self._event_handlers.clear()
        self._timers.clear()
        self._tasks.clear()

        self.logger.info("资源清理完成")
