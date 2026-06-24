#!/usr/bin/env python3
"""测试日志模块"""

import logging
from io import StringIO

from scenefab.logger import Logger


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

    def test_log_lazy(self):
        """测试懒加载日志"""
        logger = Logger("test_lazy", level=logging.INFO)
        called = []
        logger.log_lazy(logging.INFO, lambda: called.append(1) or "lazy message")
        assert len(called) == 1


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
