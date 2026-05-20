#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Voxplore 设置页 — 分类清晰的信息架构
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QScrollArea, QComboBox,
    QCheckBox, QLineEdit, QSpinBox, QGroupBox, QTabWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from app.ui.theme.ds_tokens import Colors, FontSizes, FontWeights, Spacing, Radii


# ═══════════════════════════════════════════════════════════════
# 设置分组卡片
# ═══════════════════════════════════════════════════════════════

class SettingsGroup(QFrame):
    """设置分组"""

    def __init__(self, title: str, icon: str = "", parent=None):
        super().__init__(parent)
        self._title = title
        self.setObjectName("settings_group")
        self._setup_style()
        self._setup_ui(icon)

    def _setup_style(self):
        self.setStyleSheet(f"""
            #settings_group {{
                background: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BORDER_SUBTLE};
                border-radius: {Radii.lg};
            }}
        """)

    def _setup_ui(self, icon: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 分组标题
        header = QFrame()
        header.setStyleSheet(f"border-bottom: 1px solid {Colors.BORDER_SUBTLE};")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 16)
        header_layout.setSpacing(12)

        if icon:
            icon_label = QLabel(icon)
            icon_label.setFont(QFont("", 18))
            header_layout.addWidget(icon_label)

        title_label = QLabel(self._title)
        title_label.setFont(QFont("", FontSizes.md, QFont.Weight.Semibold))
        title_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        layout.addWidget(header)

        # 内容区
        self._content = QFrame()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(20, 16, 20, 16)
        self._content_layout.setSpacing(16)
        self._content_layout.addWidget(QWidget())  # spacer
        layout.addWidget(self._content)

    def layout(self):
        return self._content_layout


# ═══════════════════════════════════════════════════════════════
# 设置项行
# ═══════════════════════════════════════════════════════════════

class SettingsRow(QFrame):
    """设置项行"""

    def __init__(self, label: str, widget: QWidget, desc: str = "", parent=None):
        super().__init__(parent)
        self.setFixedHeight(52 if desc else 40)
        self.setObjectName("settings_row")
        self._setup_style()
        self._setup_ui(label, widget, desc)

    def _setup_style(self):
        self.setStyleSheet(f"""
            #settings_row:hover {{
                background: {Colors.BG_ELEVATED};
            }}
        """)

    def _setup_ui(self, label: str, widget: QWidget, desc: str):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(16)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)

        label_widget = QLabel(label)
        label_widget.setFont(QFont("", FontSizes.sm))
        label_widget.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        text_layout.addWidget(label_widget)

        if desc:
            desc_label = QLabel(desc)
            desc_label.setFont(QFont("", FontSizes.xs))
            desc_label.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
            text_layout.addWidget(desc_label)

        layout.addLayout(text_layout, 1)
        layout.addWidget(widget)


class ToggleSwitch(QFrame):
    """开关控件"""

    toggled = Signal(bool)

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(44, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_style()

    def _setup_style(self):
        self.setStyleSheet(f"""
            QFrame {{
                background: {Colors.BG_ELEVATED};
                border-radius: 12px;
                border: none;
            }}
            QFrame[checked="true"] {{
                background: {Colors.PRIMARY_500};
            }}
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._checked = not self._checked
            self.setProperty("checked", self._checked)
            self.style().unpolish(self)
            self.style().polish(self)
            self.toggled.emit(self._checked)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool):
        if self._checked != checked:
            self._checked = checked
            self.setProperty("checked", checked)
            self.style().unpolish(self)
            self.style().polish(self)


# ═══════════════════════════════════════════════════════════════
# 设置页面
# ═══════════════════════════════════════════════════════════════

class SettingsPage(QFrame):
    """设置页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("settings_page")
        self._setup_style()
        self._setup_ui()

    def _setup_style(self):
        self.setStyleSheet(f"""
            #settings_page {{
                background: {Colors.BG_BASE};
            }}
        """)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(32, 24, 32, 32)
        container_layout.setSpacing(24)

        # 标题
        title = QLabel("设置")
        title.setFont(QFont("", FontSizes.xxl, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        container_layout.addWidget(title)

        # ── 通用设置 ──────────────────────────────
        general = SettingsGroup("通用", "⚙")
        gen_layout = general.layout()

        # 主题
        theme_row = SettingsRow("主题", QComboBox(), "选择界面外观")
        theme_combo = theme_row.layout().itemAt(1).widget()
        theme_combo.addItems(["深色", "浅色", "跟随系统"])
        theme_combo.setFixedWidth(160)
        theme_combo.setStyleSheet(f"""
            QComboBox {{
                background: {Colors.BG_ELEVATED};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Radii.sm};
                padding: 6px 12px;
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        gen_layout.insertWidget(0, theme_row)

        # 自动保存
        autosave_row = SettingsRow("自动保存", ToggleSwitch(True), "每隔 5 分钟自动保存项目")
        gen_layout.insertWidget(1, autosave_row)

        # 语言
        lang_row = SettingsRow("语言", QComboBox(), "界面显示语言")
        lang_combo = lang_row.layout().itemAt(1).widget()
        lang_combo.addItems(["简体中文", "English"])
        lang_combo.setFixedWidth(160)
        lang_combo.setStyleSheet(theme_combo.styleSheet())
        gen_layout.insertWidget(2, lang_row)

        container_layout.addWidget(general)

        # ── AI 服务设置 ───────────────────────────
        ai = SettingsGroup("AI 服务", "🤖")
        ai_layout = ai.layout()

        # API 密钥
        api_row = SettingsRow("API 密钥", QLineEdit("••••••••••••"), "用于 AI 服务认证")
        api_input = api_row.layout().itemAt(1).widget()
        api_input.setFixedWidth(280)
        api_input.setStyleSheet(f"""
            QLineEdit {{
                background: {Colors.BG_ELEVATED};
                border: 1px solid {Colors.BORDER_DEFAULT};
                border-radius: {Radii.sm};
                padding: 6px 12px;
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        ai_layout.insertWidget(0, api_row)

        # 模型选择
        model_row = SettingsRow("AI 模型", QComboBox(), "选择默认 AI 生成模型")
        model_combo = model_row.layout().itemAt(1).widget()
        model_combo.addItems(["DeepSeek V3", "GPT-4o", "Gemini 2.0", "智谱 GLM-5"])
        model_combo.setFixedWidth(180)
        model_combo.setStyleSheet(theme_combo.styleSheet())
        ai_layout.insertWidget(1, model_row)

        # 使用量显示
        usage_label = QLabel("本月 API 调用: 1,234 次")
        usage_label.setFont(QFont("", FontSizes.sm))
        usage_label.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        ai_layout.insertWidget(2, usage_label)

        container_layout.addWidget(ai)

        # ── 导出设置 ──────────────────────────────
        export = SettingsGroup("导出", "📤")
        exp_layout = export.layout()

        # 默认格式
        fmt_row = SettingsRow("默认格式", QComboBox(), "导出视频的默认格式")
        fmt_combo = fmt_row.layout().itemAt(1).widget()
        fmt_combo.addItems(["MP4", "MOV", "AVI", "MKV"])
        fmt_combo.setFixedWidth(120)
        fmt_combo.setStyleSheet(theme_combo.styleSheet())
        exp_layout.insertWidget(0, fmt_row)

        # 默认分辨率
        res_row = SettingsRow("默认分辨率", QComboBox(), "导出视频的默认分辨率")
        res_combo = res_row.layout().itemAt(1).widget()
        res_combo.addItems(["1080P (1920×1080)", "720P (1280×720)", "4K (3840×2160)"])
        res_combo.setFixedWidth(200)
        res_combo.setStyleSheet(theme_combo.styleSheet())
        exp_layout.insertWidget(1, res_row)

        container_layout.addWidget(export)

        # ── 快捷键设置 ────────────────────────────
        shortcuts = SettingsGroup("快捷键", "⌨")
        short_layout = shortcuts.layout()

        shortcuts_info = QLabel(
            "新建项目: Ctrl+N\n"
            "打开项目: Ctrl+O\n"
            "保存: Ctrl+S\n"
            "导出: Ctrl+E\n"
            "撤销: Ctrl+Z\n"
            "重做: Ctrl+Y\n"
            "全屏预览: F11"
        )
        shortcuts_info.setFont(QFont("", FontSizes.sm))
        shortcuts_info.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        shortcuts_info.setLineSpacing(6)
        short_layout.insertWidget(0, shortcuts_info)

        container_layout.addWidget(shortcuts)

        # ── 关于 ─────────────────────────────────
        about = SettingsGroup("关于", "ℹ")
        about_layout = about.layout()

        about_info = QLabel(
            "<b>Voxplore</b> v2.0.0<br>"
            "智能视频创作平台<br><br>"
            "© 2025 Agions. MIT License."
        )
        about_info.setFont(QFont("", FontSizes.sm))
        about_info.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        about_info.setAlignment(Qt.AlignmentFlag.AlignLeft)
        about_layout.insertWidget(0, about_info)

        check_btn = QPushButton("检查更新")
        check_btn.setObjectName("btn_secondary")
        check_btn.setFixedSize(100, 32)
        check_btn.setStyleSheet(f"""
            QPushButton#btn_secondary {{
                background: transparent;
                color: {Colors.PRIMARY_400};
                border: 1px solid {Colors.PRIMARY_500};
                border-radius: {Radii.base};
                font-size: {FontSizes.sm};
            }}
            QPushButton#btn_secondary:hover {{
                background: rgba(139, 92, 246, 0.1);
            }}
        """)
        about_layout.insertWidget(1, check_btn)

        container_layout.addWidget(about)

        container_layout.addStretch()

        scroll.setWidget(container)
        layout.addWidget(scroll)
