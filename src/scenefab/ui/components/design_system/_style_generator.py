#!/usr/bin/env python3

"""
Qt style generator.

将 design tokens 转换为 PySide6 样式表（QSS）。
与 dark_theme.qss 保持同步。

历史：原位于 scenefab.ui.components.design_system，Phase 3 重构中
拆分为独立模块以隔离样式生成职责。
"""

from ._tokens import _C, Radius


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
        "primary": f"background: {_C.Primary};\nborder: none;\ncolor: #ffffff;",
        "primary:hover": f"background: {_C.PrimaryHover};",
        "primary:pressed": f"background: {_C.PrimaryPressed};",
        "primary:disabled": f"background: {_C.BorderDefault};\ncolor: {_C.TextDisabled};\nopacity: 0.6;",
        "secondary": f"background: transparent;\nborder: 1px solid {_C.BorderDefault};\ncolor: {_C.TextSecondary};",
        "secondary:hover": f"background: {_C.BgElevated};\nborder-color: {_C.BorderStrong};\ncolor: {_C.TextPrimary};",
        "secondary:pressed": f"background: {_C.BgOverlay};",
        "secondary:disabled": f"background: transparent;\ncolor: {_C.TextDisabled};\nborder-color: {_C.BorderSubtle};\nopacity: 0.6;",
        "danger": f"background: {_C.Error};\nborder: none;\ncolor: #ffffff;",
        "danger:hover": f"background: {_C.ErrorSubtle};",
        "danger:pressed": f"background: {_C.AccentSubtle};",
        "ghost": f"background: transparent;\nborder: none;\ncolor: {_C.TextMuted};",
        "ghost:hover": f"background: {_C.BgElevated};\ncolor: {_C.TextPrimary};",
        "ghost:pressed": f"background: {_C.BgOverlay};",
        "ghost:disabled": f"background: transparent;\ncolor: {_C.TextDisabled};",
    }

    @staticmethod
    def button(variant: str = "primary") -> str:
        """按钮样式"""
        v = StyleSheet._BUTTON_VARIANTS
        return f"""
        QPushButton {{
            {StyleSheet._BUTTON_BASE}
            {v.get(variant, v["primary"])}
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
        bg = _C.BgElevated if elevated else _C.BgSurface
        return f"""
        QFrame {{
            background: {bg};
            border: 1px solid {_C.BorderDefault};
            border-radius: {Radius.lg};
        }}
        """

    @staticmethod
    def input(error: bool = False) -> str:
        """输入框样式"""
        border = _C.Error if error else _C.BorderDefault
        focus_border = _C.Error if error else _C.Primary
        return f"""
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background: {_C.BgBase};
            color: {_C.TextPrimary};
            border: 1px solid {border};
            border-radius: {Radius.md};
            padding: 10px 14px;
            font-size: 14px;
            min-height: 36px;
        }}
        QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover {{
            border-color: {_C.BorderStrong};
        }}
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: {focus_border};
            background-color: {_C.BgSurface};
        }}
        QLineEdit::placeholder, QTextEdit::placeholder, QPlainTextEdit::placeholder {{
            color: {_C.TextDisabled};
            font-style: italic;
        }}
        """

    @staticmethod
    def label(secondary: bool = False, muted: bool = False) -> str:
        """标签样式"""
        if muted:
            color = _C.TextMuted
        elif secondary:
            color = _C.TextSecondary
        else:
            color = _C.TextPrimary
        return f"QLabel {{ color: {color}; font-size: 14px; }}"

    @staticmethod
    def panel() -> str:
        """面板样式"""
        return f"QWidget {{ background-color: {_C.BgSurface}; }}"

    @staticmethod
    def progress_bar() -> str:
        """进度条样式"""
        return f"""
        QProgressBar {{
            background: {_C.ProgressTrack};
            border: none;
            border-radius: {Radius.md};
            text-align: center;
            color: {_C.TextPrimary};
            font-size: 12px;
            font-weight: 600;
            height: 24px;
        }}
        QProgressBar::chunk {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {_C.Primary},
                stop:1 {_C.PrimaryHover});
            border-radius: {Radius.md};
            margin: 2px;
        }}
        """

    @staticmethod
    def nav_button(selected: bool = False) -> str:
        """导航按钮样式"""
        if selected:
            bg = _C.PrimarySubtle
            color = _C.Primary
        else:
            bg = "transparent"
            color = _C.TextMuted
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
            background-color: {_C.BgElevated};
            color: {_C.TextPrimary};
        }}
        """

    @staticmethod
    def tooltip() -> str:
        """提示框样式"""
        return f"""
        QToolTip {{
            background: {_C.BgElevated};
            color: {_C.TextPrimary};
            border: 1px solid {_C.BorderDefault};
            border-radius: {Radius.md};
            padding: 10px 14px;
            font-size: 12px;
            font-weight: 500;
        }}
        """


__all__ = ["StyleSheet"]
