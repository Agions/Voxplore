#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Voxplore Design Tokens — OKLCH 感知均匀色彩系统
纯暗色简约科技风 · 2026-04-22

OKLCH 优势：
- 感知均匀（相同数值变化 = 相同视觉变化）
- 亮度和色相解耦，便于调整
- 支持 Chrome、Safari 15.4+

使用方式（QSS 示例）：
    color: var(--color-primary);
    background: var(--color-bg-base);
"""

# ─── 色彩 Tokens ────────────────────────────────────────────
COLORS = {
    # ── 主色 Primary ──
    "primary":         "oklch(0.70 0.22 250)",   # 主操作蓝
    "primary-hover":   "oklch(0.75 0.26 250)",
    "primary-pressed": "oklch(0.60 0.18 250)",
    "primary-subtle":  "oklch(0.22 0.04 250)",   # 浅色背景

    # ── 背景 Background ──
    "bg-base":         "oklch(0.08 0.00 0)",    # 最深背景
    "bg-surface":      "oklch(0.11 0.00 0)",    # 卡片/面板
    "bg-elevated":     "oklch(0.14 0.00 0)",    # 悬浮/弹窗
    "bg-overlay":      "oklch(0.18 0.00 0)",    # 遮罩

    # ── 边框 Border ──
    "border":          "oklch(0.20 0.00 0)",    # 默认边框
    "border-subtle":   "oklch(0.15 0.00 0)",    # 弱边框
    "border-strong":   "oklch(0.28 0.00 0)",    # 强调边框

    # ── 文字 Text ──
    "text-primary":    "oklch(0.95 0.00 0)",    # 主要文字
    "text-secondary":  "oklch(0.65 0.00 0)",    # 次要文字
    "text-muted":      "oklch(0.45 0.00 0)",    # 辅助文字
    "text-disabled":   "oklch(0.30 0.00 0)",    # 禁用

    # ── 功能色 Functional ──
    "success":         "oklch(0.72 0.18 145)",
    "success-subtle":  "oklch(0.25 0.05 145)",
    "warning":         "oklch(0.78 0.18 85)",
    "warning-subtle":  "oklch(0.26 0.05 85)",
    "error":           "oklch(0.68 0.22 25)",
    "error-subtle":    "oklch(0.25 0.06 25)",

    # ── 强调色 Accent ──
    "accent":          "oklch(0.72 0.20 285)",   # 紫色
    "accent-hover":    "oklch(0.78 0.24 285)",
    "accent-subtle":   "oklch(0.25 0.06 285)",
}


# ─── 间距 Spatial ─────────────────────────────────────────
SPACING = {
    "xs":  "4px",
    "sm":  "8px",
    "md":  "16px",
    "lg":  "24px",
    "xl":  "32px",
    "2xl": "48px",
}


# ─── 圆角 Border Radius ────────────────────────────────────
RADIUS = {
    "sm":   "4px",
    "md":   "8px",
    "lg":   "12px",
    "xl":   "16px",
    "full": "9999px",
}


# ─── 字体 Typography ───────────────────────────────────────
FONT = {
    "family": "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    "mono": "'JetBrains Mono', 'SF Mono', Consolas, monospace",
    "size": {
        "xs":  "11px",
        "sm":  "13px",
        "md":  "14px",
        "lg":  "16px",
        "xl":  "20px",
        "2xl": "24px",
        "3xl": "32px",
    }
}


# ─── 阴影 Shadows ─────────────────────────────────────────
SHADOW = {
    "sm": "0 1px 2px rgba(0,0,0,0.4)",
    "md": "0 2px 8px rgba(0,0,0,0.5)",
    "lg": "0 4px 16px rgba(0,0,0,0.6)",
}


# ─── 动效 Motion ──────────────────────────────────────────
TRANSITION = {
    "fast":   "120ms ease",
    "normal": "200ms ease",
    "slow":   "300ms ease",
}
