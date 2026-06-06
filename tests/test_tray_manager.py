#!/usr/bin/env python3
"""
托盘配置项单元测试（不需要 PySide6 环境）
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_tray_setting_default_is_false():
    """测试托盘功能默认禁用"""
    from scenefab.settings_data import get_all_settings_definitions

    defs = get_all_settings_definitions()
    assert "ui.minimize_to_tray" in defs, "ui.minimize_to_tray 配置项必须存在"

    tray_def = defs["ui.minimize_to_tray"]
    assert tray_def.default_value is False, "默认值必须是 False（点击X直接关闭）"
    assert tray_def.category == "ui"
    assert tray_def.subcategory == "behavior"
    print("✅ test_tray_setting_default_is_false")


def test_tray_setting_in_all_definitions():
    """测试配置项已注册到全局字典"""
    from scenefab.settings_data import get_all_settings_definitions

    defs = get_all_settings_definitions()
    assert "ui.minimize_to_tray" in defs
    print("✅ test_tray_setting_in_all_definitions")


def test_tray_manager_module_syntax():
    """测试 tray_manager.py 语法正确"""
    import py_compile

    py_compile.compile(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "src",
            "scenefab",
            "ui",
            "main",
            "tray_manager.py",
        ),
        doraise=True,
    )
    print("✅ test_tray_manager_module_syntax")


def test_main_window_module_syntax():
    """测试 main_window.py 语法正确"""
    import py_compile

    py_compile.compile(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "src",
            "scenefab",
            "ui",
            "main",
            "main_window.py",
        ),
        doraise=True,
    )
    print("✅ test_main_window_module_syntax")


def test_settings_page_module_syntax():
    """测试 settings_page.py 语法正确"""
    import py_compile

    py_compile.compile(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "src",
            "scenefab",
            "ui",
            "main",
            "pages",
            "settings_page.py",
        ),
        doraise=True,
    )
    print("✅ test_settings_page_module_syntax")


if __name__ == "__main__":
    test_tray_setting_default_is_false()
    test_tray_setting_in_all_definitions()
    test_tray_manager_module_syntax()
    test_main_window_module_syntax()
    test_settings_page_module_syntax()
    print()
    print("🎉 所有测试通过！")
