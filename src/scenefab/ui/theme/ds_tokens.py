#!/usr/bin/env python3
"""
SceneFab Design System v6
语义化色彩体系 + 组件级变量
"""


# ═══════════════════════════════════════════════════════════════════
# OKLCH 语义化色彩（午夜极光主题）
# ═══════════════════════════════════════════════════════════════════


class Colors:
    """语义化色彩"""

    # ── 背景层 ──────────────────────────────────────────────────
    BG_BASE = "#0A0C12"  # 最深层背景
    BG_SURFACE = "#12151F"  # 卡片/面板
    BG_ELEVATED = "#1A1E2C"  # 悬浮/高亮层
    BG_OVERLAY = "#212638"  # 模态/下拉
    BG_INPUT = "#0E1018"  # 输入框背景

    # ── 边框层 ──────────────────────────────────────────────────
    BORDER_SUBTLE = "#1E2436"  # 微弱分割
    BORDER_DEFAULT = "#2A3048"  # 默认边框
    BORDER_STRONG = "#3D4566"  # 强调边框
    BORDER_FOCUS = "#7C3AED"  # 聚焦边框（紫色）

    # ── 主色：极光紫 ───────────────────────────────────────────
    PRIMARY_LIGHTEST = "#F5F3FF"
    PRIMARY_LIGHTER = "#EDE9FE"
    PRIMARY_LIGHT = "#DDD6FE"
    PRIMARY_NORMAL = "#C4B5FD"
    PRIMARY = "#A78BFA"  # 主色值
    PRIMARY_DARK = "#8B5CF6"
    PRIMARY_DARKER = "#7C3AED"
    PRIMARY_DARKEST = "#6D28D9"

    # ── 辅助色：冰蓝 ───────────────────────────────────────────
    ACCENT_LIGHT = "#E0F2FE"
    ACCENT_NORMAL = "#38BDF8"
    ACCENT = "#0EA5E9"
    ACCENT_DARK = "#0284C7"

    # ── 功能色 ─────────────────────────────────────────────────
    SUCCESS = "#10B981"
    SUCCESS_LIGHT = "#D1FAE5"
    WARNING = "#F59E0B"
    WARNING_LIGHT = "#FEF3C7"
    ERROR = "#EF4444"
    ERROR_LIGHT = "#FEE2E2"
    INFO = "#6366F1"

    # ── 文字层 ─────────────────────────────────────────────────
    TEXT_PRIMARY = "#F1F5F9"  # 主要文字
    TEXT_SECONDARY = "#94A3B8"  # 次要文字
    TEXT_MUTED = "#64748B"  # 弱化文字
    TEXT_DISABLED = "#475569"  # 禁用文字
    TEXT_INVERSE = "#0A0C12"  # 反色文字

    # ── 侧边栏渐变 ─────────────────────────────────────────────
    SIDEBAR_TOP = "#13111E"
    SIDEBAR_MID = "#0D0B16"
    SIDEBAR_BOTTOM = "#080710"
    SIDEBAR_GLOW = "#7C3AED"

    # ── 状态色（透明度修饰，RRGGBBAA格式）─────────────────────
    PRIMARY_10 = "#A78BFA1A"  # 10% 透明度
    SUCCESS_10 = "#10B9811A"
    ERROR_10 = "#EF44441A"


# ═══════════════════════════════════════════════════════════════════
# 字体系统
# ═══════════════════════════════════════════════════════════════════


class FontSizes:
    xs = 11
    sm = 12
    base = 13
    md = 14
    lg = 16
    xl = 18
    xxl = 22
    xxxl = 28
    display = 36


class FontWeights:
    Normal = 400
    Medium = 500
    SemiBold = 600
    Bold = 700


# ═══════════════════════════════════════════════════════════════════
# 间距系统（8px 基准）
# ═══════════════════════════════════════════════════════════════════


class Spacing:
    xxs = 4
    xs = 8
    sm = 10
    md = 12
    base = 16
    lg = 20
    xl = 24
    xxl = 32
    xxxl = 48
    huge = 64


# ═══════════════════════════════════════════════════════════════════
# 圆角系统
# ═══════════════════════════════════════════════════════════════════


class Radii:
    none = 0
    sm = 4
    base = 8
    md = 10
    lg = 12
    xl = 16
    xl2 = 20
    full = 9999


# ═══════════════════════════════════════════════════════════════════
# 阴影系统（多层次）
# ═══════════════════════════════════════════════════════════════════


class Shadows:
    NONE = "none"

    SM = "0 1px 2px rgba(0,0,0,0.4)"
    BASE = "0 4px 6px rgba(0,0,0,0.4), 0 2px 4px rgba(0,0,0,0.3)"
    MD = "0 10px 15px rgba(0,0,0,0.45), 0 4px 6px rgba(0,0,0,0.35)"
    LG = "0 20px 25px rgba(0,0,0,0.5), 0 8px 10px rgba(0,0,0,0.4)"
    XL = "0 25px 50px rgba(0,0,0,0.6)"

    GLOW_PURPLE = (
        "0 0 0 1px rgba(167,139,250,0.3), "
        "0 0 20px rgba(139,92,246,0.2), "
        "0 0 40px rgba(139,92,246,0.1)"
    )
    GLOW_ACCENT = "0 0 0 1px rgba(56,189,248,0.3), 0 0 20px rgba(14,165,233,0.2)"
    GLOW_SUCCESS = "0 0 0 1px rgba(16,185,129,0.3), 0 0 16px rgba(16,185,129,0.15)"


# ═══════════════════════════════════════════════════════════════════
# 动效规范
# ═══════════════════════════════════════════════════════════════════


class Durations:
    instant = 50
    fast = 100
    normal = 200
    slow = 300
    xslow = 500


class Easings:
    standard = "cubic-bezier(0.4, 0, 0.2, 1)"
    decelerate = "cubic-bezier(0, 0, 0.2, 1)"
    accelerate = "cubic-bezier(0.4, 0, 1, 1)"
    spring = "cubic-bezier(0.175, 0.885, 0.32, 1.275)"
    ease_out = "cubic-bezier(0, 0, 0.2, 1)"


# ═══════════════════════════════════════════════════════════════════
# 组件级 QSS 片段（可直接拼接）
# ═══════════════════════════════════════════════════════════════════



# ── 颜色常量本地引用 (mypy f-string bug workaround) ──────
class _C:
    ACCENT = "#0EA5E9"
    ACCENT_DARK = "#0284C7"
    ACCENT_LIGHT = "#E0F2FE"
    ACCENT_NORMAL = "#38BDF8"
    BG_BASE = "#0A0C12"
    BG_ELEVATED = "#1A1E2C"
    BG_INPUT = "#0E1018"
    BG_OVERLAY = "#212638"
    BG_SURFACE = "#12151F"
    BORDER_DEFAULT = "#2A3048"
    BORDER_FOCUS = "#7C3AED"
    BORDER_STRONG = "#3D4566"
    BORDER_SUBTLE = "#1E2436"
    ERROR = "#EF4444"
    ERROR_10 = "#EF44441A"
    ERROR_LIGHT = "#FEE2E2"
    INFO = "#6366F1"
    PRIMARY = "#A78BFA"
    PRIMARY_10 = "#A78BFA1A"
    PRIMARY_DARK = "#8B5CF6"
    PRIMARY_DARKER = "#7C3AED"
    PRIMARY_DARKEST = "#6D28D9"
    PRIMARY_LIGHT = "#DDD6FE"
    PRIMARY_LIGHTER = "#EDE9FE"
    PRIMARY_LIGHTEST = "#F5F3FF"
    PRIMARY_NORMAL = "#C4B5FD"
    SIDEBAR_BOTTOM = "#080710"
    SIDEBAR_GLOW = "#7C3AED"
    SIDEBAR_MID = "#0D0B16"
    SIDEBAR_TOP = "#13111E"
    SUCCESS = "#10B981"
    SUCCESS_10 = "#10B9811A"
    SUCCESS_LIGHT = "#D1FAE5"
    TEXT_DISABLED = "#475569"
    TEXT_INVERSE = "#0A0C12"
    TEXT_MUTED = "#64748B"
    TEXT_PRIMARY = "#F1F5F9"
    TEXT_SECONDARY = "#94A3B8"
    WARNING = "#F59E0B"
    WARNING_LIGHT = "#FEF3C7"
C = _C()

class QSSComponents:
    """可复用的 QSS 片段"""

    @staticmethod
    def card(bg: str = None, border: str = None, radius: str = None) -> str:  # type: ignore[assignment]
        bg = bg or _C.BG_SURFACE
        border = border or _C.BORDER_SUBTLE
        radius = radius or Radii.lg  # type: ignore[assignment]
        return f"""
            background: {bg};
            border: 1px solid {border};
            border-radius: {radius};
        """

    @staticmethod
    def btn_primary() -> str:
        return f"""
            QPushButton {{
                background: {_C.PRIMARY_DARK};
                color: {_C.TEXT_PRIMARY};
                border: none;
                border-radius: {Radii.base};
                font-size: {FontSizes.base}px;
                font-weight: {FontWeights.Medium};
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background: {_C.PRIMARY};
            }}
            QPushButton:pressed {{
                background: {_C.PRIMARY_DARKER};
            }}
            QPushButton:disabled {{
                background: {_C.BG_ELEVATED};
                color: {_C.TEXT_DISABLED};
            }}
        """

    @staticmethod
    def btn_secondary() -> str:
        return f"""
            QPushButton {{
                background: transparent;
                color: {_C.TEXT_SECONDARY};
                border: 1px solid {_C.BORDER_DEFAULT};
                border-radius: {Radii.base};
                font-size: {FontSizes.base}px;
                font-weight: {FontWeights.Medium};
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background: {_C.BG_ELEVATED};
                color: {_C.TEXT_PRIMARY};
                border-color: {_C.BORDER_STRONG};
            }}
            QPushButton:pressed {{
                background: {_C.BG_OVERLAY};
            }}
        """

    @staticmethod
    def btn_ghost() -> str:
        return f"""
            QPushButton {{
                background: transparent;
                color: {_C.TEXT_MUTED};
                border: none;
                border-radius: {Radii.sm};
                font-size: {FontSizes.base}px;
            }}
            QPushButton:hover {{
                background: {_C.BG_ELEVATED};
                color: {_C.TEXT_SECONDARY};
            }}
        """

    @staticmethod
    def input() -> str:
        return f"""
            QLineEdit, QTextEdit {{
                background: {_C.BG_INPUT};
                color: {_C.TEXT_PRIMARY};
                border: 1px solid {_C.BORDER_DEFAULT};
                border-radius: {Radii.base};
                padding: 8px 12px;
                font-size: {FontSizes.base}px;
                selection-background-color: {_C.PRIMARY_DARK};
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border-color: {_C.PRIMARY_DARK};
                background: {_C.BG_SURFACE};
            }}
            QLineEdit::placeholder, QTextEdit::placeholder {{
                color: {_C.TEXT_DISABLED};
            }}
        """

    @staticmethod
    def combobox() -> str:
        return f"""
            QComboBox {{
                background: {_C.BG_INPUT};
                color: {_C.TEXT_PRIMARY};
                border: 1px solid {_C.BORDER_DEFAULT};
                border-radius: {Radii.base};
                padding: 6px 12px;
                font-size: {FontSizes.base}px;
            }}
            QComboBox:hover {{
                border-color: {_C.BORDER_STRONG};
            }}
            QComboBox:focus {{
                border-color: {_C.PRIMARY_DARK};
            }}
            QComboBox::dropDown {{
                border: none;
                padding-right: 4px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid {_C.TEXT_MUTED};
            }}
            QComboBox QAbstractItemView {{
                background: {_C.BG_OVERLAY};
                color: {_C.TEXT_PRIMARY};
                border: 1px solid {_C.BORDER_DEFAULT};
                border-radius: {Radii.base};
                selection-background-color: {_C.BG_ELEVATED};
            }}
        """

    @staticmethod
    def checkbox() -> str:
        return f"""
            QCheckBox {{
                spacing: 10px;
                color: {_C.TEXT_SECONDARY};
                font-size: {FontSizes.base}px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: {Radii.sm};
                border: 2px solid {_C.BORDER_STRONG};
                background: transparent;
            }}
            QCheckBox::indicator:hover {{
                border-color: {_C.PRIMARY};
            }}
            QCheckBox::indicator:checked {{
                background: {_C.PRIMARY_DARK};
                border-color: {_C.PRIMARY_DARK};
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOSIgdmlld0JveD0iMCAwIDEyIDkiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xIDQuNUw0LjUgOCAxMSAxIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPgo8L3N2Zz4K);
            }}
        """

    @staticmethod
    def progress_bar() -> str:
        return f"""
            QProgressBar {{
                background: {_C.BG_ELEVATED};
                border: none;
                border-radius: {Radii.full};
                height: 6px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {_C.PRIMARY_DARKER},
                    stop:1 {_C.PRIMARY}
                );
                border-radius: {Radii.full};
            }}
        """

    @staticmethod
    def scrollbar() -> str:
        return f"""
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {_C.BORDER_DEFAULT};
                border-radius: 3px;
                min-height: 40px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {_C.BORDER_STRONG};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QScrollBar:horizontal {{
                background: transparent;
                height: 6px;
                margin: 0;
            }}
            QScrollBar::handle:horizontal {{
                background: {_C.BORDER_DEFAULT};
                border-radius: 3px;
                min-width: 40px;
            }}
        """