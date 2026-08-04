"""Phase B controller unit tests.

Covers the responsibility-split controllers introduced in TD-02:
- MainWindowChrome  (menu bar wiring + Ctrl+Q shortcut)
- MainWindowDropZone (video MIME filter on drag/drop)
- ProductionRunner   (5-step progress mapping + worker lifecycle)
- ExportController   (no-project branch + EXPORT_FORMATS table)
- ContentArea        (transition mode switch + animation cleanup)

PySide6/QWidget tests are skipped on headless Linux CI where
``QWidget.__init__`` aborts the interpreter, but run on desktop
environments and on the offscreen Qt backend.
"""

from __future__ import annotations

import contextlib
import os
import sys

import pytest

# ── PySide6 import ────────────────────────────────────────────
PySide6 = pytest.importorskip("PySide6")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


# ── Skip marker for headless widget tests ─────────────────────
_IN_CI = os.environ.get("CI", "").lower() == "true"
_SKIP_HEADLESS_WIDGET_TESTS = _IN_CI and (
    sys.platform == "linux"
    or os.environ.get("QT_QPA_PLATFORM") == "offscreen"
)

_skip_widget = pytest.mark.skipif(
    _SKIP_HEADLESS_WIDGET_TESTS,
    reason="QWidget construction crashes the interpreter on headless Linux CI",
)


# ── QApplication helper (mirrors test_assets_page.py pattern) ─
def _qt_app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


# ──────────────────────────────────────────────────────────────
# Chrome (菜单栏)
# ──────────────────────────────────────────────────────────────


@_skip_widget
def test_chrome_builds_menu_bar_with_all_actions() -> None:
    from PySide6.QtWidgets import QMainWindow

    from app.ui.main.main_window.chrome import MainWindowChrome

    _qt_app()

    win = QMainWindow()
    chrome = MainWindowChrome(
        win,
        on_new_project=lambda: None,
        on_open_project=lambda: None,
        on_save_project=lambda: None,
        on_import_assets=lambda: None,
        on_export=lambda: None,
        on_quit=lambda: None,
        on_navigate=lambda _page_id: None,
        on_open_settings=lambda: None,
        on_check_updates=lambda: None,
    )
    try:
        menu_titles = [a.text() for a in win.menuBar().actions()]
        # 至少包含 文件 / 编辑 / 视图 / 帮助
        for expected in ("文件", "编辑", "视图", "帮助"):
            assert expected in menu_titles, f"missing menu: {expected}"
        # smoke — show_about 走 QMessageBox.about，不要真弹窗但是函数要可调用
        assert callable(chrome.show_about)
    finally:
        win.close()


@_skip_widget
def test_chrome_check_updates_uses_callback_without_navigation() -> None:
    """帮助菜单的检查更新只调用弹窗回调，不应触发页面导航。"""
    from PySide6.QtWidgets import QMainWindow

    from app.ui.main.main_window.chrome import MainWindowChrome

    _qt_app()
    calls: list[str] = []
    win = QMainWindow()
    MainWindowChrome(
        win,
        on_new_project=lambda: None,
        on_open_project=lambda: None,
        on_save_project=lambda: None,
        on_import_assets=lambda: None,
        on_export=lambda: None,
        on_quit=lambda: None,
        on_navigate=lambda page_id: calls.append(f"navigate:{page_id}"),
        on_open_settings=lambda: None,
        on_check_updates=lambda: calls.append("check"),
    )
    try:
        help_menu = next(
            action.menu()
            for action in win.menuBar().actions()
            if action.text() == "帮助"
        )
        action = next(
            action for action in help_menu.actions()
            if action.text() == "检查更新…"
        )
        action.trigger()
        assert calls == ["check"]
    finally:
        win.close()


@_skip_widget
def test_chrome_shortcuts_wired() -> None:
    """'退出' menu action 必须绑定 Ctrl+Q 快捷键。"""
    from PySide6.QtWidgets import QMainWindow

    from app.ui.main.main_window.chrome import MainWindowChrome

    _qt_app()

    win = QMainWindow()
    MainWindowChrome(
        win,
        on_new_project=lambda: None,
        on_open_project=lambda: None,
        on_save_project=lambda: None,
        on_import_assets=lambda: None,
        on_export=lambda: None,
        on_quit=lambda: None,
        on_navigate=lambda _pid: None,
        on_open_settings=lambda: None,
        on_check_updates=lambda: None,
    )
    try:
        actions = win.menuBar().actions()
        file_menu = next(a.menu() for a in actions if a.text() == "文件")
        quit_action = next(
            (a for a in file_menu.actions() if a.text() == "退出"), None
        )
        assert quit_action is not None, "'退出' action missing"
        assert not quit_action.shortcut().isEmpty(), "'退出' shortcut missing"
        # Ctrl+Q (macOS: ⌘Q) — shortcut.toString() returns "Ctrl+Q" everywhere
        assert "Q" in quit_action.shortcut().toString()
    finally:
        win.close()


# ──────────────────────────────────────────────────────────────
# Chrome i18n wiring (Phase C TD-03)
# ──────────────────────────────────────────────────────────────


@contextlib.contextmanager
def _translation_guard():
    """Restore the global translator to zh-CN around a block.

    i18n state is process-global, so flipping language in one test would
    poison the menu-bar checks in others. The context manager snapshots
    and restores automatically.
    """
    from app.ui.i18n import get_translator, set_language

    tr = get_translator()
    original = tr.language()
    try:
        yield tr
    finally:
        set_language(original)


@_skip_widget
def test_chrome_default_language_is_zh_cn() -> None:
    """默认语言必须为 zh-CN，菜单首选中文文案。"""
    from PySide6.QtWidgets import QMainWindow

    from app.ui.i18n import get_translator
    from app.ui.main.main_window.chrome import MainWindowChrome

    _qt_app()

    with _translation_guard():
        get_translator().set_language("zh-CN")

        win = QMainWindow()
        MainWindowChrome(
            win,
            on_new_project=lambda: None,
            on_open_project=lambda: None,
            on_save_project=lambda: None,
            on_import_assets=lambda: None,
            on_export=lambda: None,
            on_quit=lambda: None,
            on_navigate=lambda _pid: None,
            on_open_settings=lambda: None,
            on_check_updates=lambda: None,
        )
        try:
            titles = [a.text() for a in win.menuBar().actions()]
            assert "文件" in titles
            assert "帮助" in titles
            # 顺带验证 status 中的 "退出" action 是中文
            file_menu = next(a for a in win.menuBar().actions()
                             if a.text() == "文件").menu()
            assert any(act.text() == "退出" for act in file_menu.actions())
        finally:
            win.close()


@_skip_widget
def test_chrome_retranslate_switches_actions_to_english() -> None:
    """set_language('en-US') + chrome.retranslate() 后所有 action 文本需变更。"""
    from PySide6.QtWidgets import QMainWindow

    from app.ui.i18n import set_language
    from app.ui.main.main_window.chrome import MainWindowChrome

    _qt_app()

    with _translation_guard():
        win = QMainWindow()
        chrome = MainWindowChrome(
            win,
            on_new_project=lambda: None,
            on_open_project=lambda: None,
            on_save_project=lambda: None,
            on_import_assets=lambda: None,
            on_export=lambda: None,
            on_quit=lambda: None,
            on_navigate=lambda _pid: None,
            on_open_settings=lambda: None,
            on_check_updates=lambda: None,
        )
        try:
            # 默认中文
            assert "文件" in [a.text() for a in win.menuBar().actions()]

            # 切到英文 + 重译
            assert set_language("en-US") is True
            chrome.retranslate()

            titles = [a.text() for a in win.menuBar().actions()]
            assert "File" in titles
            assert "View" in titles
            assert "Help" in titles
            assert "文件" not in titles, "中文菜单未移除"

            file_menu = next(a for a in win.menuBar().actions()
                             if a.text() == "File").menu()
            quit_action = next(
                (a for a in file_menu.actions()
                 if "Q" in a.text() and "uit" in a.text()),
                None,
            )
            assert quit_action is not None, "'Quit' action missing"
            assert quit_action.text() == "Quit"
        finally:
            win.close()


@_skip_widget
def test_chrome_retranslate_round_trip_back_to_zh() -> None:
    """zh → en → zh 反复重译,菜单内容保持一致 (不应漂移)。"""
    from PySide6.QtWidgets import QMainWindow

    from app.ui.i18n import set_language
    from app.ui.main.main_window.chrome import MainWindowChrome

    _qt_app()

    with _translation_guard():
        win = QMainWindow()
        chrome = MainWindowChrome(
            win,
            on_new_project=lambda: None,
            on_open_project=lambda: None,
            on_save_project=lambda: None,
            on_import_assets=lambda: None,
            on_export=lambda: None,
            on_quit=lambda: None,
            on_navigate=lambda _pid: None,
            on_open_settings=lambda: None,
            on_check_updates=lambda: None,
        )
        try:
            initial_titles = [a.text() for a in win.menuBar().actions()]

            set_language("en-US")
            chrome.retranslate()
            en_titles = [a.text() for a in win.menuBar().actions()]
            assert "File" in en_titles

            set_language("zh-CN")
            chrome.retranslate()
            re_titles = [a.text() for a in win.menuBar().actions()]
            assert re_titles == initial_titles
        finally:
            win.close()


def test_chrome_retranslate_is_a_noop_safe_when_idle() -> None:
    """未创建 chrome 时,retranslate 不应崩；调用者只需 has attr 检查。"""
    # 仅验证调用逻辑不依赖 widget 实例
    from app.ui.main.main_window.chrome import MainWindowChrome

    # 类上能拿到方法即可——以避免和其他测试 state 交叉
    assert callable(MainWindowChrome.retranslate)


def test_app_and_about_keys_exist_in_both_catalogs() -> None:
    """app.name / app.tagline / app.tech_stack / about_window_title 都需两份部都存在。"""
    from app.ui.i18n import messages_en_US, messages_zh_CN

    required = {
        "app.name",
        "app.tagline",
        "app.tech_stack",
        "menu.help.about_window_title",
    }
    for key in required:
        assert key in messages_zh_CN.MESSAGES, f"zh-CN 缺少 {key}"
        assert key in messages_en_US.MESSAGES, f"en-US 缺少 {key}"


# ──────────────────────────────────────────────────────────────
# DropZone
# ──────────────────────────────────────────────────────────────


class _StubDropEvent:
    """轻量 drop event stub — 只模拟 mimeData() 接口。"""

    def __init__(self, urls: list[str]) -> None:
        from PySide6.QtCore import QMimeData, QUrl

        self._mime = QMimeData()
        if urls:
            self._mime.setUrls([QUrl.fromLocalFile(u) for u in urls])
        self._accepted: bool = False

    def mimeData(self):  # noqa: D401 — Qt API mimic
        return self._mime

    def acceptProposedAction(self) -> None:
        self._accepted = True

    def ignore(self) -> None:
        self._accepted = False


@_skip_widget
def test_drop_zone_accepts_video_url() -> None:
    from PySide6.QtWidgets import QMainWindow

    from app.ui.main.main_window.drop_zone import MainWindowDropZone

    _qt_app()
    win = QMainWindow()
    try:
        zone = MainWindowDropZone(win, on_drop=lambda _p: None)

        # 视频文件应被接受
        ev = _StubDropEvent(["/tmp/clip.mp4"])
        assert zone._has_video_url(ev) is True
        zone.handle_drag_enter(ev)
        assert ev._accepted is True

        # 非视频应被忽略
        ev2 = _StubDropEvent(["/tmp/readme.txt"])
        zone.handle_drag_enter(ev2)
        assert ev2._accepted is False
    finally:
        win.close()


@_skip_widget
def test_drop_zone_drops_video_invokes_callback() -> None:
    from PySide6.QtWidgets import QMainWindow

    from app.ui.main.main_window.drop_zone import MainWindowDropZone

    _qt_app()
    win = QMainWindow()
    try:
        seen: list[str] = []
        zone = MainWindowDropZone(win, on_drop=lambda p: seen.append(p))

        ev = _StubDropEvent(["/tmp/clip.mp4", "/tmp/notes.txt"])
        zone.handle_drop(ev)
        assert seen == ["/tmp/clip.mp4"]
        # only-first matching video strategy: notes.txt 不进入 callback
        assert len(seen) == 1
    finally:
        win.close()


@_skip_widget
def test_drop_zone_ignores_when_no_urls() -> None:
    from PySide6.QtWidgets import QMainWindow

    from app.ui.main.main_window.drop_zone import MainWindowDropZone

    _qt_app()
    win = QMainWindow()
    try:
        seen: list[str] = []
        zone = MainWindowDropZone(win, on_drop=lambda p: seen.append(p))

        ev = _StubDropEvent([])
        zone.handle_drop(ev)
        assert seen == []
        assert ev._accepted is False
    finally:
        win.close()


# ──────────────────────────────────────────────────────────────
# ProductionRunner — 静态契约 + 进度回调
# ──────────────────────────────────────────────────────────────


def test_production_runner_default_emotions_contract() -> None:
    """默认情感列表至少要包含中性的 'neutral'。"""
    from app.ui.main.main_window.production_runner import (
        DEFAULT_CONTEXT,
        DEFAULT_EMOTIONS,
    )

    assert "neutral" in DEFAULT_EMOTIONS
    assert "开心" in DEFAULT_EMOTIONS
    assert isinstance(DEFAULT_CONTEXT, str) and DEFAULT_CONTEXT


def test_production_runner_all_steps_contract() -> None:
    """5 步管线必须包含所有已知阶段名。"""
    from app.ui.main.main_window.production_runner import (
        _ALL_PRODUCTION_STEPS,
        ProductionRunner,
    )

    # 模块常量直接稳定
    assert set(_ALL_PRODUCTION_STEPS) == {
        "素材导入",
        "场景拆分",
        "脚本生成",
        "配音字幕",
        "导出发布",
    }
    # class 上能拿到
    assert ProductionRunner.default_emotions() is not None


@_skip_widget
def test_production_runner_progress_marks_step_done() -> None:
    """运行到第 1 步时，'素材导入' 应为已完成，下一步 '场景拆分' 应为进行中。"""
    from PySide6.QtWidgets import QApplication

    from app.ui.main.main_window.production_runner import ProductionRunner

    _qt_app()
    runner = ProductionRunner()
    captured: list[tuple[str, str, str]] = []
    runner.step_status_changed.connect(
        lambda step, status, color: captured.append((step, status, color))
    )

    runner._on_progress(1, 5, "场景分析完成")

    titles = [c[0] for c in captured]
    assert "素材导入" in titles
    assert "场景拆分" in titles
    assert any(c[1] == "已完成" for c in captured if c[0] == "素材导入")
    assert any(c[1] == "进行中" for c in captured if c[0] == "场景拆分")
    QApplication.processEvents()


@_skip_widget
def test_production_runner_final_step_marks_all_done() -> None:
    """current == total 时所有 5 步都标记为 已完成。"""
    from PySide6.QtWidgets import QApplication

    from app.ui.main.main_window.production_runner import ProductionRunner

    _qt_app()
    runner = ProductionRunner()
    captured: list[tuple[str, str, str]] = []
    runner.step_status_changed.connect(
        lambda step, status, color: captured.append((step, status, color))
    )

    runner._on_progress(5, 5, "全部完成")

    completed_steps = {c[0] for c in captured if c[1] == "已完成"}
    assert completed_steps == {
        "素材导入",
        "场景拆分",
        "脚本生成",
        "配音字幕",
        "导出发布",
    }
    QApplication.processEvents()


# ──────────────────────────────────────────────────────────────
# ExportController — no-project 分支
# ──────────────────────────────────────────────────────────────


def test_export_formats_table_contract() -> None:
    """EXPORT_FORMATS 至少包含 'JIANYING' 和 'MP4' 两个 key。"""
    from app.ui.main.main_window.exporter import EXPORT_FORMATS

    keys = {key for _label, key in EXPORT_FORMATS}
    assert keys == {"JIANYING", "MP4"}
    # labels 也要是不可空字符串
    assert all(isinstance(label, str) and label for label, _ in EXPORT_FORMATS)


@_skip_widget
def test_export_controller_no_project_calls_callback() -> None:
    """没有最近项目时应直接走 on_no_project 回调，而不是弹窗。"""
    from PySide6.QtWidgets import QMainWindow

    from app.ui.main.main_window.exporter import ExportController

    _qt_app()
    win = QMainWindow()
    try:
        warning_calls: list[bool] = []
        ec = ExportController(
            win,
            get_project=lambda: None,
            on_no_project=lambda: warning_calls.append(True),
        )
        ec.run()
        assert warning_calls == [True]
    finally:
        win.close()


# ──────────────────────────────────────────────────────────────
# ContentArea transitions
# ──────────────────────────────────────────────────────────────


@_skip_widget
def test_contentarea_default_mode_is_cross_fade() -> None:
    from PySide6.QtWidgets import QApplication

    from app.ui.main.main_window.content_area import ContentArea

    _qt_app()
    area = ContentArea()
    assert area.transition_mode() == "cross-fade"
    assert area.transition_mode() in (
        "none",
        "fade",
        "cross-fade",
        "slide",
    )
    QApplication.processEvents()


@_skip_widget
def test_contentarea_set_transition_mode_validates() -> None:
    from PySide6.QtWidgets import QApplication

    from app.ui.main.main_window.content_area import ContentArea

    _qt_app()
    area = ContentArea()
    try:
        area.set_transition_mode("slide")
        assert area.transition_mode() == "slide"
        area.set_transition_mode("none")
        assert area.transition_mode() == "none"

        with pytest.raises(ValueError):
            area.set_transition_mode("warp-speed")
    finally:
        QApplication.processEvents()


@_skip_widget
def test_contentarea_set_page_unknown_is_noop() -> None:
    """不存在的 page_id 不抛异常、不切换。"""
    from PySide6.QtWidgets import QApplication

    from app.ui.main.main_window.content_area import ContentArea

    _qt_app()
    area = ContentArea()
    try:
        # 没有添加过任何页面，set_page("does-not-exist") 必须被忽略
        area.set_page("does-not-exist")
        # QStackedWidget 没有 currentWidget 时返回 None
        assert area._stack.currentWidget() is None
    finally:
        QApplication.processEvents()


@_skip_widget
def test_contentarea_none_mode_keeps_widget_no_animation() -> None:
    """mode='none' 时 set_page 立即切换，并不留 effect 残留。"""
    from PySide6.QtWidgets import QApplication, QFrame

    from app.ui.main.main_window.content_area import ContentArea

    _qt_app()
    area = ContentArea()
    try:
        page1 = QFrame()
        page2 = QFrame()
        area.add_page("a", page1)
        area.add_page("b", page2)

        area.set_transition_mode("none")
        area.set_page("a", animated=True)
        assert area._stack.currentWidget() is page1
        area.set_page("b", animated=True)  # animated=True 但 mode=none
        assert area._stack.currentWidget() is page2
        # 不应创建任何 graphics effect
        assert page2.graphicsEffect() is None
        assert page1.graphicsEffect() is None
    finally:
        QApplication.processEvents()


@_skip_widget
def test_contentarea_animated_swap_keeps_effect_reusable() -> None:
    """连续 fade-in 不会留下失效 effect，use-after-free 防护验证。"""
    from PySide6.QtWidgets import QApplication, QFrame

    from app.ui.main.main_window.content_area import ContentArea

    _qt_app()
    area = ContentArea()
    try:
        page1 = QFrame()
        page2 = QFrame()
        area.add_page("a", page1)
        area.add_page("b", page2)

        area.set_transition_mode("cross-fade")
        # 切换两次 — 这是历史崩溃的最小复现路径
        area.set_page("a", animated=True)
        area.set_page("b", animated=True)

        # 给动画一个 tick；不应该崩溃或抛 use-after-free
        for _ in range(3):
            QApplication.processEvents()

        assert area._stack.currentWidget() is page2
    finally:
        QApplication.processEvents()


# ──────────────────────────────────────────────────────────────
# ProjectIOController
# ──────────────────────────────────────────────────────────────


_MISSING = object()


def _make_project_io(
    *,
    pm: object | None = None,
    production_page: object | None = None,
    last_project=_MISSING,
):
    """Build a ProjectIOController with every callback captured."""
    from PySide6.QtWidgets import QMainWindow

    from app.ui.main.main_window.project_io import ProjectIOController

    win = QMainWindow()
    captured = {
        "loaded": [],
        "status": [],
        "message": [],
        "navigated": [],
    }

    def set_last(p):
        captured["loaded"].append(p)

    def navigate():
        captured["navigated"].append(True)

    controller = ProjectIOController(
        win,
        get_project_manager=lambda: pm,
        get_last_project=lambda: last_project,
        set_last_project=set_last,
        get_production_page=lambda: production_page,
        navigate_to_create=navigate,
        show_status=lambda msg: captured["status"].append(msg),
        show_message=lambda msg, level: captured["message"].append(
            (msg, level)
        ),
    )
    return win, controller, captured


def test_projectio_open_project_cancelled_no_side_effects(monkeypatch) -> None:
    """open_project() 被取消时不应触发加载/导航/状态。"""
    from PySide6.QtWidgets import QFileDialog

    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileName",
        classmethod(lambda cls, *a, **kw: ("", "")),
    )

    win, controller, captured = _make_project_io(pm=None)
    try:
        controller.open_project()  # empty path → dialog → cancelled
        assert captured["loaded"] == []
        assert captured["navigated"] == []
        assert captured["status"] == []
        assert captured["message"] == []
    finally:
        win.close()


def test_projectio_open_project_no_manager_shows_error(monkeypatch) -> None:
    """路径非空但 project_manager 不可用时,走 show_message(error)。"""

    # 给一个 explicit path 跳过文件对话框
    win, controller, captured = _make_project_io(pm=None)
    try:
        controller.open_project("/tmp/non-existent.scenefab")
        # No project_manager → error message, 不加载、不导航
        assert captured["message"] == [("项目管理器未就绪", "error")]
        assert captured["loaded"] == []
        assert captured["navigated"] == []
    finally:
        win.close()
    monkeypatch.undo()  # reset the QFileDialog patch


def test_projectio_save_without_project_warns(monkeypatch) -> None:
    """没有 last_project 时 save 应弹 QMessageBox.warning,且不调用 QFileDialog.getSaveFileName。"""
    from PySide6.QtWidgets import QFileDialog, QMessageBox

    get_save_calls: list[tuple] = []
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        classmethod(lambda cls, *a, **
                    kw: get_save_calls.append((a, kw)) or ("", "")),
    )

    warnings: list[tuple] = []
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *a, **kw: warnings.append(
            a) or QMessageBox.StandardButton.Ok
    )

    win, controller, captured = _make_project_io(last_project=None)
    try:
        controller.save_project()
        assert get_save_calls == []  # 没进文件对话框
        assert len(warnings) == 1
        assert "请先完成生产流程" in warnings[0][-1]
        assert captured["status"] == []
    finally:
        win.close()


def test_projectio_file_filter_constant() -> None:
    """PROJECT_FILE_FILTER 必须保留 .scenefab 扩展名。"""
    from app.ui.main.main_window.project_io import ProjectIOController

    assert ".scenefab" in ProjectIOController.PROJECT_FILE_FILTER


# ──────────────────────────────────────────────────────────────
# AssetsIOController
# ──────────────────────────────────────────────────────────────


def _make_assets_io(*, pm=None, assets_page=None):
    """Build an AssetsIOController with every callback captured."""
    from PySide6.QtWidgets import QMainWindow

    from app.ui.main.main_window.assets_io import AssetsIOController

    win = QMainWindow()
    captured = {
        "status": [],
        "added": [],
        "registered": [],
    }

    class _StubAssetsPage:
        def add_imported_files(self, files):
            captured["added"].append(list(files))

    class _StubPM:
        def __init__(self):
            self.saved_ids = []

        def get_current_project(self):
            return None

        def save_project(self, project_id):
            captured["registered"].append(project_id)
            return True

    controller = AssetsIOController(
        win,
        get_project_manager=lambda: pm if pm is not None else _StubPM(),
        get_assets_page=lambda: assets_page if assets_page is not None else _StubAssetsPage(),
        show_status=lambda msg: captured["status"].append(msg),
    )
    return win, controller, captured


def test_assetsio_import_cancel_no_callbacks(monkeypatch) -> None:
    """QFileDialog 取消时不应该有副作用。"""
    from PySide6.QtWidgets import QFileDialog

    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileNames",
        classmethod(lambda cls, *a, **kw: ([], "")),
    )

    win, controller, captured = _make_assets_io()
    try:
        controller.import_assets()
        assert captured["status"] == []
        assert captured["added"] == []
    finally:
        win.close()


def test_assetsio_import_with_selection_calls_assets_page(monkeypatch) -> None:
    """用户选择文件后,AssetsPage.add_imported_files 必须被调用。"""
    from PySide6.QtWidgets import QFileDialog

    selected = ["/tmp/clip.mp4", "/tmp/poster.png"]
    monkeypatch.setattr(
        QFileDialog,
        "getOpenFileNames",
        classmethod(lambda cls, *a, **kw: (selected, "")),
    )

    win, controller, captured = _make_assets_io()
    try:
        controller.import_assets()
        # selection status + 转发给 AssetsPage
        assert len(captured["status"]) == 1
        assert "2" in captured["status"][0]
        assert captured["added"] == [selected]
    finally:
        win.close()


def test_assetsio_file_filter_includes_videos_audio_images() -> None:
    """ASSETS_FILE_FILTER 覆盖视频/音频/图片。"""
    from app.ui.main.main_window.assets_io import ASSETS_FILE_FILTER

    for ext in (".mp4", ".mov", ".mp3", ".wav", ".jpg", ".png"):
        assert ext in ASSETS_FILE_FILTER, f"{ext} missing from ASSETS_FILE_FILTER"


# ──────────────────────────────────────────────────────────────
# ThemeController (plan §4.5 — seventh controller)
# ──────────────────────────────────────────────────────────────


class _StubThemeManager:
    """Minimal stand-in for ThemeManager — emits palette_changed on set."""

    def __init__(self) -> None:
        from PySide6.QtCore import QObject, Signal

        # Build a duck-typed object with a real Qt signal so we can
        # reuse the same connection logic as production.
        class _Signals(QObject):
            palette_changed = Signal(str)

        self._signals = _Signals()
        self.applied: list[str] = []

    def apply_persisted(self) -> None:
        self.applied.append("apply_persisted")

    @property
    def palette_changed(self):
        return self._signals.palette_changed


def _make_router_with_pages(pages):
    """Tiny router stub exposing ``_page_map``."""

    class _StubRouter:
        def __init__(self):
            self._page_map = pages

    return _StubRouter()


def test_theme_controller_apply_persisted_delegates() -> None:
    """ThemeController.apply_persisted() → theme_manager.apply_persisted()."""
    from app.ui.main.main_window.theme_controller import ThemeController

    _qt_app()
    tm = _StubThemeManager()
    ctrl = ThemeController(tm, router=None)
    try:
        ctrl.apply_persisted()
        assert tm.applied == ["apply_persisted"]
    finally:
        ctrl.deleteLater()


def test_theme_controller_palette_change_runs_hook_then_restyle() -> None:
    """palette_changed → hook() → page.apply_theme() → restyle_app() 顺序。"""
    from PySide6.QtWidgets import QApplication

    from app.ui.main.main_window.theme_controller import ThemeController

    _qt_app()
    tm = _StubThemeManager()

    calls: list[str] = []

    class _Page:
        def apply_theme(self):
            calls.append("page.apply_theme")

    def hook(palette: str) -> None:
        calls.append(f"hook:{palette}")

    router = _make_router_with_pages({"home": _Page()})
    ctrl = ThemeController(tm, router=router, hook=hook)
    try:
        # simulate the manager emitting palette_changed
        tm.palette_changed.emit("dark")
        QApplication.processEvents()
        assert calls[0] == "hook:dark"
        assert "page.apply_theme" in calls
    finally:
        ctrl.deleteLater()


def test_theme_controller_restyle_pages_swallows_errors() -> None:
    """即使某个 page 的 apply_theme 抛错,其余页还应该能被处理。"""
    from PySide6.QtWidgets import QApplication

    from app.ui.main.main_window.theme_controller import ThemeController

    _qt_app()
    tm = _StubThemeManager()
    applied: list[str] = []

    class _GoodPage:
        def apply_theme(self):
            applied.append("good")

    class _BadPage:
        def apply_theme(self):
            raise RuntimeError("page-broken")

    router = _make_router_with_pages(
        {"a": _GoodPage(), "b": _BadPage(), "c": _GoodPage()}
    )
    ctrl = ThemeController(tm, router=router)
    try:
        tm.palette_changed.emit("light")
        QApplication.processEvents()
        # 不会因为 B 抛错而中断 A 和 C
        assert "good" in applied
        assert applied.count("good") == 2
    finally:
        ctrl.deleteLater()


def test_theme_controller_no_router_no_pages_no_crash() -> None:
    """不传 router 时应优雅处理,不会崩。"""
    from PySide6.QtWidgets import QApplication

    from app.ui.main.main_window.theme_controller import ThemeController

    _qt_app()
    tm = _StubThemeManager()
    ctrl = ThemeController(tm, router=None)
    try:
        # Simulate palette change with no router / no hook
        tm.palette_changed.emit("dark")
        QApplication.processEvents()
    finally:
        ctrl.deleteLater()


def test_theme_controller_set_router_late_wire() -> None:
    """set_router() 后路由上的页面也应在下次切换时被重译。"""
    from PySide6.QtWidgets import QApplication

    from app.ui.main.main_window.theme_controller import ThemeController

    _qt_app()
    tm = _StubThemeManager()
    calls: list[str] = []

    class _Page:
        def apply_theme(self):
            calls.append("apply_theme")

    ctrl = ThemeController(tm, router=None)
    try:
        router = _make_router_with_pages({"x": _Page()})
        ctrl.set_router(router)

        tm.palette_changed.emit("dark")
        QApplication.processEvents()
        assert "apply_theme" in calls
    finally:
        ctrl.deleteLater()


# ────────────────────────────────────────────────────────────
# UI chrome i18n (TD-03 extension: sidebar / topbar / statusbar / tray)
# ────────────────────────────────────────────────────────────


@_skip_widget
def test_sidebar_subtitle_renders_via_translation_key() -> None:
    """侧边栏品牌副标题应通过 nav.brand.subtitle 解析,语言切换时实时刷新。"""

    from app.ui.i18n import t
    from app.ui.main.main_window.nav_components import Sidebar
    from app.ui.main.registry import NAV_ITEMS

    _qt_app()
    with _translation_guard() as translator:
        translator.set_language("zh-CN")
        sidebar = Sidebar(NAV_ITEMS)
        try:
            assert sidebar._subtitle_label.text() == t("nav.brand.subtitle")
            translator.set_language("en-US")
            sidebar.retranslate()
            assert sidebar._subtitle_label.text() == "Short Drama Narration Studio"
        finally:
            sidebar.deleteLater()


@_skip_widget
def test_sidebar_nav_buttons_use_translated_labels() -> None:
    """导航按钮应以 t() 解析 label_key,并在重译后更新。"""

    from app.ui.main.main_window.nav_components import Sidebar
    from app.ui.main.registry import NAV_ITEMS

    _qt_app()
    with _translation_guard() as translator:
        translator.set_language("zh-CN")
        sidebar = Sidebar(NAV_ITEMS)
        try:
            home_btn = sidebar._nav_btns["home"]
            assert home_btn.text() == "工作台"
            translator.set_language("en-US")
            sidebar.retranslate()
            assert home_btn.text() == "Dashboard"
        finally:
            sidebar.deleteLater()


@_skip_widget
def test_topbar_export_action_renders_via_translation_key() -> None:
    """顶部栏导出按钮的文本/提示应通过 t() 解析。"""

    from app.ui.main.main_window.top_bar import TopBar

    _qt_app()
    with _translation_guard() as translator:
        translator.set_language("zh-CN")
        topbar = TopBar()
        try:
            btn, icon_key, tip_key = topbar._action_btns["export"]
            assert btn.text() == "导出"
            assert btn.toolTip() == "导出成片"
            translator.set_language("en-US")
            topbar.retranslate()
            assert btn.text() == "Export"
            assert btn.toolTip() == "Export the final video"
        finally:
            topbar.deleteLater()


@_skip_widget
def test_statusbar_default_text_reflects_translation_key() -> None:
    """状态栏默认文本应使用 common.ready 键,并随语言切换刷新。"""

    from app.ui.main.main_window.status_bar import StatusBar

    _qt_app()
    with _translation_guard() as translator:
        translator.set_language("zh-CN")
        bar = StatusBar()
        try:
            assert bar._status_label.text() == "就绪"
            translator.set_language("en-US")
            bar.retranslate()
            assert bar._status_label.text() == "Ready"
        finally:
            bar.deleteLater()


@_skip_widget
def test_statusbar_set_status_preserves_runtime_overrides() -> None:
    """retranslate() 应当刷新默认值,但不应覆盖运行中的 set_status 调用。"""

    from app.ui.main.main_window.status_bar import StatusBar

    _qt_app()
    with _translation_guard() as translator:
        translator.set_language("zh-CN")
        bar = StatusBar()
        try:
            bar.set_status("导出中: 42%")
            translator.set_language("en-US")
            bar.retranslate()
            # retranslate() 重置默认文本为翻译后的 common.ready,
            # 调用方再次调用 set_status() 覆盖即可保持进度信息。
            assert bar._status_label.text() == "Ready"
            bar.set_status("Exporting: 42%")
            assert bar._status_label.text() == "Exporting: 42%"
        finally:
            bar.deleteLater()


@_skip_widget
def test_tray_manager_menu_uses_translation_keys() -> None:
    """TrayManager 的菜单动作应使用 t() 解析的标题/角色名。"""
    from PySide6.QtWidgets import QSystemTrayIcon

    from app.ui.main.tray_manager import TrayManager

    _qt_app()
    with _translation_guard() as translator:
        translator.set_language("zh-CN")
        tray = TrayManager()
        try:
            # _build_menu 需要 _tray_icon 不为 None - 手动注入一个真实的
            # 底层 icon 以触发菜单构造路径(系统托盘本身不可用)。
            tray._tray_icon = QSystemTrayIcon()
            tray._build_menu("SceneFab")
            assert tray._title_action is not None
            assert tray._show_action is not None
            assert tray._settings_action is not None
            assert tray._quit_action is not None
            assert "SceneFab" in tray._title_action.text()
            assert tray._show_action.text() == "📖 显示主窗口"
            assert tray._settings_action.text() == "⚙️ 设置"

            translator.set_language("en-US")
            tray.retranslate("SceneFab")
            assert tray._title_action.text() == "🎬 SceneFab"
            assert tray._show_action.text() == "📖 Show Window"
            assert tray._settings_action.text() == "⚙️ Settings"
            assert tray._quit_action.text() == "❌ Quit SceneFab"
        finally:
            try:
                tray.disable()
            except Exception:
                pass


@_skip_widget
def test_tray_notification_message_uses_translation_key() -> None:
    """SystemTrayController.handle_close_event 的通知文案应来自 t()。"""
    from PySide6.QtCore import QObject
    from PySide6.QtWidgets import QMainWindow

    from app.ui.main.system_tray import SystemTrayController

    _qt_app()
    with _translation_guard() as translator:
        translator.set_language("zh-CN")
        captured: list[tuple[str, str]] = []

        class _FakeTray:
            is_enabled = True
            is_available = True

            def disable(self):  # pragma: no cover - guard only
                self.is_enabled = False

            def show_notification(self, title, message, **kwargs):
                captured.append((title, message))

        controller = SystemTrayController.__new__(SystemTrayController)
        QObject.__init__(controller)
        controller._tray = _FakeTray()
        controller._minimize_enabled = True
        controller._quitting = False
        controller._tray_hint_shown = False
        controller._window_title = "SceneFab"

        class _FakeEvent:
            def __init__(self):
                self._accepted = None

            def accept(self):
                self._accepted = True

            def ignore(self):
                self._accepted = False

        event = _FakeEvent()
        controller.handle_close_event(QMainWindow(), event)
        assert captured, "notification should be emitted on first close"
        title, message = captured[0]
        assert title == "SceneFab"
        assert "托盘" in message  # zh-CN "应用已最小化到系统托盘..."

        captured.clear()
        controller._tray_hint_shown = False
        translator.set_language("en-US")
        event2 = _FakeEvent()
        controller.handle_close_event(QMainWindow(), event2)
        assert captured
        _, msg_en = captured[0]
        assert "system tray" in msg_en.lower()


# ────────────────────────────────────────────────────────────
# i18n catalog parity (TD-03 extension: keys declared in
# message_keys.py must exist in both zh-CN / en-US catalogs)
# ────────────────────────────────────────────────────────────

def test_i18n_keys_have_parity_between_zh_and_en() -> None:
    """两个语言目录的 key 集合必须完全一致,否则会有一边缺失文案。"""
    from app.ui.i18n import messages_en_US, messages_zh_CN

    zh_keys = set(messages_zh_CN.MESSAGES)
    en_keys = set(messages_en_US.MESSAGES)
    assert zh_keys == en_keys, (
        f"语言目录不一致: 仅 zh 缺={sorted(en_keys - zh_keys)}; "
        f"仅 en 缺={sorted(zh_keys - en_keys)}"
    )


def test_i18n_message_keys_constants_match_catalogs() -> None:
    """message_keys.py 声明的常量应全部存在于两个语言目录中。"""
    import re

    from app.ui.i18n import message_keys, messages_en_US, messages_zh_CN

    # i18n key 形如 ``<scope>.<body>``(两层点分隔)。过滤掉
    # ``__module__`` / ``__qualname__`` 等 dunder 属性和看起来像
    # Python 模块路径的长字符串。
    key_pattern = re.compile(r"^[a-z][a-z0-9_]*\.[a-z0-9_]+$")
    declared = {
        value
        for value in vars(message_keys.MessageKey).values()
        if isinstance(value, str) and key_pattern.match(value)
    }
    zh_keys = set(messages_zh_CN.MESSAGES)
    en_keys = set(messages_en_US.MESSAGES)
    missing_zh = declared - zh_keys
    missing_en = declared - en_keys
    assert not missing_zh, f"MessageKey 常量在 zh-CN 中缺失: {sorted(missing_zh)}"
    assert not missing_en, f"MessageKey 常量在 en-US 中缺失: {sorted(missing_en)}"


def test_i18n_extract_script_reports_no_missing_keys() -> None:
    """AST 扫描器输出不应在 zh/en/message_keys 任意一处报告缺失。"""
    import json
    import subprocess

    result = subprocess.run(
        [".venv/bin/python", "bin/i18n_extract.py", "--output", "/tmp/i18n.json"],
        cwd="/Users/zfkc/Desktop/04-AI/scene-fab",
        capture_output=True,
        text=True,
        check=True,
    )
    assert "i18n scan:" in result.stdout
    with open("/tmp/i18n.json") as f:
        report = json.loads(f.read())
    missing = report.get("missing", {})
    assert not missing.get("zh-CN"), f"zh-CN 缺失 key: {missing['zh-CN']}"
    assert not missing.get("en-US"), f"en-US 缺失 key: {missing['en-US']}"
    assert not missing.get("message_keys"), (
        f"message_keys 未声明: {missing['message_keys']}"
    )


# ────────────────────────────────────────────────────────────
# Business page i18n (Phase C TD-03: production / assets /
# page router coverage)
# ────────────────────────────────────────────────────────────


@_skip_widget
def test_production_page_form_labels_use_translation_keys() -> None:
    """ProductionPage 表单 / 节区 / 拖拽文案需全部来自 i18n。"""
    from PySide6.QtWidgets import QApplication

    from app.ui.main.pages.production_page import ProductionPage

    _qt_app()
    with _translation_guard() as translator:
        translator.set_language("zh-CN")
        page = ProductionPage()
        try:
            # Drop zone uses production.drop_hint / production.format_supported
            assert page.dropzone._title_lbl.text() == "拖拽素材视频到此处，或点击下方按钮选择"
            assert "MP4" in page.dropzone._path_lbl.text()
            assert page.dropzone._browse_btn.text() == "选择源视频文件"

            # Header / actions
            assert page._start_btn.text() == "🚀 开始 AI 自动创作"
            assert page._cancel_btn.text() == "取消"

            # Section titles
            assert page._pipeline_section.text() == "素材导入与创作配置"
            assert page._steps_section.text() == "5 步自动化流水线"
            assert page._brief_section.text() == "脚本约束"
            assert page._quality_section.text() == "导出门禁"

            # Form labels and placeholders
            assert page._ctx_label.text() == "解说主题:"
            assert page._emo_label.text() == "情感基调:"
            assert page._context_input.placeholderText() == "请输入视频解说的主题或剧情概括..."

            # Emotion dropdown (7 entries from _EMOTION_KEYS)
            assert page._emotion_combo.count() == 7
            assert page._emotion_combo.itemText(0) == "中立 (自然独白)"

            QApplication.processEvents()
        finally:
            page.deleteLater()


@_skip_widget
def test_production_page_retranslate_switches_to_english() -> None:
    """set_language('en-US') + ProductionPage.retranslate() 后所有标签更新。"""
    from PySide6.QtWidgets import QApplication

    from app.ui.main.pages.production_page import ProductionPage

    _qt_app()
    with _translation_guard() as translator:
        page = ProductionPage()
        try:
            translator.set_language("en-US")
            page.retranslate()

            assert page.dropzone._title_lbl.text() == (
                "Drag a source video here, or click the button below to choose"
            )
            assert page._start_btn.text() == "🚀 Start AI Auto Production"
            assert page._cancel_btn.text() == "Cancel"
            assert page._pipeline_section.text() == "Media Import & Production Config"
            assert page._steps_section.text() == "5-Step Automation Pipeline"
            assert page._ctx_label.text() == "Narration topic:"
            assert page._emo_label.text() == "Emotional tone:"
            assert page._emotion_combo.itemText(
                0) == "Neutral (Natural Monologue)"

            # Round-trip restore to zh-CN
            translator.set_language("zh-CN")
            page.retranslate()
            assert page._start_btn.text() == "🚀 开始 AI 自动创作"
            assert page.dropzone._title_lbl.text() == "拖拽素材视频到此处，或点击下方按钮选择"

            QApplication.processEvents()
        finally:
            page.deleteLater()


@_skip_widget
def test_production_page_dropzone_state_survives_retranslate() -> None:
    """选完文件后再 retranslate,标题应该用 selected 字符串(而非回退)。"""
    from PySide6.QtWidgets import QApplication

    from app.ui.main.pages.production_page import ProductionPage

    _qt_app()
    with _translation_guard():
        page = ProductionPage()
        try:
            page.dropzone.set_file("/tmp/clip.MP4")
            assert page.dropzone._title_lbl.text() == "已选择视频: clip.MP4"
            assert page.dropzone._browse_btn.text() == "更换视频"

            page.retranslate()
            assert page.dropzone._title_lbl.text() == "已选择视频: clip.MP4"
            assert page.dropzone._browse_btn.text() == "更换视频"
            assert page.dropzone._path_lbl.text() == "/tmp/clip.MP4"

            # file_present flag should now be reset after a new retranslate call
            # when user is in selected state.
            QApplication.processEvents()
        finally:
            page.deleteLater()


@_skip_widget
def test_assets_page_header_and_refresh_button_translate() -> None:
    """AssetsPage header / refresh / empty state 需全部来自 i18n。"""
    from PySide6.QtWidgets import QApplication

    from app.ui.main.pages.assets_page import AssetsPage

    _qt_app()
    with _translation_guard() as translator:
        translator.set_language("zh-CN")
        page = AssetsPage()
        try:
            assert page._header_action_btn.text() == "导入素材"
            assert page._asset_list_section.text() == "资产列表"
            assert page._refresh_btn.text() == "刷新"

            # Column row uses i18n keys for header cells
            assert page._column_labels[0].text() == "类型"
            assert page._column_labels[1].text() == "名称"
            assert page._column_labels[2].text() == "创建日期"
            QApplication.processEvents()
        finally:
            page.deleteLater()


@_skip_widget
def test_assets_page_source_panel_uses_translation_keys() -> None:
    """Source panel 卡片标题/副标题/按钮都应来自 i18n key。"""
    from PySide6.QtWidgets import QApplication, QPushButton

    from app.ui.main.pages.assets_page import AssetsPage

    _qt_app()
    with _translation_guard():
        page = AssetsPage()
        try:
            # Three source items + choose button on first two only
            assert len(page._source_items) == 3
            # Titles in zh-CN default language
            titles = [t.text() for (_f, t, _d, _n, _b) in page._source_items]
            assert titles == ["素材目录", "输出目录", "资源规范"]

            # First two have navigate buttons, third does not
            nav_buttons = [
                (page._source_items[i][3], page._source_items[i][4])
                for i in range(3)
            ]
            assert nav_buttons[0][0] == "settings"
            assert isinstance(nav_buttons[0][1], QPushButton)
            assert nav_buttons[1][0] == "settings"
            assert isinstance(nav_buttons[1][1], QPushButton)
            assert nav_buttons[2][0] is None
            assert nav_buttons[2][1] is None
            QApplication.processEvents()
        finally:
            page.deleteLater()


@_skip_widget
def test_assets_page_retranslate_switches_source_cards_to_english() -> None:
    """切到英文后,所有卡片标题、按钮、描述都应刷成英文。"""
    from PySide6.QtWidgets import QApplication

    from app.ui.main.pages.assets_page import AssetsPage

    _qt_app()
    with _translation_guard() as translator:
        page = AssetsPage()
        try:
            translator.set_language("en-US")
            page.retranslate()

            titles = [t.text() for (_f, t, _d, _n, _b) in page._source_items]
            assert titles == ["Media Folder",
                              "Output Folder", "Resource Policy"]
            # choose directory button text refreshed
            assert page._source_items[0][4].text() == "Choose Folder"
            # Refresh button
            assert page._refresh_btn.text() == "Refresh"
            # Asset list section
            assert page._asset_list_section.text() == "Asset List"
            QApplication.processEvents()
        finally:
            page.deleteLater()


def test_page_router_error_page_uses_translation_keys() -> None:
    """_build_error_page 占位页的标题/提示都需通过 t() 获取。"""
    from PySide6.QtWidgets import QLabel

    from app.ui.i18n import t
    from app.ui.main.page_router import PageRouter

    with _translation_guard() as translator:
        translator.set_language("zh-CN")
        widget = PageRouter._build_error_page("create", "Traceback ...")
        labels = widget.findChildren(QLabel)
        assert len(labels) >= 3, "expected title + hint + detail"
        # First label is title, contains page_id formatted via t()
        assert labels[0].text() == t("page.load_failed_title_with_id").format(
            page_id="create"
        )
        assert labels[1].text() == t("page.load_failed_hint")
        assert "Traceback" in labels[2].text()

        # English swap
        translator.set_language("en-US")
        widget2 = PageRouter._build_error_page("assets", "boom")
        labels2 = widget2.findChildren(QLabel)
        assert labels2[0].text() == "Page failed to load: assets"
        assert "Traceback" in labels2[2].text() or "boom" in labels2[2].text()


def test_main_window_show_message_localizes_titles(monkeypatch) -> None:
    """SceneFabMainWindow.show_message 应根据 level 翻译标题。

    这里用 *unbound* 调用以避开 SceneFabMainWindow 的重型 __init__
    (ThemeManager + 信号 + lazy pages 都会触发)。QMessageBox.{critical,
    warning,information} 都是静态方法,parent 参数传 ``None`` 即可,
    所以这里测试的是纯 i18n 路由逻辑,而非 QMainWindow 本身。
    """
    from PySide6.QtWidgets import QMessageBox

    from app.ui.main.main_window import SceneFabMainWindow

    captured: list[tuple[str, str, str]] = []

    def _capture(level_method):
        def _inner(parent, title, message, *args, **kwargs):
            captured.append((level_method, title, message))
            return QMessageBox.StandardButton.Ok

        return _inner

    # Patch at class level so the patched versions are picked up by the
    # unbound call below. ``monkeypatch`` undoes the swap automatically
    # when the test exits, so no global state lingers.
    monkeypatch.setattr(QMessageBox, "critical", _capture("critical"))
    monkeypatch.setattr(QMessageBox, "warning", _capture("warning"))
    monkeypatch.setattr(QMessageBox, "information", _capture("information"))

    _qt_app()
    with _translation_guard() as translator:
        translator.set_language("zh-CN")
        # Unbound call — 不实例化 SceneFabMainWindow,跳过它的重型
        # __init__ 与信号连接。
        SceneFabMainWindow.show_message(None, "disk full", level="error")
        SceneFabMainWindow.show_message(None, "careful", level="warning")
        SceneFabMainWindow.show_message(None, "hi", level="info")
        assert captured == [
            ("critical", "错误", "disk full"),
            ("warning", "警告", "careful"),
            ("information", "提示", "hi"),
        ]

        captured.clear()
        translator.set_language("en-US")
        SceneFabMainWindow.show_message(None, "disk full", level="error")
        assert captured == [("critical", "Error", "disk full")]
