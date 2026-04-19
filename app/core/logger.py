#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Voxplore 日志记录器模块
提供日志记录和管理功能
"""

import logging
import sys
from enum import Enum


class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


class LogFormat(Enum):
    """日志格式枚举"""
    SIMPLE = "simple"
    DETAILED = "detailed"
    STRUCTURED = "structured"


class Logger:
    """简化日志记录器（支持懒加载和结构化日志）"""

    def __init__(self, name: str, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self._name = name

        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    @classmethod
    def get_logger(cls, name: str) -> 'Logger':
        """获取日志记录器实例"""
        return cls(name)

    def _log(self, level: int, message: str, *args, **kwargs) -> None:
        """内部日志方法，支持懒加载格式化"""
        if self.logger.isEnabledFor(level):
            # 如果消息是 callable（延迟计算），执行它获取实际消息
            if callable(message):
                message = message()
            self.logger.log(level, message, *args, **kwargs)

    def debug(self, message: str) -> None:
        """调试日志"""
        self._log(logging.DEBUG, message)

    def info(self, message: str) -> None:
        """信息日志"""
        self._log(logging.INFO, message)

    def warning(self, message: str) -> None:
        """警告日志"""
        self._log(logging.WARNING, message)

    def error(self, message: str) -> None:
        """错误日志"""
        self._log(logging.ERROR, message)

    def critical(self, message: str) -> None:
        """严重错误日志"""
        self._log(logging.CRITICAL, message)

    def log_lazy(self, level: int, message_fn: callable) -> None:
        """懒加载日志：仅在对应日志级别启用时才计算消息内容
        
        Args:
            level: 日志级别
            message_fn: 返回消息字符串的函数（callable）
        
        Usage:
            logger.log_lazy(logging.INFO, lambda: f"Expensive calculation: {compute()}")
        """
        self._log(level, message_fn)

    @property
    def name(self) -> str:
        """获取日志记录器名称"""
        return self._name


def setup_logging(
    level: LogLevel = LogLevel.INFO,
    format_type: LogFormat = LogFormat.DETAILED,
    enable_console: bool = True,
    enable_file: bool = True
) -> None:
    """设置全局日志配置"""
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(level.value)

    # 清除现有处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 创建格式化器
    if format_type == LogFormat.SIMPLE:
        formatter = logging.Formatter('%(levelname)s - %(message)s')
    elif format_type == LogFormat.DETAILED:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    else:  # STRUCTURED
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )

    # 控制台处理器
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # 文件处理器
    if enable_file:
        try:
            from pathlib import Path
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)

            file_handler = logging.FileHandler(
                log_dir / "Voxplore.log",
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            logging.getLogger(__name__).error(f"无法创建日志文件: {e}")


def get_logger(name: str) -> Logger:
    """获取日志记录器实例"""
    return Logger(name)