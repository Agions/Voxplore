#!/usr/bin/env python3

"""Shared Qt-compatible UI styles."""


class ColorPalette:
    """Qt-compatible color tokens."""

    # --- Primary ---
    PRIMARY = "#0A84FF"  # 主强调色
    PRIMARY_LIGHT = "#2196FF"  # 主色悬停
    PRIMARY_DARK = "#0070E0"  # 主色按下

    # --- Status ---
    SUCCESS = "#10B981"
    WARNING = "#F59E0B"
    ERROR = "#EF4444"
    INFO = "#3B82F6"

    # --- Neutral — all tinted, no pure gray ---
    # Background
    BG_BASE = "#0C1018"
    BG_RAISED = "#0E1520"
    BG_SUNKEN = "#0A0E16"
    BG_OVERLAY = "#111827"  # hover state

    # Border
    BORDER_SUBTLE = "#141E2E"
    BORDER_DEFAULT = "#1A2332"
    BORDER_STRONG = "#2A3A50"

    # Text
    TEXT_PRIMARY = "#E2E8F0"
    TEXT_SECONDARY = "#8098B0"
    TEXT_MUTED = "#4A5A70"
    TEXT_DISABLED = "#3A4A60"

    # Accent tints
    TINT_IDLE = "#1E2D42"  # idle state
    TINT_RUNNING = "#0A1028"  # running/highlight state


class Spacing:
    """
    间距系统 — 4px 基础模数
    REDESIGN: 规范化间距，避免随意数字
    """

    XS = "4px"  # 微间距（图标内填充）
    SM = "8px"  # 小间距（标签与内容）
    MD = "12px"  # 组件内间距
    LG = "16px"  # 标准间距
    XL = "24px"  # 区块间距
    XXL = "32px"  # 大区块间距
    XXL_PLUS = "48px"  # 页面边距


class Radius:
    """
    圆角系统 — 分级设计
    """

    SM = "6px"  # 复选框、标签
    MD = "10px"  # 按钮、输入框
    LG = "14px"  # 卡片、面板
    XL = "20px"  # 拖放区、模态
    FULL = "9999px"  # 全圆（头像、徽章）


class ButtonStyles:
    """
    按钮样式 token

    REDESIGN:
    - PRIMARY: solid fill → hover scale + glow
    - SECONDARY: transparent + border → hover border-color brightens
    - 所有颜色引用 ColorPalette
    """

    # Primary — solid fill
    PRIMARY = f"""
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {ColorPalette.PRIMARY},
            stop:1 {ColorPalette.PRIMARY_LIGHT});
        color: #FFFFFF;
        border: none;
        border-radius: {Radius.MD};
        padding: 14px 28px;
        font-weight: 600;
        font-size: 14px;
    """
    PRIMARY_HOVER = f"""
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {ColorPalette.PRIMARY_LIGHT},
            stop:1 {ColorPalette.PRIMARY});
        border: none;
        border-radius: {Radius.MD};
        padding: 14px 28px;
        font-weight: 600;
        font-size: 14px;
    """

    # Secondary — transparent + border
    SECONDARY = f"""
        background: transparent;
        color: {ColorPalette.TEXT_SECONDARY};
        border: 1px solid {ColorPalette.BORDER_DEFAULT};
        border-radius: {Radius.MD};
        padding: 10px 20px;
        font-weight: 500;
        font-size: 13px;
    """
    SECONDARY_HOVER = f"""
        background: {ColorPalette.BG_BASE};
        color: {ColorPalette.TEXT_PRIMARY};
        border: 1px solid {ColorPalette.PRIMARY};
        border-radius: {Radius.MD};
        padding: 10px 20px;
        font-weight: 500;
        font-size: 13px;
    """


class CardStyles:
    """
    卡片样式 token

    REDESIGN:
    - DEFAULT: subtle gradient + soft border
    - HOVER: stronger border
    - GLASS: translucent panel
    """

    DEFAULT = f"""
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 {ColorPalette.BG_RAISED},
            stop:1 #111827);
        border: 1px solid {ColorPalette.BORDER_SUBTLE};
        border-radius: {Radius.LG};
        padding: 20px;
    """

    HOVER = f"""
        border-color: {ColorPalette.PRIMARY};
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 {ColorPalette.BG_RAISED},
            stop:1 #131C2C);
    """

    GLASS = f"""
        background: rgba(14, 21, 32, 0.80);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: {Radius.LG};
        padding: 24px;
    """


class InputStyles:
    """
    输入框样式 token

    REDESIGN:
    - FOCUS: border → primary color
    - Placeholder: TEXT_DISABLED
    """

    DEFAULT = f"""
        background: {ColorPalette.BG_SUNKEN};
        color: {ColorPalette.TEXT_PRIMARY};
        border: 1px solid {ColorPalette.BORDER_DEFAULT};
        border-radius: {Radius.MD};
        padding: 10px 14px;
        font-size: 13px;
        selection-background-color: {ColorPalette.PRIMARY};
    """

    FOCUS = f"""
        border-color: {ColorPalette.PRIMARY};
        background: {ColorPalette.BG_SUNKEN};
    """

    PLACEHOLDER = f"""
        color: {ColorPalette.TEXT_DISABLED};
    """


# ========================================================================
# Public helpers
# ========================================================================


def get_button_styles(button_type: str = "primary") -> str:
    """获取按钮样式字符串"""
    styles = {
        "primary": ButtonStyles.PRIMARY,
        "secondary": ButtonStyles.SECONDARY,
    }
    base = styles.get(button_type, ButtonStyles.PRIMARY)
    return base


def get_card_styles(card_type: str = "default") -> str:
    """获取卡片样式字符串"""
    styles = {
        "default": CardStyles.DEFAULT,
        "hover": CardStyles.HOVER,
        "glass": CardStyles.GLASS,
    }
    return styles.get(card_type, CardStyles.DEFAULT)
