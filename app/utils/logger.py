#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
全局日志配置
统一日志格式和输出
"""

import logging
import sys
from pathlib import Path
from typing import Optional


class LogFormatter(logging.Formatter):
    """自定义日志格式"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # 青色
        'INFO': '\033[32m',     # 绿色
        'WARNING': '\033[33m',  # 黄色
        'ERROR': '\033[31m',    # 红色
        'CRITICAL': '\033[35m', # 紫色
        'RESET': '\033[0m',
    }
    
    def format(self, record):
        # 添加颜色
        if hasattr(sys.stderr, 'isatty') and sys.stderr.isatty():
            levelname = record.levelname
            if levelname in self.COLORS:
                record.levelname = (
                    f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
                )
        
        return super().format(record)


def setup_logger(
    name: str = "narrafiilm",
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    format_string: Optional[str] = None,
) -> logging.Logger:
    """
    设置日志器
    
    Args:
        name: 日志器名称
        level: 日志级别
        log_file: 日志文件路径 (可选)
        format_string: 格式字符串 (可选)
        
    Returns:
        Logger 实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers.clear()
    
    # 默认格式
    if format_string is None:
        format_string = (
            "%(asctime)s | %(levelname)-8s | "
            "%(name)s:%(lineno)d | %(message)s"
        )
    
    formatter = LogFormatter(format_string, datefmt="%H:%M:%S")
    
    # 控制台处理器
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    logger.addHandler(console)
    
    # 文件处理器
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """获取日志器"""
    return logging.getLogger(f"narrafiilm.{name}")


# 默认日志器
default_logger = setup_logger()


# 便捷函数
def debug(msg: str, *args, **kwargs):
    """已禁用 DEBUG 日志"""
    pass


def info(msg: str, *args, **kwargs):
    default_logger.info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs):
    default_logger.warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs):
    default_logger.error(msg, *args, **kwargs)


def critical(msg: str, *args, **kwargs):
    default_logger.critical(msg, *args, **kwargs)
