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

from ...i18n import t
from ...theme.ds_tokens import _C, FontSizes, FontWeights, Radii, ui_font
from ...theme.runtime import ThemeAwareMixin
from ..controls import ComboBox, ToggleSwitch
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
# i18n-key ↔ internal code so ``_on_language_changed`` can resolve the
# combo's currently displayed (translated) label back to a stable code
# after the user picks a different option.
_LANGUAGE_LABEL_TO_CODE_BY_KEY = {
    "settings.language.zh-CN": "zh-CN",
    "settings.language.en-US": "en-US",
}
# Reverse lookup: code → i18n key. Used by ``load_settings`` so a value
# stored in SettingsManager (independent of the UI language at the time)
# can be matched back to its translated label without string-matching.
_LANGUAGE_CODE_TO_KEY = {v: k for k,
                         v in _LANGUAGE_LABEL_TO_CODE_BY_KEY.items()}

# 编码选项标签 ↔ ProjectSettingsManager 编码器值
_CODEC_LABEL_TO_VALUE = {
    "MP4 / H.264": "h264",
    "MP4 / H.265": "h265",
    "MOV / ProRes": "prores",
}
_CODEC_VALUE_TO_LABEL = {v: k for k, v in _CODEC_LABEL_TO_VALUE.items()}
_CODEC_LABEL_TO_VALUE_BY_KEY = {
    "settings.codec.h264": "h264",
    "settings.codec.h265": "h265",
    "settings.codec.prores": "prores",
}
_CODEC_VALUE_TO_KEY = {v: k for k, v in _CODEC_LABEL_TO_VALUE_BY_KEY.items()}

# 主题标签 ↔ ThemeManager 模式
_THEME_LABEL_TO_MODE = {"跟随系统": "system", "浅色": "light", "深色": "dark"}
_THEME_MODE_TO_LABEL = {v: k for k, v in _THEME_LABEL_TO_MODE.items()}
_THEME_LABEL_TO_MODE_BY_KEY = {
    "settings.theme.system": "system",
    "settings.theme.light": "light",
    "settings.theme.dark": "dark",
}
_THEME_MODE_TO_KEY = {v: k for k, v in _THEME_LABEL_TO_MODE_BY_KEY.items()}

THEME_OPTIONS = tuple(_THEME_LABEL_TO_MODE)
THEME_MODES = tuple(_THEME_LABEL_TO_MODE.values())

# QSettings 组织/应用名 — 与 main_window / application 保持一致，
# 确保工作区路径等设置在所有页面间共享同一存储。
_QSETTINGS_ORG = "SceneFab"
_QSETTINGS_APP = "Application"


class SettingsPage(QFrame, ThemeAwareMixin):
    """Application settings page."""

    theme_changed = Signal(str)
    # Phase 3 · Help & Support group emits this when a row's button is
    # clicked. ``MainWindow`` subscribes and dispatches the actual work.
    help_action_requested = Signal(str)

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
        # i18n bookkeeping for retranslate().
        # ``_i18n_entries`` maps each row to (label_lbl, desc_lbl,
        # label_key, desc_key) so the retranslate pass can swap text
        # in place without rebuilding the QFrame tree.
        self._i18n_entries: list[tuple[QLabel, QLabel | None, str, str]] = []
        self._group_title_labels: list[tuple[QLabel, str]] = []
        self._header_title_lbl: QLabel | None = None
        self._header_subtitle_lbl: QLabel | None = None
        self._save_button: QPushButton | None = None
        # Combo boxes that need a re-paint of their items on language
        # change (theme + language + codec + canvas + fps + default_model).
        self._combo_keys: dict[QComboBox, list[str]] = {}

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

    def _on_theme_changed(self, label: str) -> None:
        """Apply the selected three-state theme and notify compatibility slots.

        Combo labels are translated, so the lookup walks the i18n catalog
        and compares translated labels against the *currently displayed*
        text. Falls back to the legacy literal mapping so callers passing
        plain strings still get the right mode.
        """
        mode = None
        for candidate in ("settings.theme.system",
                          "settings.theme.light",
                          "settings.theme.dark"):
            if t(candidate) == label:
                mode = _THEME_LABEL_TO_MODE_BY_KEY[candidate]
                break
        if mode is None:
            mode = _THEME_LABEL_TO_MODE.get(label)
        if mode is None:
            return
        if self._theme_manager is None:
            from ...theme.theme_manager import ThemeManager

            self._theme_manager = ThemeManager(self)
        self._theme_manager.set_mode(mode)
        self.theme_changed.emit(mode)

    def _on_language_changed(self, label: str) -> None:
        """Apply the selected UI language *immediately* and persist it.

        Mirrors :meth:`_on_theme_changed`: the combo fires the moment the
        user picks an option so the change is visible without waiting
        for :meth:`save_settings`. Persistence still happens in
        ``save_settings`` so the choice is restored on the next launch.
        """
        code = None
        for candidate in ("settings.language.zh-CN",
                          "settings.language.en-US"):
            if t(candidate) == label:
                code = _LANGUAGE_LABEL_TO_CODE_BY_KEY[candidate]
                break
        if code is None:
            code = _LANGUAGE_LABEL_TO_CODE.get(label)
        if code is None:
            return
        # Flip the global translator. ``SceneFabMainWindow`` listens to
        # ``Translator.language_changed`` and walks every chrome owner
        # + lazy-loaded page to invoke ``retranslate()``.
        from app.ui.i18n import set_language

        set_language(code)
        # Persist via the SettingsManager if we have one — mirrors the
        # legacy write in ``save_settings`` but happens up-front so a
        # crash between combo-change and Save doesn't lose the pick.
        if self._settings_manager is not None:
            try:
                self._settings_manager.set_setting("ui.language", code)
            except Exception:
                # Persistence is best-effort: a transient settings
                # failure must not break the live language switch.
                pass

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
        theme_mode = self._resolve_mode_for_combo("theme")
        if theme_mode:
            qsettings.setValue("appearance/theme_mode", theme_mode)

        if manager is not None:
            # 语言
            language_code = self._resolve_code_for_combo("language")
            if language_code:
                manager.set_setting("ui.language", language_code)

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
            self._save_validated_codec_combo(
                manager,
                qsettings,
                "codec",
                "video.codec",
                "export/codec",
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
        theme_mode = qsettings.value(
            "appearance/theme_mode", "system", type=str)
        theme_key = _THEME_MODE_TO_KEY.get(theme_mode, "settings.theme.system")
        self._set_combo_text("theme", t(theme_key))

        if manager is None:
            return

        # 语言
        language_code = manager.get_setting("ui.language")
        language_key = _LANGUAGE_CODE_TO_KEY.get(
            language_code, "settings.language.zh-CN")
        self._set_combo_text("language", t(language_key))

        # 默认模型
        self._set_combo_text(
            "default_model", manager.get_setting("ai.default_model"))

        # 帧率（30 → "30 fps"）
        fps_value = manager.get_setting("video.fps")
        if fps_value is not None:
            self._set_combo_text("fps", f"{fps_value} fps")

        # 画布与编码：优先使用 QSettings 回退值（保留竖屏等自定义项）
        self._load_validated_combo(
            manager, qsettings, "canvas", "video.resolution", "export/canvas"
        )
        self._load_validated_codec_combo(
            manager,
            qsettings,
            "codec",
            "video.codec",
            "export/codec",
        )

        # 自动保存 / 最小化到托盘
        auto_save = self._controls.get("auto_save")
        if isinstance(auto_save, ToggleSwitch):
            auto_save.setChecked(
                bool(manager.get_setting("auto_save.enabled", True)))
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

    def _save_validated_codec_combo(
        self,
        manager: Any,
        qsettings: QSettings,
        key: str,
        manager_key: str,
        fallback_qkey: str,
    ) -> None:
        """Same shape as ``_save_validated_combo`` but resolves the codec
        via i18n keys — the codec combo's options are translated, so the
        *displayed* label cannot be used as the stored value directly.
        """
        label = self._combo_text(key)
        if not label:
            return
        # Map the displayed (translated) label back to its internal code
        # by walking the i18n catalog.
        stored = None
        for candidate_key, candidate_value in _CODEC_LABEL_TO_VALUE_BY_KEY.items():
            if t(candidate_key) == label:
                stored = candidate_value
                break
        if stored is None:
            # Legacy / fallback path: match the literal label directly.
            stored = _CODEC_LABEL_TO_VALUE.get(label, label)
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

    def _load_validated_codec_combo(
        self,
        manager: Any,
        qsettings: QSettings,
        key: str,
        manager_key: str,
        fallback_qkey: str,
    ) -> None:
        """Codec counterpart of ``_load_validated_combo``: translates the
        stored codec value via i18n catalog so the combo reflects the
        active UI language.
        """
        fallback = qsettings.value(fallback_qkey, "", type=str)
        if fallback:
            self._set_combo_text(key, fallback)
            return
        stored = manager.get_setting(manager_key)
        if stored is None:
            return
        codec_key = _CODEC_VALUE_TO_KEY.get(str(stored))
        if codec_key is not None:
            self._set_combo_text(key, t(codec_key))
        else:
            self._set_combo_text(key, str(stored))

    # ── i18n helpers for combo ↔ internal code ────────────────────

    def _resolve_mode_for_combo(self, key: str) -> str | None:
        """Map a theme combo's currently displayed (translated) text
        back to the internal mode code stored in QSettings.

        Returns ``None`` when the displayed text doesn't match any
        known i18n key — the caller should treat this as a no-op so a
        transient or mis-built combo can't silently drop the user's
        pick on save.
        """
        label = self._combo_text(key)
        for candidate_key, candidate_mode in _THEME_LABEL_TO_MODE_BY_KEY.items():
            if t(candidate_key) == label:
                return candidate_mode
        # Fallback to legacy literal mapping so previously stored
        # values (e.g. "深色") still resolve.
        return _THEME_LABEL_TO_MODE.get(label)

    def _resolve_code_for_combo(self, key: str) -> str | None:
        """Map a language combo's currently displayed text back to the
        internal code (e.g. ``"zh-CN"``).
        """
        label = self._combo_text(key)
        for candidate_key, candidate_code in _LANGUAGE_LABEL_TO_CODE_BY_KEY.items():
            if t(candidate_key) == label:
                return candidate_code
        return _LANGUAGE_LABEL_TO_CODE.get(label)

    _API_KEY_MAP = {
        "qwen_api_key": "qwen",
        "deepseek_api_key": "deepseek",
        "openai_api_key": "openai",
        "kimi_api_key": "kimi",
        "glm_api_key": "glm5",
        "gemini_api_key": "gemini",
        "api_key": "default",
    }

    def _save_api_key(self):
        key_manager = self._secure_key_manager()
        if key_manager is None:
            return
        for control_key, provider in self._API_KEY_MAP.items():
            api_input = self._controls.get(control_key)
            if isinstance(api_input, QLineEdit):
                api_key = api_input.text().strip()
                if api_key:
                    try:
                        key_manager.store_api_key(provider, api_key)
                    except Exception:
                        pass

    def _load_api_key(self):
        key_manager = self._secure_key_manager()
        if key_manager is None:
            return
        for control_key, provider in self._API_KEY_MAP.items():
            api_input = self._controls.get(control_key)
            if isinstance(api_input, QLineEdit):
                try:
                    key_data = key_manager.get_api_key(provider)
                except Exception:
                    key_data = None
                if key_data and key_data.get("api_key"):
                    api_input.setText(str(key_data["api_key"]))

    def _secure_key_manager(self) -> Any:
        manager = self._settings_manager
        if manager is not None and hasattr(manager, "secure_key_manager"):
            return manager.secure_key_manager
        try:
            from app.core.security_keys import get_secure_key_manager

            return get_secure_key_manager()
        except Exception:
            return None

    @staticmethod
    def _api_provider() -> str:
        try:
            from app.config.config import config_manager

            return config_manager.config.default_llm
        except Exception:
            return "deepseek"

    def retranslate(self) -> None:
        """Refresh every visible string after a language flip.

        The page renders labels / descriptions / save button from i18n
        keys at construction time but Qt freezes the displayed glyphs.
        We re-resolve each cached key here so a ``set_language(...)``
        call mid-session is reflected without rebuilding the page.

        Combos whose option list is made of i18n keys (theme, codec,
        canvas, fps) are also re-painted — the *current* selection is
        preserved so the user's pick survives the language switch.
        """
        if self._header_title_lbl is not None:
            self._header_title_lbl.setText(t("settings.header.title"))
        if self._header_subtitle_lbl is not None:
            self._header_subtitle_lbl.setText(t("settings.header.subtitle"))
        if self._save_button is not None:
            self._save_button.setText(t("settings.save_button"))
        for label, key in self._group_title_labels:
            label.setText(t(key))
        for label_lbl, desc_lbl, label_key, desc_key in self._i18n_entries:
            if label_key:
                label_lbl.setText(t(label_key))
            if desc_lbl is not None and desc_key:
                desc_lbl.setText(t(desc_key))
        # Combos: repaint each item whose option was an i18n key. We
        # keep the user's current selection (item index) so picking
        # English still leaves the right mode in place.
        for combo, keys in self._combo_keys.items():
            current = combo.currentIndex()
            for index, key in enumerate(keys):
                if index < combo.count():
                    combo.setItemText(index, t(key))
            if 0 <= current < combo.count():
                combo.setCurrentIndex(current)

    def _show_status(self, message: str):
        if self._status_label is not None:
            self._status_label.setText(message)

    def _build_header(self) -> QFrame:
        header = header_panel(
            "settings_header",
            t("settings.header.title"),
            t("settings.header.subtitle"),
        )
        labels = header.findChildren(QLabel)
        if labels:
            self._header_title_lbl = labels[0]
            if len(labels) > 1:
                self._header_subtitle_lbl = labels[1]
        return header

    def _build_footer(self) -> QFrame:
        footer = panel("settings_footer")
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(20, 14, 20, 14)

        self._status_label = QLabel("")
        self._status_label.setFont(ui_font(FontSizes.xs))
        self._status_label.setStyleSheet(f"color: {_C.SUCCESS};")
        layout.addWidget(self._status_label, 1)

        self._save_button = QPushButton(t("settings.save_button"))
        self._save_button.setObjectName("settings_save_button")
        self._save_button.setFixedHeight(36)
        self._save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_button.setStyleSheet(action_button_style(primary=True))
        self._save_button.clicked.connect(self.save_settings)
        layout.addWidget(self._save_button)
        return footer

    def _settings_group(
        self, title_or_key: str, rows: tuple[SettingRowView, ...]
    ) -> QFrame:
        group = self._group(title_or_key)
        layout = group.layout()
        assert layout is not None
        for row in rows:
            layout.addWidget(
                self._row(
                    t(row.label_key) if row.label_key else row.label,
                    self._control_for_row(row),
                    t(row.description_key) if row.description_key else row.description,
                    label_key=row.label_key,
                    desc_key=row.description_key,
                )
            )
        return group

    def _control_for_row(self, row: SettingRowView) -> QWidget:
        if row.control == "path":
            wrapper, edit, button = self._path_input(row.value)
            self._path_edits[row.key] = edit
            button.clicked.connect(lambda checked=False,
                                   e=edit: self._choose_directory(e))
            self._controls[row.key] = wrapper
            return wrapper
        if row.control == "combo":
            combo = self._combo(
                row.options,
                option_keys=row.options_keys,
            )
            if row.key == "theme":
                self._theme_combo = combo
                combo.currentTextChanged.connect(self._on_theme_changed)
            elif row.key == "language":
                # Mirror the theme combo: instant switch on pick instead
                # of waiting for Save. ``currentTextChanged`` fires after
                # the user actually changes the selection, so this never
                # triggers during the initial ``load_settings`` read.
                combo.currentTextChanged.connect(self._on_language_changed)
            self._controls[row.key] = combo
            # The combo's options may themselves be i18n keys — store
            # them so ``retranslate`` can re-render the visible items.
            if row.options_keys:
                self._combo_keys[combo] = list(row.options_keys)
            else:
                keys: list[str] = []
                for option in row.options:
                    if option.startswith("settings.") or option.startswith(
                        ("common.", "nav.", "menu.", "topbar.")
                    ):
                        keys.append(option)
                if keys:
                    self._combo_keys[combo] = keys
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
        # Phase 3 · Help system: rows that surface as a single button.
        # The page exposes ``help_action_requested(key)`` and the
        # ``MainWindow`` listens to dispatch the actual work (show dock,
        # reset onboarding flag, copy diagnostics, etc.).
        if row.control == "button":
            button_text = (
                t(row.button_label_key) if row.button_label_key else row.label
            )
            button = QPushButton(button_text)
            button.setObjectName(f"settings_help_btn_{row.key}")
            button.clicked.connect(
                lambda checked=False, k=row.key: self.help_action_requested.emit(
                    k)
            )
            self._controls[row.key] = button
            # Keep the label translation fresh on retranslate.
            if row.button_label_key:
                self._i18n_entries.append(
                    (button, None, row.button_label_key, "")
                )
            return button
        # Fallback: legacy callers may have used "label" as a sentinel
        # for a plain text field. We render a QLabel so the row stays
        # visually consistent.
        if row.control == "label":
            label = QLabel(row.value or row.label)
            label.setStyleSheet(f"color: {_C.TEXT_SECONDARY};")
            return label
        raise ValueError(f"Unsupported settings control: {row.control}")

    def _group(self, title_or_key: str) -> QFrame:
        group = panel(f"settings_{title_or_key}")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)
        # The header is the i18n key when it starts with ``settings.``,
        # otherwise a literal fallback (legacy callers). Either way the
        # resulting label is cached so retranslate can refresh it.
        is_key = title_or_key.startswith("settings.")
        label = section_title(t(title_or_key) if is_key else title_or_key)
        layout.addWidget(label)
        if is_key:
            self._group_title_labels.append((label, title_or_key))
        return group

    def _row(
        self,
        label: str,
        widget: QWidget,
        desc: str = "",
        *,
        label_key: str = "",
        desc_key: str = "",
    ) -> QFrame:
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
        else:
            desc_label = None
        layout.addLayout(text, 1)
        layout.addWidget(widget)
        if label_key or desc_key:
            self._i18n_entries.append((title, desc_label, label_key, desc_key))
        return row

    def _combo(
        self,
        items: tuple[str, ...],
        *,
        option_keys: tuple[str, ...] = (),
    ) -> QComboBox:
        combo = ComboBox()
        # When ``option_keys`` is provided, treat each entry in ``items``
        # as an i18n key and translate to the active catalog. Otherwise
        # ``items`` are taken verbatim so legacy callers still work.
        if option_keys:
            for key in option_keys:
                combo.addItem(t(key))
        else:
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

        button = QPushButton(t("settings.choose_directory"))
        button.setFixedHeight(32)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setStyleSheet(action_button_style(padding=12))
        layout.addWidget(button)
        return wrapper, edit, button

    def _choose_directory(self, edit: QLineEdit):
        """打开目录选择对话框并回填路径输入框"""
        directory = QFileDialog.getExistingDirectory(
            self, t("settings.choose_directory"), edit.text())
        if directory:
            edit.setText(directory)

    def _input_style(self) -> str:
        return f"""
            QComboBox, QLineEdit {{
                background: {_C.BG_ELEVATED};
                border: 1px solid {_C.BORDER_DEFAULT};
                border-radius: {Radii.sm};
                color: {_C.TEXT_PRIMARY};
                font-size: {FontSizes.xs}px;
            }}
            QLineEdit {{
                padding: 6px 10px;
            }}
            QComboBox {{
                padding: 6px 32px 6px 10px;
            }}
            QComboBox::down-arrow {{
                image: none;
            }}
            QComboBox:focus, QLineEdit:focus {{
                border-color: {_C.PRIMARY};
            }}
        """
