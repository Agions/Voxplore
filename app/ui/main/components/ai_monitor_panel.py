#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI状态监控面板 - 重新导出
已拆分为多个组件文件，请使用 monitor_panel 模块
"""

# 向后兼容导入
from .monitor_panel import AIMonitorPanel, MonitorMode, AlertData

__all__ = ["AIMonitorPanel", "MonitorMode", "AlertData"]
