#!/usr/bin/env python3

"""
设置类型定义

包含设置管理器的类型定义（枚举和 dataclass）。
这些类型被多个模块使用，单独提取以便共享。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Union


class SettingType(Enum):
    """设置类型枚举"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    COLOR = "color"
    PATH = "path"
    RESOLUTION = "resolution"


@dataclass
class SettingDefinition:
    """设置定义"""
    key: str
    name: str
    description: str
    setting_type: SettingType
    default_value: Any
    min_value: int | float | None = None
    max_value: int | float | None = None
    options: list[str] | None = None
    category: str = "general"
    subcategory: str = ""
    advanced: bool = False
    restart_required: bool = False
    validator: str | None = None  # 验证函数名


@dataclass
class ProjectSettingsProfile:
    """项目设置配置文件"""
    name: str
    description: str
    settings: dict[str, Any]
    created_at: str
    modified_at: str
    tags: list[str] = field(default_factory=list)
    is_builtin: bool = False


__all__ = [
    "SettingType",
    "SettingDefinition",
    "ProjectSettingsProfile",
]
