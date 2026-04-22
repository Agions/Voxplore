#!/usr/bin/env python3
"""测试日志模块"""

import logging
from io import StringIO

from app.core.logger import Logger, LogLevel, LogFormat


class TestLogLevel:
    """测试日志级别枚举"""

    def test_enum_values(self):
        """测试枚举值"""
        assert LogLevel.DEBUG.value == logging.DEBUG
        assert LogLevel.INFO.value == logging.INFO
        assert LogLevel.WARNING.value == logging.WARNING
        assert LogLevel.ERROR.value == logging.ERROR
        assert LogLevel.CRITICAL.value == logging.CRITICAL


class TestLogFormat:
    """测试日志格式枚举"""

    def test_enum_values(self):
        """测试枚举值"""
        assert LogFormat.SIMPLE.value == "simple"
        assert LogFormat.DETAILED.value == "detailed"
        assert LogFormat.STRUCTURED.value == "structured"


class TestLogger:
    """测试日志记录器"""

    def test_init_default_level(self):
        """测试默认日志级别"""
        logger = Logger("test")
        assert logger.logger.level == logging.INFO

    def test_init_custom_level(self):
        """测试自定义日志级别"""
        logger = Logger("test", level=logging.DEBUG)
        assert logger.logger.level == logging.DEBUG

    def test_get_logger(self):
        """测试获取日志器"""
        logger1 = Logger.get_logger("test1")
        logger2 = Logger.get_logger("test1")
        
        # 应该是同一个实例或同名的logger
        assert logger1.logger.name == logger2.logger.name

    def test_debug_message(self):
        """测试调试消息"""
        logger = Logger("test_debug", level=logging.DEBUG)
        
        # 不应抛出异常
        logger.debug("debug message")
        logger.info("info message")
        logger.warning("warning message")
        logger.error("error message")
        logger.critical("critical message")

    def test_logger_name(self):
        """测试日志器名称"""
        logger = Logger("my_test_logger")
        assert logger.logger.name == "my_test_logger"


class TestLoggerIntegration:
    """集成测试"""

    def test_log_to_stdout(self):
        """测试输出到标准输出"""
        logger = Logger("stdout_test", level=logging.INFO)
        
        # 应该能正常输出而不崩溃
        output = StringIO()
        handler = logging.StreamHandler(output)
        handler.setLevel(logging.INFO)
        
        logger.logger.addHandler(handler)
        logger.info("test message")
        
        # 验证消息被写入
        result = output.getvalue()
        assert "test message" in result
