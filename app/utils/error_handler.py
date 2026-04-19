#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Voxplore 错误处理模块 ✅ 优化版本
提供全局异常处理和错误对话框功能
支持异步操作和错误恢复
"""

import sys
import traceback
import asyncio
import logging
from typing import Optional, Callable, Any, Dict
from dataclasses import dataclass, field
from enum import Enum
from PySide6.QtWidgets import QMessageBox, QWidget
from functools import wraps

logger = logging.getLogger(__name__)


# ============ 枚举定义 ============

class ErrorSeverity(Enum):
    """错误严重程度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """错误类别"""
    NETWORK = "network"          # 网络错误
    API = "api"                  # API 调用错误
    FILE = "file"                # 文件操作错误
    VALIDATION = "validation"    # 验证错误
    PERMISSION = "permission"     # 权限错误
    UNKNOWN = "unknown"           # 未知错误


# ============ 数据类 ============

@dataclass
class ErrorInfo:
    """错误信息数据类"""
    error_type: str
    severity: str
    message: str
    category: str = "unknown"     # ✅ 新增：错误类别
    exception: Optional[Exception] = None
    details: str = ""
    retry_count: int = 0         # ✅ 新增：重试次数
    context: Dict[str, Any] = field(default_factory=dict)  # ✅ 新增：上下文


# ============ 错误恢复策略 ============

class RetryStrategy:
    """
    重试策略 ✅ 新增
    支持指数退避和条件重试
    """
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        retryable_categories: tuple = (ErrorCategory.NETWORK, ErrorCategory.API)
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retryable_categories = retryable_categories
    
    def can_retry(self, error_info: ErrorInfo) -> bool:
        """判断是否可以重试"""
        if error_info.retry_count >= self.max_attempts:
            return False
        
        try:
            category = ErrorCategory(error_info.category)
            return category in self.retryable_categories
        except ValueError:
            return False
    
    def get_delay(self, attempt: int) -> float:
        """计算延迟时间"""
        import random
        delay = min(self.base_delay * (self.exponential_base ** attempt), self.max_delay)
        # 添加 jitter
        return delay * (0.5 + random.random() * 0.5)


# ============ 异步错误处理 ============

class AsyncErrorHandler:
    """
    异步错误处理器 ✅ 新增
    支持异步操作的安全执行和自动重试
    """
    
    def __init__(self, retry_strategy: RetryStrategy = None):
        self.retry_strategy = retry_strategy or RetryStrategy()
        self._error_history: list = []
        self._max_history = 100
    
    def _record_error(self, error_info: ErrorInfo):
        """记录错误历史"""
        self._error_history.append(error_info)
        if len(self._error_history) > self._max_history:
            self._error_history.pop(0)
    
    async def safe_execute_async(
        self,
        func: Callable,
        *args,
        error_message: str = "异步操作失败",
        on_retry: Callable[[ErrorInfo], None] = None,
        **kwargs
    ) -> Optional[Any]:
        """
        安全执行异步函数
        
        Args:
            func: 异步函数
            *args: 位置参数
            error_message: 错误消息
            on_retry: 重试时的回调函数
            **kwargs: 关键字参数
            
        Returns:
            函数返回值，失败时返回 None
        """
        _last_error = None
        
        for attempt in range(self.retry_strategy.max_attempts):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            
            except Exception as e:
                _last_error = e
                error_info = ErrorInfo(
                    error_type=type(e).__name__,
                    severity="error",
                    message=error_message,
                    exception=e,
                    details=str(e),
                    retry_count=attempt,
                    context={"args": str(args)[:100], "kwargs": str(kwargs)[:100]}
                )
                
                self._record_error(error_info)
                
                if self.retry_strategy.can_retry(error_info):
                    delay = self.retry_strategy.get_delay(attempt)
                    logger.warning(
                        f"异步操作失败 (尝试 {attempt + 1}/{self.retry_strategy.max_attempts}): {e}. "
                        f"{delay:.1f}秒后重试..."
                    )
                    
                    if on_retry:
                        on_retry(error_info)
                    
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"异步操作最终失败: {e}")
                    break
        
        return None
    
    def get_recent_errors(self, limit: int = 10) -> list:
        """获取最近的错误"""
        return self._error_history[-limit:]


# ============ 错误处理器 ============

class ErrorHandler:
    """错误处理器"""

    def __init__(self, logger: logging.Logger = None):
        """初始化错误处理器"""
        self.logger = logger
        # ✅ 新增：错误历史
        self._error_history: list = []
        self._max_history = 100
    
    def handle_error(self, error_info: ErrorInfo):
        """处理错误
        
        Args:
            error_info: 错误信息对象
        """
        # 记录历史
        self._error_history.append(error_info)
        if len(self._error_history) > self._max_history:
            self._error_history.pop(0)
        
        error_message = f"[{error_info.category.upper()}] {error_info.error_type}: {error_info.message}"
        if error_info.details:
            error_message += f"\n详情: {error_info.details}"
        
        if self.logger:
            log_method = getattr(self.logger, error_info.severity, self.logger.error)
            log_method(error_message, exc_info=error_info.exception)
        else:
            logging.getLogger("error_handler").error(error_message)
            if error_info.exception:
                traceback.print_exception(
                    type(error_info.exception), 
                    error_info.exception, 
                    error_info.exception.__tracetrace__
                )
    
    def show_error_dialog(
        self, 
        parent: Optional[QWidget], 
        title: str, 
        message: str, 
        details: str = "",
        category: str = "unknown"
    ) -> None:
        """显示错误对话框
        
        Args:
            parent: 父窗口
            title: 对话框标题
            message: 错误消息
            details: 详细错误信息
            category: 错误类别
        """
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

    def log_and_show_error(
        self, 
        parent: Optional[QWidget], 
        error_info: ErrorInfo,
        show_dialog: bool = True
    ) -> None:
        """记录错误并可选显示错误对话框
        
        Args:
            parent: 父窗口
            error_info: 错误信息对象
            show_dialog: 是否显示对话框
        """
        self.handle_error(error_info)
        
        if show_dialog:
            self.show_error_dialog(
                parent, 
                "错误", 
                error_info.message, 
                error_info.details,
                error_info.category
            )
    
    def get_error_summary(self) -> Dict[str, int]:
        """获取错误统计摘要"""
        summary = {}
        for error in self._error_history:
            summary[error.category] = summary.get(error.category, 0) + 1
        return summary
    
    def get_recent_errors(self, limit: int = 10) -> list:
        """获取最近的错误"""
        return self._error_history[-limit:]


# ============ 装饰器 ============

def async_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    retryable_exceptions: tuple = (Exception,)
):
    """
    异步重试装饰器 ✅ 新增
    
    Args:
        max_attempts: 最大重试次数
        base_delay: 基础延迟（秒）
        retryable_exceptions: 可重试的异常类型元组
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            import random
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    if attempt < max_attempts - 1:
                        delay = base_delay * (2 ** attempt) * (0.5 + random.random() * 0.5)
                        logger.warning(
                            f"{func.__name__} 失败 (尝试 {attempt + 1}/{max_attempts}): {e}. "
                            f"{delay:.1f}秒后重试..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"{func.__name__} 最终失败: {e}")
                        raise
            return None
        
        return wrapper
    return decorator


def sync_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    retryable_exceptions: tuple = (Exception,)
):
    """
    同步重试装饰器 ✅ 新增
    
    Args:
        max_attempts: 最大重试次数
        base_delay: 基础延迟（秒）
        retryable_exceptions: 可重试的异常类型元组
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time
            import random
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    if attempt < max_attempts - 1:
                        delay = base_delay * (2 ** attempt) * (0.5 + random.random() * 0.5)
                        logger.warning(
                            f"{func.__name__} 失败 (尝试 {attempt + 1}/{max_attempts}): {e}. "
                            f"{delay:.1f}秒后重试..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(f"{func.__name__} 最终失败: {e}")
                        raise
            return None
        
        return wrapper
    return decorator


# ============ 全局异常处理 ============

def handle_exception(exc_type, exc_value, exc_traceback):
    """处理未捕获的异常"""
    logging.getLogger("error_handler").critical(f"未捕获的异常: {exc_value}")
    traceback.print_exception(exc_type, exc_value, exc_traceback)


def show_error_dialog(
    parent: Optional[QWidget], 
    title: str, 
    message: str, 
    details: str = "",
    category: str = "unknown"
) -> None:
    """显示错误对话框
    
    Args:
        parent: 父窗口
        title: 对话框标题
        message: 错误消息
        details: 详细错误信息
        category: 错误类别
    """
    if parent:
        msg_box = QMessageBox(parent)
        icon_map = {
            "critical": QMessageBox.Icon.Critical,
            "error": QMessageBox.Icon.Critical,
            "warning": QMessageBox.Icon.Warning,
            "info": QMessageBox.Icon.Information,
        }
        msg_box.setIcon(icon_map.get(category, QMessageBox.Icon.Critical))
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        if details:
            msg_box.setDetailedText(details)
        msg_box.exec()
    else:
        QMessageBox.critical(None, title, message)


def setup_global_exception_handler(log: logging.Logger = None) -> ErrorHandler:
    """设置全局异常处理器
    
    Args:
        logger: 日志记录器
        
    Returns:
        ErrorHandler: 错误处理器实例
    """
    def exception_handler(exc_type, exc_value, exc_traceback):
        error_info = ErrorInfo(
            error_type="UnhandledException",
            severity="critical",
            message=f"未捕获的异常: {exc_value}",
            exception=exc_value,
            details=str(exc_value)
        )
        
        if log:
            log.critical(error_info.message, exc_info=(exc_type, exc_value, exc_traceback))
        else:
            logging.getLogger("error_handler").critical(f"{error_info.error_type}: {error_info.message}")
            traceback.print_exception(exc_type, exc_value, exc_traceback)

    sys.excepthook = exception_handler
    return ErrorHandler(log)


def safe_execute(
    func: Callable,
    parent: Optional[QWidget] = None,
    error_message: str = "操作失败",
    logger = None,
    category: str = "unknown",
    *args,
    **kwargs
) -> Optional[Any]:
    """安全执行函数
    
    Args:
        func: 要执行的函数
        parent: 父窗口，用于显示错误对话框
        error_message: 错误消息
        logger: 日志记录器
        category: 错误类别
        *args: 函数参数
        **kwargs: 函数关键字参数
        
    Returns:
        Any: 函数返回值，如果执行失败则返回None
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        error_info = ErrorInfo(
            error_type="ExecutionError",
            severity="error",
            message=error_message,
            exception=e,
            details=str(e),
            category=category
        )
        
        # 记录错误
        if logger:
            logger.error(error_info.message, exc_info=e)
        else:
            logging.getLogger("error_handler").error(f"{error_info.error_type}: {error_info.message}")
            traceback.print_exception(type(e), e, e.__traceback__)
        
        # 显示错误对话框
        if parent:
            show_error_dialog(parent, "错误", error_info.message, error_info.details, category)
        
        return None


# ============ 全局实例 ============

_async_error_handler: Optional[AsyncErrorHandler] = None


def get_async_error_handler() -> AsyncErrorHandler:
    """获取全局异步错误处理器"""
    global _async_error_handler
    if _async_error_handler is None:
        _async_error_handler = AsyncErrorHandler()
    return _async_error_handler
