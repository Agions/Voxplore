#!/usr/bin/env python3
"""Application settings page."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...theme.ds_tokens import _C, FontSizes, Radii, get_theme_mode
from ...theme.runtime import ThemeAwareMixin
from ..controls import ToggleSwitch
from .page_widgets import (
    action_button_style,
    header_panel,
    page_background_style,
    page_container,
    panel,
    scroll_area,
    section_title,
)

# Theme mode options presented in the appearance combo box.
THEME_OPTIONS = ("浅色", "深色")  # display labels
THEME_MODES = ("light", "dark")  # values emitted on theme_changed


class SettingsPage(QFrame, ThemeAwareMixin):
    """Professional settings surface.

    Hosts the theme switcher in :meth:`_appearance_group`. Picking a
    new option emits :attr:`theme_changed`; :class:`SceneFabMainWindow`
    listens and applies the new palette via :func:`restyle_app` plus
    each :class:`ThemeAwareMixin.apply_theme`.
    """

    theme_changed = Signal(str)  # "light" / "dark"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("settings_page")
        self._tray_toggle: ToggleSwitch | None = None
        self._theme_combo: QComboBox | None = None
        # Apply stylesheet once ThemeAwareMixin is in the MRO. The mixin
        # has no ``__init__`` — declaring it on the class is enough.
        ThemeAwareMixin.__init__(self)
        self.setStyleSheet(self._build_stylesheet())
        self._setup_ui()
        self._connect_tray_signal()
        self._connect_theme_signal()

    def _setup_style(self):
        # Kept for backwards-compat: ThemeAwareMixin.__init__ now calls
        # build_stylesheet directly. Re-applied here so subclasses that
        # override ``_setup_style`` keep working.
        self.setStyleSheet(page_background_style("settings_page"))

    def _build_stylesheet(self) -> str:
        """Return the page-level stylesheet using the **current** ``_C``.

        Used by :class:`ThemeAwareMixin.apply_theme` to refresh colours
        after :func:`set_theme_mode`.
        """
        return page_background_style("settings_page")

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = scroll_area()
        container = page_container()
        layout = container.layout()

        layout.addWidget(self._build_header())
        layout.addWidget(self._workspace_group())
        layout.addWidget(self._appearance_group())
        layout.addWidget(self._ai_group())
        layout.addWidget(self._export_group())
        layout.addWidget(self._behavior_group())
        layout.addStretch()

        scroll.setWidget(container)
        root.addWidget(scroll)

    def _connect_tray_signal(self):
        if self._tray_toggle is not None:
            self._tray_toggle.toggled.connect(self._on_tray_toggled)

    def _connect_theme_signal(self):
        if self._theme_combo is not None:
            self._theme_combo.currentIndexChanged.connect(self._on_theme_changed)

    def _on_theme_changed(self, index: int) -> None:
        if 0 <= index < len(THEME_MODES):
            mode = THEME_MODES[index]
            self.theme_changed.emit(mode)

    def set_theme_mode_index(self, mode: str) -> None:
        """Programmatically select a theme option without firing the signal.

        Used by :class:`SceneFabMainWindow` when restoring the user's
        persisted preference on startup. Falls back silently when the
        combo has not been built yet (headless test path).
        """
        if self._theme_combo is None or mode not in THEME_MODES:
            return
        target = THEME_MODES.index(mode)
        self._theme_combo.blockSignals(True)
        self._theme_combo.setCurrentIndex(target)
        self._theme_combo.blockSignals(False)

    def _on_tray_toggled(self, checked: bool):
        window = self.window()
        if window is not None and hasattr(window, "set_minimize_to_tray"):
            window.set_minimize_to_tray(checked)

    def _build_header(self) -> QFrame:
        return header_panel("settings_header", "系统设置", "配置默认工作区、AI 服务和导出参数")

    def _workspace_group(self) -> QFrame:
        group = self._group("工作区")
        layout = group.layout()
        layout.addWidget(
            self._row("项目目录", self._path_input("~/SceneFab/projects"), "默认项目保存位置")
        )
        layout.addWidget(
            self._row("输出目录", self._path_input("~/SceneFab/exports"), "成片和草稿导出位置")
        )
        layout.addWidget(self._row("界面语言", self._combo(["简体中文", "English"])))
        return group

    def _appearance_group(self) -> QFrame:
        """Theme selector — emits ``theme_changed`` on pick.

        The combo is captured on the instance so that
        :meth:`set_theme_mode_index` can sync it to the persisted
        preference without bouncing the signal back.
        """
        group = self._group("外观")
        layout = group.layout()
        theme_combo = self._combo(list(THEME_OPTIONS))
        # Default to the active theme (light on startup).
        theme_combo.setCurrentIndex(THEME_MODES.index(get_theme_mode()))
        self._theme_combo = theme_combo
        layout.addWidget(
            self._row(
                "界面主题",
                theme_combo,
                "切换后立即生效",
            )
        )
        return group

    def _ai_group(self) -> QFrame:
        group = self._group("AI 服务")
        layout = group.layout()
        api_input = QLineEdit()
        api_input.setEchoMode(QLineEdit.EchoMode.Password)
        api_input.setPlaceholderText("输入 API Key")
        api_input.setFixedWidth(280)
        api_input.setStyleSheet(self._input_style())
        layout.addWidget(self._row("API Key", api_input, "用于脚本生成和画面理解"))
        layout.addWidget(
            self._row(
                "默认模型",
                self._combo(["deepseek-v4-pro", "gpt-5", "gemini-3.1-pro", "qwen3.7-max", "claude-sonnet-4-6"]),
                "影响脚本质量和响应速度",
            )
        )
        return group

    def _export_group(self) -> QFrame:
        group = self._group("导出默认值")
        layout = group.layout()
        layout.addWidget(
            self._row(
                "画布",
                self._combo(["1080x1920", "720x1280", "1920x1080"]),
                "短视频默认使用竖屏 9:16",
            )
        )
        layout.addWidget(self._row("帧率", self._combo(["30 fps", "60 fps", "24 fps"])))
        layout.addWidget(
            self._row(
                "编码",
                self._combo(["MP4 / H.264", "MP4 / H.265", "MOV / ProRes"]),
            )
        )
        return group

    def _behavior_group(self) -> QFrame:
        group = self._group("应用行为")
        layout = group.layout()
        layout.addWidget(self._row("自动保存", ToggleSwitch(True), "每 5 分钟保存项目状态"))
        self._tray_toggle = ToggleSwitch(False)
        layout.addWidget(
            self._row("关闭到系统托盘", self._tray_toggle, "关闭窗口时保持后台运行")
        )
        return group

    def _group(self, title: str) -> QFrame:
        group = panel(f"settings_{title}")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)
        layout.addWidget(section_title(title))
        return group

    def _row(self, label: str, widget: QWidget, desc: str = "") -> QFrame:
        row = QFrame()
        row.setObjectName("settings_row")
        row.setStyleSheet(f"""
            QFrame#settings_row {{
                background: {_C.BG_BASE};
                border: 1px solid {_C.BORDER_SUBTLE};
                border-radius: {Radii.sm};
            }}
        """)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(16)

        text = QVBoxLayout()
        text.setSpacing(2)
        title = QLabel(label)
        title.setFont(QFont("", FontSizes.sm, QFont.Weight.Medium))
        title.setStyleSheet(f"color: {_C.TEXT_PRIMARY};")
        text.addWidget(title)
        if desc:
            desc_label = QLabel(desc)
            desc_label.setFont(QFont("", FontSizes.xs))
            desc_label.setStyleSheet(f"color: {_C.TEXT_MUTED};")
            text.addWidget(desc_label)
        layout.addLayout(text, 1)
        layout.addWidget(widget)
        return row

    def _combo(self, items: list[str]) -> QComboBox:
        combo = QComboBox()
        combo.addItems(items)
        combo.setFixedWidth(180)
        combo.setStyleSheet(self._input_style())
        return combo

    def _path_input(self, value: str) -> QWidget:
        wrapper = QFrame()
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        edit = QLineEdit(value)
        edit.setFixedWidth(280)
        edit.setStyleSheet(self._input_style())
        layout.addWidget(edit)

        button = QPushButton("选择")
        button.setFixedHeight(32)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setStyleSheet(action_button_style(padding=12))
        layout.addWidget(button)
        return wrapper

    def _input_style(self) -> str:
        return f"""
            QComboBox, QLineEdit {{
                background: {_C.BG_ELEVATED};
                border: 1px solid {_C.BORDER_DEFAULT};
                border-radius: {Radii.sm};
                padding: 6px 10px;
                color: {_C.TEXT_PRIMARY};
                font-size: {FontSizes.xs}px;
            }}
            QComboBox:focus, QLineEdit:focus {{
                border-color: {_C.PRIMARY};
            }}
        """
