#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Voxplore Design System — OKLCH 感知均匀色彩系统
frontend-design-pro 规范 · 2026-04-10

规范参考：
- 色彩：OKLCH 空间（感知均匀，亮度/色度解耦）
- 字体：Geist / DM Sans / Sora（有个性，避免 Inter/Arial）
- 动效：OutCubic 缓动，拒绝 bounce/elastic
- 空间：4px 基础网格，65ch 内容宽度上限
"""

from PySide6.QtWidgets import (
    QWidget, QPushButton, QLabel, QLineEdit, QProgressBar, QFrame
)
from PySide6.QtCore import Qt


# ─── OKLCH 色彩系统 ────────────────────────────────────────
class Colors:
    """
    OKLCH 色彩 tokens — 与 dark_theme.qss 保持同步

    使用说明：
        color = Colors.Primary          # str: "oklch(0.65 0.20 250)"
        palette = Colors.Warning.value  # 获取 CSS 变量字符串
    """

    # ── 主色 Primary ──
    Primary = "oklch(0.65 0.20 250)"       # #388BFD — 主操作蓝
    PrimaryHover = "oklch(0.70 0.24 250)"  # 悬停增亮
    PrimaryPressed = "oklch(0.55 0.18 250)" # 按下略暗
    PrimarySubtle = "oklch(0.70 0.12 250)" # 浅色背景

    # ── 背景 Background（暗色模式）─
    BgBase = "oklch(0.13 0.01 250)"         # #121212 — 最深背景
    BgSurface = "oklch(0.16 0.01 250)"     # #1a1a1a — 卡片/面板
    BgElevated = "oklch(0.19 0.01 250)"     # #1f1f1f — 悬浮元素
    BgOverlay = "oklch(0.22 0.01 250)"      # #252525 — 遮罩层

    # ── 边框 Border ──
    BorderDefault = "oklch(0.24 0.01 250)"   # #2e2e2e — 默认边框
    BorderSubtle = "oklch(0.19 0.01 250)"    # #222 — 弱边框
    BorderStrong = "oklch(0.32 0.01 250)"   # #404040 — 强调边框

    # ── 文字 Text ──
    TextPrimary = "oklch(0.93 0.01 250)"     # #e8e8e8 — 主要文字
    TextSecondary = "oklch(0.75 0.01 250)"  # #a8a8a8 — 次要文字
    TextMuted = "oklch(0.55 0.01 250)"       # #787878 — 辅助文字
    TextDisabled = "oklch(0.40 0.01 250)"    # #555 — 禁用文字

    # ── 功能色 Functional ──
    Success = "oklch(0.65 0.22 145)"         # #2EA043 — 成功
    SuccessSubtle = "oklch(0.70 0.14 145)"   # 成功浅色
    Warning = "oklch(0.75 0.20 85)"          # #D29922 — 警告
    WarningSubtle = "oklch(0.78 0.14 85)"     # 警告浅色
    Error = "oklch(0.63 0.24 25)"            # #DA3633 — 错误
    ErrorSubtle = "oklch(0.67 0.16 25)"      # 错误浅色
    Info = "oklch(0.65 0.20 250)"            # 同 Primary

    # ── 强调色 Accent ──
    Accent = "oklch(0.70 0.18 300)"          # #A371F7 — 紫色强调
    AccentSubtle = "oklch(0.75 0.12 300)"    # 强调浅色

    # ── 进度/交互 ──
    ProgressTrack = "oklch(0.20 0.01 250)"   # 进度条轨道
    FocusRing = "oklch(0.65 0.20 250)"       # 焦点环

    # ── 十六进制兼容（仅在 OKLCH 不支持时降级使用）─
    _HEX_FALLBACK = {
        "primary": "#388BFD",
        "bg_base": "#121212",
        "text_primary": "#e8e8e8",
        "border_default": "#2e2e2e",
        "success": "#2EA043",
        "warning": "#D29922",
        "error": "#DA3633",
    }


# ─── 字体系统 ──────────────────────────────────────────────
class Fonts:
    """
    字体 tokens — frontend-design-pro 规范
    优先使用有个性的字体，避免 Arial/Inter/system-ui
    """
    Display = (
        '"SF Pro Display", "Inter var", "Geist", "DM Sans", '
        '"Sora", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    )
    Body = (
        '"SF Pro Text", "Inter var", "Geist", "DM Sans", '
        '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    )
    Mono = (
        '"SF Mono", "JetBrains Mono", "Fira Code", "Consolas", monospace'
    )


# ─── 动效系统 ──────────────────────────────────────────────
class Motion:
    """
    frontend-design-pro 规范：
    - 标准曲线：OutCubic — cubic-bezier(0.16, 1, 0.3, 1)
    - 微交互：100-200ms
    - 页面过渡：300-500ms
    - 禁止 bounce/elastic — 显得廉价
    """
    # 缓动曲线
    OutCubic = "cubic-bezier(0.16, 1, 0.3, 1)"   # 标准快入慢出
    InCubic = "cubic-bezier(0.7, 0, 0.84, 0)"     # 慢入快出
    InOut = "cubic-bezier(0.65, 0, 0.35, 1)"      # 缓入缓出
    Spring = "cubic-bezier(0.34, 1.56, 0.64, 1)"  # 轻微弹性（克制）

    # 时长
    Instant = "50ms"    # 极快（hover 反馈）
    Fast = "100ms"      # 快（按钮状态）
    Normal = "200ms"    # 标准（展开/收起）
    Slow = "300ms"      # 慢（页面过渡）
    Slower = "400ms"    # 更慢（大型模态）
    Page = "500ms"      # 页面级切换


# ─── 阴影系统 ──────────────────────────────────────────────
class Shadows:
    sm = "0 1px 2px oklch(0.00 0.00 0.00 / 0.20)"
    md = "0 4px 12px oklch(0.00 0.00 0.00 / 0.30)"
    lg = "0 8px 24px oklch(0.00 0.00 0.00 / 0.40)"
    xl = "0 16px 48px oklch(0.00 0.00 0.00 / 0.50)"
    GlowPrimary = "0 0 20px oklch(0.65 0.20 250 / 0.35)"
    GlowAccent = "0 0 20px oklch(0.70 0.18 300 / 0.35)"


# ─── 样式生成器 ────────────────────────────────────────────
class StyleSheet:
    """
    PySide6 样式生成器 — 与 dark_theme.qss 同步
    """

    @staticmethod
    def button(variant: str = "primary") -> str:
        """按钮样式"""
        radius = Radius
        base = f"""
            border-radius: {radius.md};
            padding: 10px 20px;
            font-size: 14px;
            font-weight: 600;
            min-height: 36px;
        """

        variants = {
            "primary": f"""
                background: {Colors.Primary};
                border: none;
                color: #ffffff;
            """,
            "primary:hover": f"""
                background: {Colors.PrimaryHover};
            """,
            "primary:pressed": f"""
                background: {Colors.PrimaryPressed};
            """,
            "primary:disabled": f"""
                background: {Colors.BorderDefault};
                color: {Colors.TextDisabled};
                opacity: 0.6;
            """,
            "secondary": f"""
                background: transparent;
                border: 1px solid {Colors.BorderDefault};
                color: {Colors.TextSecondary};
            """,
            "secondary:hover": f"""
                background: {Colors.BgElevated};
                border-color: {Colors.BorderStrong};
                color: {Colors.TextPrimary};
            """,
            "secondary:disabled": f"""
                background: transparent;
                color: {Colors.TextDisabled};
                border-color: {Colors.BorderSubtle};
                opacity: 0.6;
            """,
            "danger": f"""
                background: {Colors.Error};
                border: none;
                color: #ffffff;
            """,
            "danger:hover": f"""
                background: {Colors.ErrorSubtle};
            """,
            "ghost": f"""
                background: transparent;
                border: none;
                color: {Colors.TextMuted};
            """,
            "ghost:hover": f"""
                background: {Colors.TextMuted} / 0.08;
                color: {Colors.TextPrimary};
            """,
        }

        return f"""
        QPushButton {{
            {base}
            {variants.get("primary", "")}
        }}
        QPushButton:hover {{
            {variants.get(f"{variant}:hover", variants["primary:hover"])}
        }}
        QPushButton:pressed {{
            {variants.get(f"{variant}:pressed", variants["primary:pressed"])}
        }}
        QPushButton:disabled {{
            {variants.get(f"{variant}:disabled", variants["primary:disabled"])}
        }}
        """

    @staticmethod
    def card(elevated: bool = False) -> str:
        """卡片样式"""
        bg = Colors.BgElevated if elevated else Colors.BgSurface
        shadow = Shadows.md if elevated else "none"
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


# ─── 组件封装 ──────────────────────────────────────────────
class CFButton(QPushButton):
    """
    Voxplore 按钮 — 支持多变体

    用法：
        btn = CFButton("保存", variant="primary")
        btn = CFButton("取消", variant="secondary")
        btn = CFButton("删除", variant="danger")
    """

    def __init__(
        self,
        text: str = "",
        variant: str = "primary",
        icon: str = "",
        parent=None,
    ):
        super().__init__(text, parent)
        self.setStyleSheet(StyleSheet.button(variant))
        if icon:
            self.setText(f"{icon} {text}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class CFLabel(QLabel):
    """
    Voxplore 标签

    用法：
        lbl = CFLabel("标题")
        lbl = CFLabel("次要文字", secondary=True)
        lbl = CFLabel("辅助说明", muted=True)
    """

    def __init__(self, text: str = "", secondary: bool = False, muted: bool = False, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(StyleSheet.label(secondary, muted))


class CFCard(QFrame):
    """
    Voxplore 卡片

    用法：
        card = CFCard()
        card = CFCard(elevated=True)  # 带阴影
    """

    def __init__(self, elevated: bool = False, parent=None):
        super().__init__(parent)
        self.setStyleSheet(StyleSheet.card(elevated))


class CFPanel(QWidget):
    """Voxplore 面板"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(StyleSheet.panel())


class CFInput(QLineEdit):
    """
    Voxplore 输入框

    用法：
        input = CFInput(placeholder="请输入...")
        input = CFInput(placeholder="邮箱", error=True)
    """

    def __init__(self, placeholder: str = "", error: bool = False, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setStyleSheet(StyleSheet.input(error))


class CFProgressBar(QProgressBar):
    """Voxplore 进度条"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(StyleSheet.progress_bar())


class CFNavButton(CFButton):
    """
    Voxplore 导航按钮 — 支持选中状态

    用法：
        nav = CFNavButton("首页", icon="🏠", selected=True)
        nav.set_selected(False)
    """

    def __init__(self, text: str = "", icon: str = "", selected: bool = False, parent=None):
        super().__init__(text, variant="ghost", parent=parent)
        self.selected = selected
        if icon:
            self.setText(f"{icon} {text}")
        self._update_style()

    def _update_style(self):
        self.setStyleSheet(StyleSheet.nav_button(self.selected))

    def set_selected(self, selected: bool):
        self.selected = selected
        self._update_style()
