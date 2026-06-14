#!/usr/bin/env python3

"""
Design tokens used by generated Qt styles.

The values mirror the resource QSS palette and intentionally use plain HEX or
RGBA strings because Qt style sheets do not support modern CSS color functions.
"""


# ─── Resource-aligned color system ─────────────────────────
class Colors:
    """Color tokens shared by generated component styles."""

    # ── 主色 Primary ──
    Primary = "#0891b2"
    PrimaryHover = "#06b6d4"
    PrimaryPressed = "#0e7490"
    PrimarySubtle = "#164e63"

    # ── 背景 Background（暗色模式）─
    BgBase = "#0b1120"
    BgSurface = "#111827"
    BgElevated = "#182235"
    BgOverlay = "#1f2c43"

    # ── 边框 Border ──
    BorderDefault = "#334155"
    BorderSubtle = "#253247"
    BorderStrong = "#38bdf8"

    # ── 文字 Text ──
    TextPrimary = "#e5edf6"
    TextSecondary = "#cbd5e1"
    TextMuted = "#91a4ba"
    TextDisabled = "#64748b"

    # ── 功能色 Functional ──
    Success = "#22c55e"
    SuccessSubtle = "#163923"
    Warning = "#f59e0b"
    WarningSubtle = "#422d12"
    Error = "#e11d48"
    ErrorSubtle = "#fb7185"
    Info = "#22d3ee"

    # ── 强调色 Accent ──
    Accent = "#f43f5e"
    AccentSubtle = "#4c1d2f"

    # ── 进度/交互 ──
    ProgressTrack = "#253247"
    FocusRing = "#38bdf8"

    # ── Compatibility aliases for older callers ─────────────
    _HEX_FALLBACK = {
        "primary": Primary,
        "bg_base": BgBase,
        "text_primary": TextPrimary,
        "border_default": BorderDefault,
        "success": Success,
        "warning": Warning,
        "error": Error,
    }


# ── 颜色常量本地引用 (mypy f-string bug) ──
_C = Colors


# ─── 圆角系统 ────────────────────────────────────────────
class Radius:
    """圆角 tokens"""

    none = "0px"
    sm = "4px"
    md = "6px"
    lg = "8px"
    xl = "12px"
    full = "9999px"


# ─── 字体系统 ──────────────────────────────────────────────
class Fonts:
    """Font tokens."""

    Display = (
        '"SF Pro Display", "Inter var", "Geist", "DM Sans", '
        '"Sora", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    )
    Body = (
        '"SF Pro Text", "Inter var", "Geist", "DM Sans", '
        '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    )
    Mono = '"SF Mono", "JetBrains Mono", "Fira Code", "Consolas", monospace'


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
    OutCubic = "cubic-bezier(0.16, 1, 0.3, 1)"  # 标准快入慢出
    InCubic = "cubic-bezier(0.7, 0, 0.84, 0)"  # 慢入快出
    InOut = "cubic-bezier(0.65, 0, 0.35, 1)"  # 缓入缓出
    Spring = "cubic-bezier(0.16, 1, 0.3, 1)"

    # 时长
    Instant = "50ms"  # 极快（hover 反馈）
    Fast = "100ms"  # 快（按钮状态）
    Normal = "200ms"  # 标准（展开/收起）
    Slow = "300ms"  # 慢（页面过渡）
    Slower = "400ms"  # 更慢（大型模态）
    Page = "500ms"  # 页面级切换


# ─── 阴影系统 ──────────────────────────────────────────────
class Shadows:
    sm = "0 1px 2px rgba(0,0,0,0.24)"
    md = "0 4px 12px rgba(0,0,0,0.30)"
    lg = "0 8px 24px rgba(0,0,0,0.38)"
    xl = "0 16px 48px rgba(0,0,0,0.46)"
    GlowPrimary = "0 0 20px rgba(34,211,238,0.28)"
    GlowAccent = "0 0 20px rgba(244,63,94,0.26)"


__all__ = ["Colors", "Radius", "Fonts", "Motion", "Shadows"]
