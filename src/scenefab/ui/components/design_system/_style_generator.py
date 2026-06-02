#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SceneFab 样式生成器

将 design tokens 转换为 PySide6 样式表（QSS）。
与 dark_theme.qss 保持同步。

历史：原位于 scenefab.ui.components.design_system，Phase 3 重构中
拆分为独立模块以隔离样式生成职责。
"""

from ._tokens import Colors, Radius


# ─── 样式生成器 ────────────────────────────────────────────
class StyleSheet:
    """
    PySide6 样式生成器 — 与 dark_theme.qss 同步
    """

    # 类常量：按钮变体样式（避免每次调用重建字典）
    _BUTTON_BASE = f"""
            border-radius: {Radius.md};
            padding: 10px 20px;
            font-size: 14px;
            font-weight: 600;
            min-height: 36px;
        """
    _BUTTON_VARIANTS = {
        "primary": f"background: {Colors.Primary};\nborder: none;\ncolor: #ffffff;",
        "primary:hover": f"background: {Colors.PrimaryHover};",
        "primary:pressed": f"background: {Colors.PrimaryPressed};",
        "primary:disabled": f"background: {Colors.BorderDefault};\ncolor: {Colors.TextDisabled};\nopacity: 0.6;",
        "secondary": f"background: transparent;\nborder: 1px solid {Colors.BorderDefault};\ncolor: {Colors.TextSecondary};",
        "secondary:hover": f"background: {Colors.BgElevated};\nborder-color: {Colors.BorderStrong};\ncolor: {Colors.TextPrimary};",
        "secondary:disabled": f"background: transparent;\ncolor: {Colors.TextDisabled};\nborder-color: {Colors.BorderSubtle};\nopacity: 0.6;",
        "danger": f"background: {Colors.Error};\nborder: none;\ncolor: #ffffff;",
        "danger:hover": f"background: {Colors.ErrorSubtle};",
        "ghost": f"background: transparent;\nborder: none;\ncolor: {Colors.TextMuted};",
        "ghost:hover": f"background: {Colors.TextMuted} / 0.08;\ncolor: {Colors.TextPrimary};",
    }

    @staticmethod
    def button(variant: str = "primary") -> str:
        """按钮样式"""
        v = StyleSheet._BUTTON_VARIANTS
        return f"""
        QPushButton {{
            {StyleSheet._BUTTON_BASE}
            {v.get("primary", "")}
        }}
        QPushButton:hover {{
            {v.get(f"{variant}:hover", v["primary:hover"])}
        }}
        QPushButton:pressed {{
            {v.get(f"{variant}:pressed", v["primary:pressed"])}
        }}
        QPushButton:disabled {{
            {v.get(f"{variant}:disabled", v["primary:disabled"])}
        }}
        """

    @staticmethod
    def card(elevated: bool = False) -> str:
        """卡片样式"""
        bg = Colors.BgElevated if elevated else Colors.BgSurface
        return f"""
        QFrame {{
            background: {bg};
            border: 1px solid {Colors.BorderDefault};
            border-radius: {Radius.lg};
        }}
        """

    @staticmethod
    def input(error: bool = False) -> str:
        """输入框样式"""
        border = Colors.Error if error else Colors.BorderDefault
        focus_border = Colors.Error if error else Colors.Primary
        return f"""
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background: {Colors.BgBase};
            color: {Colors.TextPrimary};
            border: 1px solid {border};
            border-radius: {Radius.md};
            padding: 10px 14px;
            font-size: 14px;
            min-height: 36px;
        }}
        QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover {{
            border-color: {Colors.BorderStrong};
        }}
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: {focus_border};
            background-color: {Colors.BgSurface};
        }}
        QLineEdit::placeholder, QTextEdit::placeholder, QPlainTextEdit::placeholder {{
            color: {Colors.TextDisabled};
            font-style: italic;
        }}
        """

    @staticmethod
    def label(secondary: bool = False, muted: bool = False) -> str:
        """标签样式"""
        if muted:
            color = Colors.TextMuted
        elif secondary:
            color = Colors.TextSecondary
        else:
            color = Colors.TextPrimary
        return f"QLabel {{ color: {color}; font-size: 14px; }}"

    @staticmethod
    def panel() -> str:
        """面板样式"""
        return f"QWidget {{ background-color: {Colors.BgSurface}; }}"

    @staticmethod
    def progress_bar() -> str:
        """进度条样式"""
        return f"""
        QProgressBar {{
            background: {Colors.ProgressTrack};
            border: none;
            border-radius: {Radius.md};
            text-align: center;
            color: {Colors.TextPrimary};
            font-size: 12px;
            font-weight: 600;
            height: 24px;
        }}
        QProgressBar::chunk {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {Colors.Primary},
                stop:1 {Colors.PrimaryHover});
            border-radius: {Radius.md};
            margin: 2px;
        }}
        """

    @staticmethod
    def nav_button(selected: bool = False) -> str:
        """导航按钮样式"""
        if selected:
            bg = f"{Colors.Primary} / 0.15"
            color = Colors.Primary
        else:
            bg = "transparent"
            color = Colors.TextMuted
        return f"""
        QPushButton {{
            text-align: left;
            background-color: {bg};
            border: none;
            border-radius: {Radius.md};
            color: {color};
            padding: 12px 16px;
            font-size: 14px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {Colors.TextMuted} / 0.08;
            color: {Colors.TextPrimary};
        }}
        """

    @staticmethod
    def tooltip() -> str:
        """提示框样式"""
        return f"""
        QToolTip {{
            background: {Colors.BgElevated};
            color: {Colors.TextPrimary};
            border: 1px solid {Colors.BorderDefault};
            border-radius: {Radius.md};
            padding: 10px 14px;
            font-size: 12px;
            font-weight: 500;
        }}
        """


__all__ = ["StyleSheet"]
