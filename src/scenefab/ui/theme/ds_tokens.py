#!/usr/bin/env python3
"""
Design system tokens.

These values are aligned with resources/styles and keep the public token names
used by existing UI modules.

Theme mode (Phase 3)
---------------------

This module exposes two palettes, :class:`Colors` (light) and
:class:`DarkColors` (dark), and a single mutable container :class:`_C`
that most UI code reads from. The active palette is controlled by
:func:`set_theme_mode`. Pages that have already rendered read the
token via ``_C.X`` which is *rebound* on each mode change — that
means existing widgets don't auto-restyle. Callers that want
live theme switching must re-apply their stylesheets after
:func:`set_theme_mode` returns.

Persistence: the mode is *not* persisted here — that's the job of
``Application`` / ``QSettings`` layer. The function returns the new
mode so the caller can save it.
"""


# ═══════════════════════════════════════════════════════════════════
# 语义化色彩
# ═══════════════════════════════════════════════════════════════════


class Colors:
    """语义化色彩"""

    # ── 背景层 ──────────────────────────────────────────────────
    BG_BASE = "#f6f8fb"
    BG_SURFACE = "#ffffff"
    BG_ELEVATED = "#f1f5f9"
    BG_OVERLAY = "#e2e8f0"
    BG_INPUT = "#ffffff"

    # ── 边框层 ──────────────────────────────────────────────────
    BORDER_SUBTLE = "#dbe3ee"
    BORDER_DEFAULT = "#cbd5e1"
    BORDER_STRONG = "#0891b2"
    BORDER_FOCUS = "#0891b2"

    # ── 主色：叙事青 ───────────────────────────────────────────
    PRIMARY_LIGHTEST = "#e0f7fb"
    PRIMARY_LIGHTER = "#a5f3fc"
    PRIMARY_LIGHT = "#67e8f9"
    PRIMARY_NORMAL = "#22d3ee"
    PRIMARY = "#0891b2"
    PRIMARY_DARK = "#0e7490"
    PRIMARY_DARKER = "#155e75"
    PRIMARY_DARKEST = "#164e63"

    # ── 辅助色：重点标记 ───────────────────────────────────────
    ACCENT_LIGHT = "#ffe4e6"
    ACCENT_NORMAL = "#fb7185"
    ACCENT = "#f43f5e"
    ACCENT_DARK = "#be123c"
    ACCENT_SUBTLE = "#ffe4e6"

    # ── 功能色 ─────────────────────────────────────────────────
    SUCCESS = "#22c55e"
    SUCCESS_LIGHT = "#dcfce7"
    WARNING = "#f59e0b"
    WARNING_LIGHT = "#fef3c7"
    ERROR = "#e11d48"
    ERROR_LIGHT = "#ffe4e6"
    INFO = "#22d3ee"

    # ── 文字层 ─────────────────────────────────────────────────
    TEXT_PRIMARY = "#182235"
    TEXT_SECONDARY = "#334155"
    TEXT_MUTED = "#64748b"
    TEXT_DISABLED = "#94a3b8"
    TEXT_INVERSE = "#ffffff"

    # ── 侧边栏渐变 ─────────────────────────────────────────────
    SIDEBAR_TOP = "#ffffff"
    SIDEBAR_MID = "#f8fafc"
    SIDEBAR_BOTTOM = "#f1f5f9"
    SIDEBAR_GLOW = "#0891b2"

    # ── 状态色（透明度修饰，RRGGBBAA格式）─────────────────────
    PRIMARY_10 = "#0891b21A"
    SUCCESS_10 = "#22c55e1A"
    ERROR_10 = "#e11d481A"


class DarkColors:
    """Dark theme palette (Phase 3).

    Mirror of :class:`Colors` with values tuned for low-light UI. Only
    the colour tokens are redefined here — ``Radii`` / ``FontSizes``
    / ``Shadows`` etc. are shared with the light theme because they
    are theme-agnostic.
    """

    # ── 背景层 ──────────────────────────────────────────────────
    BG_BASE = "#0f172a"
    BG_SURFACE = "#1e293b"
    BG_ELEVATED = "#334155"
    BG_OVERLAY = "#475569"
    BG_INPUT = "#1e293b"

    # ── 边框层 ──────────────────────────────────────────────────
    BORDER_SUBTLE = "#334155"
    BORDER_DEFAULT = "#475569"
    BORDER_STRONG = "#22d3ee"
    BORDER_FOCUS = "#22d3ee"

    # ── 主色：叙事青 (提亮) ────────────────────────────────────
    PRIMARY_LIGHTEST = "#164e63"
    PRIMARY_LIGHTER = "#155e75"
    PRIMARY_LIGHT = "#0e7490"
    PRIMARY_NORMAL = "#0891b2"
    PRIMARY = "#22d3ee"
    PRIMARY_DARK = "#67e8f9"
    PRIMARY_DARKER = "#a5f3fc"
    PRIMARY_DARKEST = "#e0f7fb"

    # ── 辅助色 (提亮) ─────────────────────────────────────────
    ACCENT_LIGHT = "#4c0519"
    ACCENT_NORMAL = "#fb7185"
    ACCENT = "#fda4af"
    ACCENT_DARK = "#fecdd3"
    ACCENT_SUBTLE = "#4c0519"

    # ── 功能色 ─────────────────────────────────────────────────
    SUCCESS = "#4ade80"
    SUCCESS_LIGHT = "#14532d"
    WARNING = "#fbbf24"
    WARNING_LIGHT = "#78350f"
    ERROR = "#fb7185"
    ERROR_LIGHT = "#4c0519"
    INFO = "#22d3ee"

    # ── 文字层 (反转) ─────────────────────────────────────────
    TEXT_PRIMARY = "#f1f5f9"
    TEXT_SECONDARY = "#cbd5e1"
    TEXT_MUTED = "#94a3b8"
    TEXT_DISABLED = "#475569"
    TEXT_INVERSE = "#0f172a"

    # ── 侧边栏渐变 (深色版) ─────────────────────────────────
    SIDEBAR_TOP = "#0f172a"
    SIDEBAR_MID = "#1e293b"
    SIDEBAR_BOTTOM = "#334155"
    SIDEBAR_GLOW = "#22d3ee"

    # ── 状态色 (深色版透明度) ───────────────────────────────
    PRIMARY_10 = "#22d3ee1A"
    SUCCESS_10 = "#4ade801A"
    ERROR_10 = "#fb71851A"


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
        "0 0 0 1px rgba(34,211,238,0.28), "
        "0 0 20px rgba(8,145,178,0.22), "
        "0 0 40px rgba(8,145,178,0.12)"
    )
    GLOW_ACCENT = "0 0 0 1px rgba(244,63,94,0.28), 0 0 20px rgba(244,63,94,0.18)"
    GLOW_SUCCESS = "0 0 0 1px rgba(34,197,94,0.28), 0 0 16px rgba(34,197,94,0.16)"


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
    ACCENT = Colors.ACCENT
    ACCENT_DARK = Colors.ACCENT_DARK
    ACCENT_LIGHT = Colors.ACCENT_LIGHT
    ACCENT_NORMAL = Colors.ACCENT_NORMAL
    ACCENT_SUBTLE = Colors.ACCENT_SUBTLE
    BG_BASE = Colors.BG_BASE
    BG_ELEVATED = Colors.BG_ELEVATED
    BG_INPUT = Colors.BG_INPUT
    BG_OVERLAY = Colors.BG_OVERLAY
    BG_SURFACE = Colors.BG_SURFACE
    BORDER_DEFAULT = Colors.BORDER_DEFAULT
    BORDER_FOCUS = Colors.BORDER_FOCUS
    BORDER_STRONG = Colors.BORDER_STRONG
    BORDER_SUBTLE = Colors.BORDER_SUBTLE
    ERROR = Colors.ERROR
    ERROR_10 = Colors.ERROR_10
    ERROR_LIGHT = Colors.ERROR_LIGHT
    INFO = Colors.INFO
    PRIMARY = Colors.PRIMARY
    PRIMARY_10 = Colors.PRIMARY_10
    PRIMARY_DARK = Colors.PRIMARY_DARK
    PRIMARY_DARKER = Colors.PRIMARY_DARKER
    PRIMARY_DARKEST = Colors.PRIMARY_DARKEST
    PRIMARY_LIGHT = Colors.PRIMARY_LIGHT
    PRIMARY_LIGHTER = Colors.PRIMARY_LIGHTER
    PRIMARY_LIGHTEST = Colors.PRIMARY_LIGHTEST
    PRIMARY_NORMAL = Colors.PRIMARY_NORMAL
    SIDEBAR_BOTTOM = Colors.SIDEBAR_BOTTOM
    SIDEBAR_GLOW = Colors.SIDEBAR_GLOW
    SIDEBAR_MID = Colors.SIDEBAR_MID
    SIDEBAR_TOP = Colors.SIDEBAR_TOP
    SUCCESS = Colors.SUCCESS
    SUCCESS_10 = Colors.SUCCESS_10
    SUCCESS_LIGHT = Colors.SUCCESS_LIGHT
    TEXT_DISABLED = Colors.TEXT_DISABLED
    TEXT_INVERSE = Colors.TEXT_INVERSE
    TEXT_MUTED = Colors.TEXT_MUTED
    TEXT_PRIMARY = Colors.TEXT_PRIMARY
    TEXT_SECONDARY = Colors.TEXT_SECONDARY
    WARNING = Colors.WARNING
    WARNING_LIGHT = Colors.WARNING_LIGHT


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


# ═══════════════════════════════════════════════════════════════════
# Theme mode (Phase 3) — runtime theme switching
# ═══════════════════════════════════════════════════════════════════


# Currently active palette source. "light" or "dark".
_THEME_MODE: str = "light"


def get_theme_mode() -> str:
    """Return the active theme mode (``"light"`` / ``"dark"``)."""
    return _THEME_MODE


def _set_c_from_palette(palette) -> None:
    """Rebind every colour token on :class:`_C` to the values in ``palette``.

    Called by :func:`set_theme_mode`. Operates on ``_C.__dict__`` so
    existing references like ``_C.BG_BASE`` pick up the new value
    without code that uses them needing to be re-imported.
    """
    for name in (
        "ACCENT",
        "ACCENT_DARK",
        "ACCENT_LIGHT",
        "ACCENT_NORMAL",
        "ACCENT_SUBTLE",
        "BG_BASE",
        "BG_ELEVATED",
        "BG_INPUT",
        "BG_OVERLAY",
        "BG_SURFACE",
        "BORDER_DEFAULT",
        "BORDER_FOCUS",
        "BORDER_STRONG",
        "BORDER_SUBTLE",
        "ERROR",
        "ERROR_10",
        "ERROR_LIGHT",
        "INFO",
        "PRIMARY",
        "PRIMARY_10",
        "PRIMARY_DARK",
        "PRIMARY_DARKER",
        "PRIMARY_DARKEST",
        "PRIMARY_LIGHT",
        "PRIMARY_LIGHTER",
        "PRIMARY_LIGHTEST",
        "PRIMARY_NORMAL",
        "SIDEBAR_BOTTOM",
        "SIDEBAR_GLOW",
        "SIDEBAR_MID",
        "SIDEBAR_TOP",
        "SUCCESS",
        "SUCCESS_10",
        "SUCCESS_LIGHT",
        "TEXT_DISABLED",
        "TEXT_INVERSE",
        "TEXT_MUTED",
        "TEXT_PRIMARY",
        "TEXT_SECONDARY",
        "WARNING",
        "WARNING_LIGHT",
    ):
        setattr(_C, name, getattr(palette, name))


def set_theme_mode(mode: str) -> str:
    """Switch the global theme palette. Idempotent.

    Parameters
    ----------
    mode : str
        Either ``"light"`` (use :class:`Colors`) or ``"dark"`` (use
        :class:`DarkColors`).

    Returns
    -------
    str
        The mode that ended up being applied. Unknown values fall
        back to ``"light"`` and the palette is reset to :class:`Colors`.
    """
    global _THEME_MODE
    if mode == "dark":
        _set_c_from_palette(DarkColors)
        _THEME_MODE = "dark"
    else:
        _set_c_from_palette(Colors)
        _THEME_MODE = "light"
    return _THEME_MODE


__all__ = [
    "Colors",
    "DarkColors",
    "FontSizes",
    "FontWeights",
    "Spacing",
    "Radii",
    "Shadows",
    "Durations",
    "Easings",
    "QSSComponents",
    "_C",
    "set_theme_mode",
    "get_theme_mode",
]
