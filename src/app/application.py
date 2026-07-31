import logging
from collections.abc import Callable
from enum import Enum
from typing import Any, TypeVar

from app.core.signals import QObject, Signal

try:
    from PySide6.QtCore import QSettings, QTimer
    from PySide6.QtWidgets import QApplication

    _HAS_PYSIDE6 = True
except ImportError:
    _HAS_PYSIDE6 = False

T = TypeVar("T")

logger = logging.getLogger(__name__)

__all__ = [
    "ApplicationState",
    "Application",
]


class ApplicationState(Enum):
    INITIALIZING = "initializing"
    STARTING = "starting"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    SHUTTING_DOWN = "shutting_down"
    ERROR = "error"


class Application(QObject):

    state_changed = Signal(ApplicationState)
    error_occurred = Signal(str, str)
    progress_updated = Signal(int, str)

    def __init__(self, config):
        super().__init__()

        self.config = config
        self._state = ApplicationState.INITIALIZING

        from app.core.di_container import DIContainer

        self._service_container = DIContainer(name="app")

        self._timers: dict[str, Any] = {}
        self._tasks: list[Callable] = []

        self._init_sequence = [
            ("logger", self._init_logger),
            ("config_manager", self._init_config_manager),
            ("event_bus", self._init_event_bus),
            ("error_handler", self._init_error_handler),
            ("services", self._init_services),
        ]

    def initialize(self, argv: list[str]) -> bool:
        try:
            self._set_state(ApplicationState.INITIALIZING)

            if not _HAS_PYSIDE6:
                self.error_occurred.emit("INIT_ERROR", "PySide6 not available")
                return False
            app = QApplication.instance()
            if not app:
                self.error_occurred.emit(
                    "INIT_ERROR",
                    "QApplication not created. Call QApplication.instance() first.",
                )
                return False

            for index, (name, init_func) in enumerate(self._init_sequence, start=1):
                if not init_func():
                    self.error_occurred.emit(
                        "INIT_ERROR", f"Failed to initialize {name}"
                    )
                    return False

                self.progress_updated.emit(
                    int(index / len(self._init_sequence) * 100),
                    f"Initializing {name}...",
                )

            self._load_configuration()

            self._set_state(ApplicationState.READY)
            self.progress_updated.emit(100, "Initialization complete")

            return True

        except Exception as e:
            self.error_occurred.emit("INIT_ERROR", f"Initialization failed: {str(e)}")
            self._set_state(ApplicationState.ERROR)
            return False

    def start(self) -> bool:
        try:
            self._set_state(ApplicationState.STARTING)

            for service_name in self._service_container.all_names():
                service = self._service_container.get_by_name(service_name)
                if hasattr(service, "start"):
                    assert service is not None
                    if not service.start():
                        self.error_occurred.emit(
                            "SERVICE_ERROR", f"Failed to start service: {service_name}"
                        )
                        return False

            self._start_timers()
            self._start_tasks()

            self._set_state(ApplicationState.RUNNING)
            return True

        except Exception as e:
            self.error_occurred.emit("START_ERROR", f"Start failed: {str(e)}")
            self._set_state(ApplicationState.ERROR)
            return False

    def shutdown(self) -> None:
        try:
            self._set_state(ApplicationState.SHUTTING_DOWN)

            self._stop_timers()

            services_list = self._service_container.all_names()
            for service_name in reversed(services_list):
                service = self._service_container.get_by_name(service_name)
                if hasattr(service, "stop"):
                    assert service is not None
                    try:
                        service.stop()
                    except Exception as e:
                        self.error_occurred.emit(
                            "SERVICE_ERROR",
                            f"Error stopping service {service_name}: {str(e)}",
                        )

            self._save_configuration()
            self._shutdown_event_bus()
            self._cleanup()

            self._set_state(ApplicationState.READY)

        except Exception as e:
            self.error_occurred.emit("SHUTDOWN_ERROR", f"Shutdown failed: {str(e)}")

    def _shutdown_event_bus(self) -> None:
        bus = self._service_container.get_by_name("event_bus")
        close = getattr(bus, "close", None)
        if callable(close):
            try:
                close()
            except Exception as e:
                self.error_occurred.emit(
                    "SHUTDOWN_ERROR", f"Error closing event bus: {str(e)}"
                )

    def get_service(self, service_type: type[T]) -> T | None:
        try:
            return self._service_container.get(service_type)
        except ValueError:
            return None

    def get_service_by_name(self, service_name: str) -> object | None:
        try:
            return self._service_container.get_by_name(service_name)
        except ValueError:
            return None

    def get_config(self) -> Any:
        return self.config

    def get_state(self) -> ApplicationState:
        return self._state

    def is_ready(self) -> bool:
        return self._state in [ApplicationState.READY, ApplicationState.RUNNING]

    def register_service(self, name: str, service: object) -> None:
        self._service_container.register_by_name(name, service)
        service_type = type(service)
        self._service_container.register(service_type, service)

    def unregister_service(self, name: str) -> None:
        self._service_container.remove_by_name(name)

    def has_service(self, service_type: type) -> bool:
        return self._service_container.has(service_type)

    def has_service_by_name(self, service_name: str) -> bool:
        return self._service_container.has_by_name(service_name)

    def subscribe(self, event_name: str, handler: Callable) -> None:
        event_bus: Any = self.get_service_by_name("event_bus")
        if event_bus:
            event_bus.subscribe(event_name, handler)

    def unsubscribe(self, event_name: str, handler: Callable) -> None:
        event_bus: Any = self.get_service_by_name("event_bus")
        if event_bus:
            event_bus.unsubscribe(event_name, handler)

    def publish(self, event_name: str, data: Any = None) -> None:
        event_bus: Any = self.get_service_by_name("event_bus")
        if event_bus:
            event_bus.publish(event_name, data)

    def add_timer(
        self, name: str, interval: int, callback: Callable, single_shot: bool = False
    ) -> object:
        timer = QTimer()
        timer.setInterval(interval)
        timer.setSingleShot(single_shot)
        timer.timeout.connect(callback)
        if not single_shot:
            self._timers[name] = timer
        return timer

    def remove_timer(self, name: str) -> None:
        if name in self._timers:
            self._timers[name].stop()
            del self._timers[name]

    def _set_state(self, state: ApplicationState) -> None:
        self._state = state
        self.state_changed.emit(state)

    def _init_logger(self) -> bool:
        try:
            app_logger = logging.getLogger("SceneFab")
            self.register_service("logger", app_logger)
            self.logger = app_logger
            self.logger.info("Logger initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize logger: {e}")
            return False

    def _init_config_manager(self) -> bool:
        try:
            from .config import ConfigManager

            config_manager = ConfigManager()
            self.register_service("config_manager", config_manager)

            self.logger.info("Config manager initialized")
            return True
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.error(f"Config manager init failed: {e}")
            return False

    def _init_event_bus(self) -> bool:
        try:
            from app.core.unified_event_bus import UnifiedEventBus

            event_bus = UnifiedEventBus.get_default()
            self.register_service("event_bus", event_bus)

            self.logger.info("Event bus initialized")
            return True
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.error(f"Event bus init failed: {e}")
            return False

    def _init_error_handler(self) -> bool:
        try:
            from .utils.error_handler import ErrorHandler

            error_handler = ErrorHandler(self.logger)
            self.register_service("error_handler", error_handler)

            self.logger.info("Error handler initialized")
            return True
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.error(f"Error handler init failed: {e}")
            return False

    def _init_services(self) -> bool:
        try:
            from .config import ConfigManager, ProjectSettingsManager
            from .project import ProjectManager
            from .project import TemplateManager as ProjectTemplateManager

            config_manager: Any = self.get_service_by_name("config_manager")
            if not config_manager:
                config_manager = ConfigManager()
                self.register_service("config_manager", config_manager)

            project_manager = ProjectManager(config_manager)
            self.register_service("project_manager", project_manager)

            template_manager = ProjectTemplateManager(config_manager)
            self.register_service("template_manager", template_manager)

            settings_manager = ProjectSettingsManager(config_manager)
            self.register_service("settings_manager", settings_manager)

            from app.services.video.monologue_maker import MonologueMaker
            self.register_service("monologue_maker", MonologueMaker())

            self.logger.info("Services initialized")
            return True
        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.error(f"Service init failed: {e}")
            return False

    def _load_configuration(self) -> None:
        try:
            settings = QSettings("SceneFab", "Application")
            self.logger.info(f"Config loaded: {len(settings.allKeys())} keys")
        except Exception as e:
            self.logger.error(f"Config load failed: {e}")

    def _save_configuration(self) -> None:
        try:
            settings_mgr = self.get_service_by_name("settings_manager")
            if settings_mgr and hasattr(settings_mgr, "save"):
                settings_mgr.save()
            if _HAS_PYSIDE6:
                settings = QSettings("SceneFab", "Application")
                settings.sync()
            self.logger.info("Config saved")
        except Exception as e:
            self.logger.error(f"Config save failed: {e}")

    def _start_timers(self) -> None:
        for timer in self._timers.values():
            if not timer.isSingleShot():
                timer.start()

    def _stop_timers(self) -> None:
        for timer in self._timers.values():
            timer.stop()

    def _start_tasks(self) -> None:
        for task in self._tasks:
            try:
                task()
            except Exception as e:
                self.logger.error(f"Task failed: {e}")

    def _cleanup(self) -> None:
        self._service_container.clear()
        self._timers.clear()
        self._tasks.clear()
        self.logger.info("Cleanup complete")
