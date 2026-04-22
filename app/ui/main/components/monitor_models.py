#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI监控面板 - 数据模型

定义监控面板使用的数据模型。
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional


class MonitorMode:
    """监控模式"""
    OVERVIEW = "overview"
    SERVICES = "services"
    PERFORMANCE = "performance"
    USAGE = "usage"
    ALERTS = "alerts"


@dataclass
class AlertData:
    """告警数据"""
    id: str
    service_name: str
    level: str  # info, warning, error, critical
    message: str
    timestamp: float
    resolved: bool = False
    details: Optional[Dict[str, Any]] = None


__all__ = [
    "MonitorMode",
    "AlertData",
]
