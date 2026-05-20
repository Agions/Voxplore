#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Voxplore Design System Tokens v2
统一的色彩、字体、间距、圆角规范
"""

from PySide6.QtGui import QColor

# ═══════════════════════════════════════════════════════════
# 色彩系统
# ═══════════════════════════════════════════════════════════

class Colors:
    """主色彩体系 - 午夜蓝+极光紫双主色"""

    # 背景层（由深到浅）
    BG_BASE     = "#0D0F14"   # 最深背景
    BG_SURFACE  = "#151821"   # 卡片/面板
    BG_ELEVATED = "#1C2030"   # 悬浮/高亮层
    BG_OVERLAY  = "#242838"   # 模态/下拉

    # 边框
    BORDER_SUBTLE = "#2A2F42"
    BORDER_DEFAULT = "#363C52"
    BORDER_STRONG  = "#4A5270"

    # 主色调 - 极光紫
    PRIMARY_50  = "#F5F3FF"
    PRIMARY_100 = "#EDE9FE"
    PRIMARY_200 = "#DDD6FE"
    PRIMARY_300 = "#C4B5FD"
    PRIMARY_400 = "#A78BFA"
    PRIMARY_500 = "#8B5CF6"   # 主色
    PRIMARY_600 = "#7C3AED"
    PRIMARY_700 = "#6D28D9"
    PRIMARY_800 = "#5B21B6"
    PRIMARY_900 = "#4C1D95"

    # 辅助色 - 冰蓝
    ACCENT_50   = "#F0F9FF"
    ACCENT_100  = "#E0F2FE"
    ACCENT_400  = "#38BDF8"
    ACCENT_500  = "#0EA5E9"   # 辅助主色
    ACCENT_600  = "#0284C7"

    # 功能色
    SUCCESS     = "#10B981"
    WARNING     = "#F59E0B"
    ERROR       = "#EF4444"
    INFO        = "#6366F1"

    # 文字层
    TEXT_PRIMARY   = "#F1F5F9"   # 主要文字
    TEXT_SECONDARY = "#94A3B8"  # 次要文字
    TEXT_MUTED     = "#64748B"   # 弱化文字
    TEXT_DISABLED  = "#475569"  # 禁用文字

    # 侧边栏渐变（紫色系）
    SIDEBAR_BG_TOP    = "#13111C"
    SIDEBAR_BG_MID    = "#0F0D16"
    SIDEBAR_BG_BOTTOM = "#0A0910"
    SIDEBAR_GLOW      = "#7C3AED"

    # 工具栏
    TOOLBAR_BG = "qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #1C2030,stop:1 #151821)"
    TOOLBAR_BORDER = "#2A2F42"


# ═══════════════════════════════════════════════════════════
# 字体系统
# ═══════════════════════════════════════════════════════════

class FontSizes:
    """字体尺寸规范"""
    xs   = 11
    sm   = 12
    base = 13
    md   = 14
    lg   = 16
    xl   = 18
    xxl  = 22
    xxxl = 28


class FontWeights:
    """字体权重"""
    Regular  = 400
    Medium   = 500
    Semibold = 600
    Bold     = 700


# ═══════════════════════════════════════════════════════════
# 间距系统（基于 4px 单位）
# ═══════════════════════════════════════════════════════════

class Spacing:
    """间距规范（4px 基准）"""
    xxs  = 4
    xs   = 8
    sm   = 10
    md   = 12
    base = 16
    lg   = 20
    xl   = 24
    xxl  = 32
    xxxl = 48


# ═══════════════════════════════════════════════════════════
# 圆角系统
# ═══════════════════════════════════════════════════════════

class Radii:
    """圆角规范"""
    none  = 0
    sm    = 4
    base  = 8
    md    = 10
    lg    = 12
    xl    = 16
    full  = 9999


# ═══════════════════════════════════════════════════════════
# 阴影系统
# ═══════════════════════════════════════════════════════════

class Shadows:
    """阴影规范"""
    NONE = "none"

    SM = ("0 1px 2px rgba(0,0,0,0.3), 0 1px 3px rgba(0,0,0,0.2)",
          "0 1px 2px rgba(0,0,0,0.25)")

    BASE = ("0 4px 6px rgba(0,0,0,0.35), 0 2px 4px rgba(0,0,0,0.25)",
            "0 4px 8px rgba(0,0,0,0.3)")

    MD = ("0 10px 15px rgba(0,0,0,0.4), 0 4px 6px rgba(0,0,0,0.3)",
          "0 10px 20px rgba(0,0,0,0.35)")

    LG = ("0 20px 25px rgba(0,0,0,0.45), 0 8px 10px rgba(0,0,0,0.3)",
          "0 20px 30px rgba(0,0,0,0.4)")

    XL = ("0 25px 50px rgba(0,0,0,0.5)",
          "0 30px 60px rgba(0,0,0,0.45)")

    GLOW_PURPLE = ("0 0 20px rgba(139, 92, 246, 0.3)",
                   "0 0 40px rgba(139, 92, 246, 0.15)")

    GLOW_ACCENT = ("0 0 20px rgba(14, 165, 233, 0.3)",
                   "0 0 40px rgba(14, 165, 233, 0.15)")


# ═══════════════════════════════════════════════════════════
# 动效规范
# ═══════════════════════════════════════════════════════════

class Durations:
    """动画时长"""
    instant = 50
    fast    = 100
    normal  = 200
    slow    = 300
    xslow   = 500


class Easings:
    """缓动曲线"""
    standard   = "cubic-bezier(0.4, 0, 0.2, 1)"
    decelerate = "cubic-bezier(0, 0, 0.2, 1)"
    accelerate = "cubic-bezier(0.4, 0, 1, 1)"
    spring     = "cubic-bezier(0.175, 0.885, 0.32, 1.275)"
