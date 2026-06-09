"""
StylesheetTemplates - 消除 UI 组件中 182 处重复的 setStyleSheet 样式块

提供常用 UI 组件的样式生成函数, 避免在每个组件中重复书写 CSS 模板.

使用示例::

    from scenefab.ui.common.stylesheet_templates import ST

    label.setStyleSheet(ST.badge(color=\"#10B981\", bg=\"#10B98120\"))
    frame.setStyleSheet(ST.card(bg=\"#1a1a1a\", border=\"#333\"))
    text_edit.setStyleSheet(ST.input_field(bg=\"#111\", border=\"#333\", focus=\"#4a9eff\"))
"""

from __future__ import annotations


class _StylesheetTemplates:
    """样式模板集合 — 所有方法返回可直接传入 setStyleSheet 的字符串."""

    @staticmethod
    def card(
        bg: str = "oklch(0.16 0.01 250)",
        border: str = "oklch(0.24 0.01 250)",
        radius: int = 12,
        border_width: int = 1,
    ) -> str:
        """卡片容器: QFrame 圆角边框背景."""
        return f"""
            QFrame {{
                background: {bg};
                border: {border_width}px solid {border};
                border-radius: {radius}px;
            }}
        """

    @staticmethod
    def badge(
        color: str = "oklch(0.65 0.20 250)",
        bg: str = "oklch(0.65 0.20 250)20",
        radius: int = 4,
        font_size: int = 11,
    ) -> str:
        """徽章/标签: 圆角背景 + 颜色文字."""
        return f"""
            color: {color};
            background: {bg};
            border: 1px solid {color}40;
            border-radius: {radius}px;
            font-size: {font_size}px;
            font-weight: 600;
            padding: 0 6px;
        """

    @staticmethod
    def pill_badge(
        color: str = "oklch(0.65 0.20 250)",
        bg: str = "oklch(0.65 0.20 250)20",
        radius: int = 6,
        padding_h: int = 8,
        padding_v: int = 3,
    ) -> str:
        """药丸徽章: 圆角背景 + 内边距, 用于时间戳等."""
        return f"""
            color: {color};
            background: {bg};
            padding: {padding_v}px {padding_h}px;
            border-radius: {radius}px;
        """

    @staticmethod
    def input_field(
        bg: str = "oklch(0.13 0.01 250)",
        border: str = "oklch(0.24 0.01 250)",
        focus: str = "oklch(0.65 0.20 250)",
        text: str = "oklch(0.93 0.01 250)",
        radius: int = 8,
    ) -> str:
        """输入框: QTextEdit/QLineEdit 圆角边框 + 聚焦高亮."""
        return f"""
            background: {bg};
            color: {text};
            border: 1px solid {border};
            border-radius: {radius}px;
            padding: 10px;
            line-height: 1.6;
        """ + f"""
            :focus {{
                border-color: {focus};
            }}
        """

    @staticmethod
    def button_primary(
        bg: str = "oklch(0.65 0.20 250)",
        text: str = "white",
        radius: int = 8,
        padding_h: int = 16,
        padding_v: int = 6,
    ) -> str:
        """主按钮: 实心背景 + 圆角."""
        return f"""
            QPushButton {{
                background: {bg};
                color: {text};
                border: none;
                border-radius: {radius}px;
                padding: {padding_v}px {padding_h}px;
                font-size: 12px;
            }}
        """

    @staticmethod
    def button_secondary(
        bg: str = "transparent",
        border: str = "oklch(0.24 0.01 250)",
        text: str = "oklch(0.75 0.01 250)",
        radius: int = 8,
    ) -> str:
        """次按钮: 透明背景 + 边框."""
        return f"""
            QPushButton {{
                background: {bg};
                color: {text};
                border: 1px solid {border};
                border-radius: {radius}px;
                padding: 6px 16px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                border-color: {text};
            }}
        """

    @staticmethod
    def progress_bar(
        bg: str = "oklch(0.20 0.01 250)",
        chunk: str = "oklch(0.65 0.20 250)",
        radius: int = 4,
    ) -> str:
        """进度条: 圆角背景 + 色块."""
        return f"""
            QProgressBar {{
                background: {bg};
                border: none;
                border-radius: {radius}px;
                text-align: center;
                color: white;
            }}
            QProgressBar::chunk {{
                background: {chunk};
                border-radius: {radius}px;
            }}
        """

    @staticmethod
    def text_color(color: str = "oklch(0.93 0.01 250)", font_size: int = 12) -> str:
        """文字颜色: QLabel 常用."""
        return f"color: {color}; font-size: {font_size}px;"

    @staticmethod
    def text_muted(color: str = "oklch(0.55 0.01 250)", font_size: int = 10) -> str:
        """弱化文字: 次要信息."""
        return f"color: {color}; font-size: {font_size}px;"


# 全局单例, 无需实例化
ST = _StylesheetTemplates()
