#!/usr/bin/env python3
"""Application settings page."""

from typing import Any

from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...theme.ds_tokens import _C, FontSizes, FontWeights, Radii, ui_font
from ...theme.runtime import ThemeAwareMixin
from ..controls import ToggleSwitch
from .page_view_models import SETTINGS_GROUPS, SettingRowView
from .page_widgets import (
    action_button_style,
    header_panel,
    page_background_style,
    page_container,
    panel,
    scroll_area,
    section_title,
)

# 界面语言标签 ↔ ProjectSettingsManager 语言代码
_LANGUAGE_LABEL_TO_CODE = {"简体中文": "zh-CN", "English": "en-US"}
_LANGUAGE_CODE_TO_LABEL = {v: k for k, v in _LANGUAGE_LABEL_TO_CODE.items()}

# 编码选项标签 ↔ ProjectSettingsManager 编码器值
_CODEC_LABEL_TO_VALUE = {
    "MP4 / H.264": "h264",
    "MP4 / H.265": "h265",
    "MOV / ProRes": "prores",
}
_CODEC_VALUE_TO_LABEL = {v: k for k, v in _CODEC_LABEL_TO_VALUE.items()}

# 主题标签 ↔ ThemeManager 模式
_THEME_LABEL_TO_MODE = {"浅色": "light", "深色": "dark"}
_THEME_MODE_TO_LABEL = {v: k for k, v in _THEME_LABEL_TO_MODE.items()}

THEME_OPTIONS = ("浅色", "深色")
THEME_MODES = ("light", "dark")

# QSettings 组织/应用名 — 与 main_window / application 保持一致，
# 确保工作区路径等设置在所有页面间共享同一存储。
_QSETTINGS_ORG = "SceneFab"
_QSETTINGS_APP = "Application"


class SettingsPage(QFrame, ThemeAwareMixin):
    """Application settings page."""

    theme_changed = Signal(str)

    def __init__(
        self,
        settings_manager: Any = None,
        parent=None,
        *,
        theme_manager: Any = None,
        project_manager: Any = None,
    ):
        super().__init__(parent)
        self.setObjectName("settings_page")
        self._settings_manager = settings_manager
        self._theme_manager = theme_manager
        self._project_manager = project_manager
        self._tray_toggle: ToggleSwitch | None = None
        self._controls: dict[str, QWidget] = {}
        self._path_edits: dict[str, QLineEdit] = {}
        self._status_label: QLabel | None = None
        self._theme_combo: QComboBox | None = None

        ThemeAwareMixin.__init__(self)
        self._setup_style()
        self._setup_ui()
        self._connect_tray_signal()
        self._connect_auto_save_signal()
        self.load_settings()

    def _setup_style(self):
        self.setStyleSheet(page_background_style("settings_page"))

    def _build_stylesheet(self) -> str:
        return page_background_style("settings_page")

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = scroll_area()
        container = page_container()
        layout = container.layout()
        assert layout is not None  # for type checker

        layout.addWidget(self._build_header())
        for title, rows in SETTINGS_GROUPS:
            layout.addWidget(self._settings_group(title, rows))
        layout.addWidget(self._build_footer())
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

    def _connect_auto_save_signal(self):
        auto_save = self._controls.get("auto_save")
        if isinstance(auto_save, ToggleSwitch):
            auto_save.toggled.connect(self._on_auto_save_toggled)

    def _on_auto_save_toggled(self, checked: bool):
        pm = self._project_manager
        if pm is not None and hasattr(pm, "auto_save_timer"):
            if checked:
                pm.auto_save_timer.start(60000)
            else:
                pm.auto_save_timer.stop()

    def _on_theme_changed(self, label: str):
        mode = _THEME_LABEL_TO_MODE.get(label)
        if mode is None:
            return
        if self._theme_manager is None:
            from ...theme.theme_manager import ThemeManager

            self._theme_manager = ThemeManager()
        self._theme_manager.set_theme_mode(mode)

    # ══════════════════════════════════════════════════════════════
    # 设置持久化
    # ══════════════════════════════════════════════════════════════

    def save_settings(self) -> bool:
        """读取所有控件值并写入 SettingsManager / QSettings。"""
        qsettings = QSettings(_QSETTINGS_ORG, _QSETTINGS_APP)
        manager = self._settings_manager

        # 工作区路径（SettingsManager 未定义，使用 QSettings 持久化）
        for key, qkey in (
            ("project_dir", "workspace/project_dir"),
            ("export_dir", "workspace/export_dir"),
        ):
            edit = self._path_edits.get(key)
            if edit is not None:
                qsettings.setValue(qkey, edit.text().strip())

        # API Key（通过 SettingsManager 的安全密钥存储）
        self._save_api_key()

        # 主题
        theme_label = self._combo_text("theme")
        theme_mode = _THEME_LABEL_TO_MODE.get(theme_label)
        if theme_mode:
            qsettings.setValue("appearance/theme_mode", theme_mode)

        if manager is not None:
            # 语言
            language_label = self._combo_text("language")
            if language_label:
                manager.set_setting(
                    "ui.language",
                    _LANGUAGE_LABEL_TO_CODE.get(language_label, language_label),
                )

            # 默认模型
            model = self._combo_text("default_model")
            if model:
                manager.set_setting("ai.default_model", model)

            # 帧率（"30 fps" → 30）
            fps_text = self._combo_text("fps")
            fps_value = self._parse_fps(fps_text)
            if fps_value is not None:
                manager.set_setting("video.fps", fps_value)

            # 自动保存 / 最小化到托盘
            auto_save = self._controls.get("auto_save")
            if isinstance(auto_save, ToggleSwitch):
                manager.set_setting("auto_save.enabled", auto_save.isChecked())
            if self._tray_toggle is not None:
                manager.set_setting(
                    "ui.minimize_to_tray", self._tray_toggle.isChecked()
                )

            # 画布与编码：SettingsManager 校验未通过时退回 QSettings
            self._save_validated_combo(
                manager, qsettings, "canvas", "video.resolution", "export/canvas"
            )
            self._save_validated_combo(
                manager,
                qsettings,
                "codec",
                "video.codec",
                "export/codec",
                _CODEC_LABEL_TO_VALUE,
            )

        self._show_status("已保存")
        return True

    def load_settings(self):
        """从 SettingsManager / QSettings 读取值并填充控件。"""
        qsettings = QSettings(_QSETTINGS_ORG, _QSETTINGS_APP)
        manager = self._settings_manager

        # 工作区路径
        for key, qkey in (
            ("project_dir", "workspace/project_dir"),
            ("export_dir", "workspace/export_dir"),
        ):
            edit = self._path_edits.get(key)
            value = qsettings.value(qkey, "", type=str)
            if edit is not None and value:
                edit.setText(value)

        # API Key
        self._load_api_key()

        # 主题
        theme_mode = qsettings.value("appearance/theme_mode", "light", type=str)
        theme_label = _THEME_MODE_TO_LABEL.get(theme_mode, "浅色")
        self._set_combo_text("theme", theme_label)

        if manager is None:
            return

        # 语言
        language_code = manager.get_setting("ui.language")
        language_label = _LANGUAGE_CODE_TO_LABEL.get(language_code, language_code)
        self._set_combo_text("language", language_label)

        # 默认模型
        self._set_combo_text("default_model", manager.get_setting("ai.default_model"))

        # 帧率（30 → "30 fps"）
        fps_value = manager.get_setting("video.fps")
        if fps_value is not None:
            self._set_combo_text("fps", f"{fps_value} fps")

        # 画布与编码：优先使用 QSettings 回退值（保留竖屏等自定义项）
        self._load_validated_combo(
            manager, qsettings, "canvas", "video.resolution", "export/canvas"
        )
        self._load_validated_combo(
            manager,
            qsettings,
            "codec",
            "video.codec",
            "export/codec",
            _CODEC_VALUE_TO_LABEL,
        )

        # 自动保存 / 最小化到托盘
        auto_save = self._controls.get("auto_save")
        if isinstance(auto_save, ToggleSwitch):
            auto_save.setChecked(bool(manager.get_setting("auto_save.enabled", True)))
        if self._tray_toggle is not None:
            checked = bool(manager.get_setting("ui.minimize_to_tray", False))
            self._tray_toggle.setChecked(checked)
            self._on_tray_toggled(checked)

    # ── 持久化辅助方法 ────────────────────────────────────────────

    def _combo_text(self, key: str) -> str:
        widget = self._controls.get(key)
        if isinstance(widget, QComboBox):
            return widget.currentText()
        return ""

    def _set_combo_text(self, key: str, value: Any):
        widget = self._controls.get(key)
        if isinstance(widget, QComboBox) and value in self._combo_items(widget):
            widget.setCurrentText(str(value))

    @staticmethod
    def _combo_items(combo: QComboBox) -> list[str]:
        return [combo.itemText(i) for i in range(combo.count())]

    @staticmethod
    def _parse_fps(text: str) -> int | None:
        try:
            return int(text.split()[0])
        except (ValueError, IndexError, AttributeError):
            return None

    def _save_validated_combo(
        self,
        manager: Any,
        qsettings: QSettings,
        key: str,
        manager_key: str,
        fallback_qkey: str,
        label_map: dict[str, str] | None = None,
    ):
        label = self._combo_text(key)
        if not label:
            return
        stored = (label_map or {}).get(label, label)
        if manager.set_setting(manager_key, stored):
            qsettings.remove(fallback_qkey)
        else:
            qsettings.setValue(fallback_qkey, label)

    def _load_validated_combo(
        self,
        manager: Any,
        qsettings: QSettings,
        key: str,
        manager_key: str,
        fallback_qkey: str,
        value_map: dict[str, str] | None = None,
    ):
        fallback = qsettings.value(fallback_qkey, "", type=str)
        if fallback:
            self._set_combo_text(key, fallback)
            return
        stored = manager.get_setting(manager_key)
        if stored is None:
            return
        label = (value_map or {}).get(str(stored), str(stored))
        self._set_combo_text(key, label)

    def _save_api_key(self):
        api_input = self._controls.get("api_key")
        if not isinstance(api_input, QLineEdit):
            return
        api_key = api_input.text().strip()
        if not api_key:
            return
        key_manager = self._secure_key_manager()
        if key_manager is None:
            return
        try:
            key_manager.store_api_key(self._api_provider(), api_key)
        except Exception:
            pass

    def _load_api_key(self):
        api_input = self._controls.get("api_key")
        if not isinstance(api_input, QLineEdit):
            return
        key_manager = self._secure_key_manager()
        if key_manager is None:
            return
        try:
            key_data = key_manager.get_api_key(self._api_provider())
        except Exception:
            key_data = None
        if key_data and key_data.get("api_key"):
            api_input.setText(str(key_data["api_key"]))

    def _secure_key_manager(self) -> Any:
        manager = self._settings_manager
        if manager is not None and hasattr(manager, "secure_key_manager"):
            return manager.secure_key_manager
        try:
            from scenefab.secure_key_manager import get_secure_key_manager

            return get_secure_key_manager()
        except Exception:
            return None

    @staticmethod
    def _api_provider() -> str:
        try:
            from scenefab.settings.config import config_manager

            return config_manager.config.default_llm
        except Exception:
            return "deepseek"

    def _show_status(self, message: str):
        if self._status_label is not None:
            self._status_label.setText(message)

    def _build_header(self) -> QFrame:
        return header_panel(
            "settings_header", "系统设置", "配置默认工作区、AI 服务和导出参数"
        )

    def _build_footer(self) -> QFrame:
        footer = panel("settings_footer")
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(20, 14, 20, 14)

        self._status_label = QLabel("")
        self._status_label.setFont(ui_font(FontSizes.xs))
        self._status_label.setStyleSheet(f"color: {_C.SUCCESS};")
        layout.addWidget(self._status_label, 1)

        save_button = QPushButton("保存设置")
        save_button.setObjectName("settings_save_button")
        save_button.setFixedHeight(36)
        save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        save_button.setStyleSheet(action_button_style(primary=True))
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)
        return footer

    def _settings_group(self, title: str, rows: tuple[SettingRowView, ...]) -> QFrame:
        group = self._group(title)
        layout = group.layout()
        assert layout is not None
        for row in rows:
            layout.addWidget(
                self._row(row.label, self._control_for_row(row), row.description)
            )
        return group

    def _control_for_row(self, row: SettingRowView) -> QWidget:
        if row.control == "path":
            wrapper, edit, button = self._path_input(row.value)
            self._path_edits[row.key] = edit
            button.clicked.connect(lambda checked=False, e=edit: self._choose_directory(e))
            self._controls[row.key] = wrapper
            return wrapper
        if row.control == "combo":
            combo = self._combo(row.options)
            if row.key == "theme":
                combo.currentTextChanged.connect(self._on_theme_changed)
            self._controls[row.key] = combo
            return combo
        if row.control == "password":
            password = self._password_input(row.placeholder)
            self._controls[row.key] = password
            return password
        if row.control == "toggle":
            toggle = ToggleSwitch(row.checked)
            if row.key == "minimize_to_tray":
                self._tray_toggle = toggle
            self._controls[row.key] = toggle
            return toggle
        raise ValueError(f"Unsupported settings control: {row.control}")

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
        title.setFont(ui_font(FontSizes.sm, FontWeights.Medium))
        title.setStyleSheet(f"color: {_C.TEXT_PRIMARY};")
        text.addWidget(title)
        if desc:
            desc_label = QLabel(desc)
            desc_label.setFont(ui_font(FontSizes.xs))
            desc_label.setStyleSheet(f"color: {_C.TEXT_MUTED};")
            text.addWidget(desc_label)
        layout.addLayout(text, 1)
        layout.addWidget(widget)
        return row

    def _combo(self, items: tuple[str, ...]) -> QComboBox:
        combo = QComboBox()
        combo.addItems(items)
        combo.setFixedWidth(180)
        combo.setStyleSheet(self._input_style())
        return combo

    def _password_input(self, placeholder: str) -> QLineEdit:
        api_input = QLineEdit()
        api_input.setEchoMode(QLineEdit.EchoMode.Password)
        api_input.setPlaceholderText(placeholder)
        api_input.setFixedWidth(280)
        api_input.setStyleSheet(self._input_style())
        return api_input

    def _path_input(self, value: str) -> tuple[QFrame, QLineEdit, QPushButton]:
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
        return wrapper, edit, button

    def _choose_directory(self, edit: QLineEdit):
        """打开目录选择对话框并回填路径输入框"""
        directory = QFileDialog.getExistingDirectory(self, "选择目录", edit.text())
        if directory:
            edit.setText(directory)

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
