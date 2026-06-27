#!/usr/bin/env python3
"""
回归测试: UI 模块 import smoke + SceneFabMainWindow 结构 (Phase 3b)

不测试 GUI 行为 (headless 环境易 flaky), 只测试:
- UI 模块可正常 import (不破)
- SceneFabMainWindow 类签名稳定 (4 个 production page, title, 结构)
- UI 主题模块 (theme/ds_tokens) 正常

诚实性核心:
- 验证 import 链路 (用户在主程序启动会触发)
- 验证 main_window 结构契约 (4 个 page + PAGE_TITLES)
- 不强测 GUI 行为 (PySide6 真实环境 + offscreen 都可能因系统库缺失失败)
"""

import os

import pytest

# PySide6 可能不可用 (headless CI), 但要尝试
PySide6 = pytest.importorskip("PySide6")


@pytest.fixture(autouse=True)
def setup_qt_platform():
    """设置 Qt 平台为 offscreen (headless)"""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


# =============================================================================
# 1. SceneFabMainWindow 基础契约
# =============================================================================


def test_main_window_imports():
    """SceneFabMainWindow 可 import (主程序启动依赖)"""
    from scenefab.ui.main.main_window import SceneFabMainWindow
    assert SceneFabMainWindow is not None


def test_main_window_class_structure():
    """SceneFabMainWindow 结构契约: 4 个 production page + PAGE_TITLES"""
    from PySide6.QtWidgets import QApplication

    from scenefab.ui.main.main_window import SceneFabMainWindow

    app = QApplication.instance() or QApplication([])
    window = SceneFabMainWindow()

    try:
        # 窗口标题
        assert window.windowTitle() == "SceneFab"

        # PAGE_TITLES 必须含 4 个 production page
        assert "home" in window.PAGE_TITLES
        assert "create" in window.PAGE_TITLES
        assert "assets" in window.PAGE_TITLES
        assert "settings" in window.PAGE_TITLES

        # ContentArea 必须有 _page_map 含 4 个 page
        assert set(window.content._page_map) == {"home", "create", "assets", "settings"}

        # QStackedWidget 必须有 4 页
        assert window.content._stack.count() == 4
    finally:
        window.close()
        app.quit()


def test_main_window_submodules_importable():
    """main_window 子模块可 import (content_area, nav_components, status_bar, top_bar)"""
    from scenefab.ui.main.main_window import (
        ContentArea,
        Sidebar,
        StatusBar,
        TopBar,
    )
    assert ContentArea is not None
    assert Sidebar is not None
    assert StatusBar is not None
    assert TopBar is not None


# =============================================================================
# 2. UI theme 主题模块
# =============================================================================


def test_theme_tokens_module_importable():
    """theme/ds_tokens 设计 token 模块可 import"""
    from scenefab.ui.theme import ds_tokens
    assert ds_tokens is not None


def test_theme_typography_module_importable():
    """theme/typography 模块可 import (如果存在)"""
    try:
        from scenefab.ui.theme import typography
        assert typography is not None
    except ImportError:
        pytest.skip("typography module not found (optional)")


# =============================================================================
# 3. UI __init__.py 包导入
# =============================================================================


def test_ui_main_package_importable():
    """scenefab.ui.main 包可 import"""
    import scenefab.ui.main
    assert scenefab.ui.main is not None


def test_ui_package_importable():
    """scenefab.ui 包可 import (顶层)"""
    import scenefab.ui
    assert scenefab.ui is not None


# =============================================================================
# 4. UI 不存在 'MainWindow' 别名 (audit 发现的接口不一致)
# =============================================================================


def test_main_window_does_not_export_mainwindow_alias():
    """★ 诚实性: main_window 包不导出 MainWindow 别名 (只有 SceneFabMainWindow)

    任何用户代码尝试 `from scenefab.ui.main.main_window import MainWindow` 会失败.
    这是已知接口 (不是 bug), 但应该明确文档化以避免混淆.
    """
    from scenefab.ui.main import main_window

    assert hasattr(main_window, "SceneFabMainWindow"), "缺少 SceneFabMainWindow"
    # 故意不导出 MainWindow 别名 — 防止命名混淆
    assert not hasattr(main_window, "MainWindow"), (
        "main_window 包不应有 MainWindow 别名, 只用 SceneFabMainWindow"
    )
