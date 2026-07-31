import logging
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

try:
    from PySide6.QtWidgets import QMessageBox, QWidget
    _HAS_QT = True
except ImportError:
    QMessageBox = None
    QWidget = None
    _HAS_QT = False

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    NETWORK = "network"
    API = "api"
    FILE = "file"
    VALIDATION = "validation"
    PERMISSION = "permission"
    UNKNOWN = "unknown"


@dataclass
class ErrorInfo:
    error_type: str
    severity: str
    message: str
    category: str = "unknown"
    exception: Exception | None = None
    details: str = ""
    retry_count: int = 0
    context: dict[str, Any] = field(default_factory=dict)


class ErrorHandler:
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger
        self._error_history: list = []
        self._max_history = 100

    def handle_error(self, error_info: ErrorInfo):
        self._error_history.append(error_info)
        if len(self._error_history) > self._max_history:
            self._error_history.pop(0)

        error_message = f"[{error_info.category.upper()}] {error_info.error_type}: {error_info.message}"
        if error_info.details:
            error_message += f"\nDetails: {error_info.details}"

        if self.logger:
            log_method = getattr(self.logger, error_info.severity, self.logger.error)
            log_method(error_message, exc_info=error_info.exception)
        else:
            logging.getLogger("error_handler").error(error_message)
            if error_info.exception:
                traceback.print_exception(
                    type(error_info.exception),
                    error_info.exception,
                    error_info.exception.__traceback__,
                )

    def show_error_dialog(
        self,
        parent: Any = None,
        title: str = "",
        message: str = "",
        details: str = "",
        category: str = "unknown",
    ) -> None:
        if not _HAS_QT:
            logger.error(f"[{category.upper()}] {title}: {message}")
            return
        icon_map = {
            "critical": QMessageBox.Icon.Critical,
            "error": QMessageBox.Icon.Critical,
            "warning": QMessageBox.Icon.Warning,
            "info": QMessageBox.Icon.Information,
            "network": QMessageBox.Icon.Warning,
            "api": QMessageBox.Icon.Warning,
            "file": QMessageBox.Icon.Warning,
            "validation": QMessageBox.Icon.Information,
            "permission": QMessageBox.Icon.Critical,
        }
        icon = icon_map.get(category, QMessageBox.Icon.Critical)

        if parent:
            msg_box = QMessageBox(parent)
            msg_box.setIcon(icon)
            msg_box.setWindowTitle(title)
            msg_box.setText(message)
            if details:
                msg_box.setDetailedText(details)
            msg_box.exec()
        else:
            QMessageBox.critical(None, title, message)

    def get_error_summary(self) -> dict[str, int]:
        summary: dict[str, int] = {}
        for error in self._error_history:
            summary[error.category] = summary.get(error.category, 0) + 1
        return summary

    def get_recent_errors(self, limit: int = 10) -> list:
        return self._error_history[-limit:]
