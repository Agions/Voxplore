#!/usr/bin/env python3
"""
托盘配置项单元测试（不需要 PySide6 环境）
"""

import py_compile
from pathlib import Path

from scenefab.settings.definitions import get_all_settings_definitions

_SRC = Path(__file__).resolve().parent.parent.parent / "src" / "scenefab"


def test_tray_setting_default_is_false():
    """测试托盘功能默认禁用"""

    defs = get_all_settings_definitions()
    assert "ui.minimize_to_tray" in defs, "ui.minimize_to_tray 配置项必须存在"

    tray_def = defs["ui.minimize_to_tray"]
    assert tray_def.default_value is False, "默认值必须是 False（点击X直接关闭）"
    assert tray_def.category == "ui"
    assert tray_def.subcategory == "behavior"


def test_tray_setting_in_all_definitions():
    """测试配置项已注册到全局字典"""

    defs = get_all_settings_definitions()
    assert "ui.minimize_to_tray" in defs


def test_tray_manager_module_syntax():
    """测试 tray_manager.py 语法正确"""
    py_compile.compile(str(_SRC / "ui" / "main" / "tray_manager.py"), doraise=True)


def test_main_window_module_syntax():
    """测试 main_window 包语法正确"""
    py_compile.compile(
        str(_SRC / "ui" / "main" / "main_window" / "__init__.py"), doraise=True
    )


def test_settings_page_module_syntax():
    """测试 settings_page.py 语法正确"""
    py_compile.compile(
        str(_SRC / "ui" / "main" / "pages" / "settings_page.py"), doraise=True
    )
