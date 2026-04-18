#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Voxplore Design Tokens — OKLCH 感知均匀色彩系统
Frontend Design Pro 规范 · 2026-04-10

OKLCH 优势：
- 感知均匀（相同数值变化 = 相同视觉变化）
- 亮度和色相解耦，便于调整
- 支持 Chrome、Psykhe、Safari 15.4+

使用方式（QSS 示例）：
    color: var(--color-primary);
    background: var(--color-bg-base);
"""

# ─── 色相常量 ────────────────────────────────────────────────
_H = 250  # 主蓝色相（度）

# ─── 色彩 Tokens ────────────────────────────────────────────
COLORS = {
    # ── 主色 Primary ──
    # OKLCH: L(亮度) C(色度) H(色相)
    "primary":          "oklch(0.65 0.20 250)",   # #388BFD — 主操作蓝
    "primary-hover":    "oklch(0.70 0.24 250)",   # 悬停增亮
    "primary-pressed":  "oklch(0.55 0.18 250)",   # 按下略暗
    "primary-subtle":   "oklch(0.70 0.12 250)",   # 浅色背景

    # ── 背景 Background ──
    # 暗色模式：#0f0f0f 改为带色调的深色，避免纯黑
    "bg-base":          "oklch(0.13 0.01 250)",   # #121212 — 最深背景
    "bg-surface":       "oklch(0.16 0.01 250)",   # #1a1a1a — 卡片/面板
    "bg-elevated":      "oklch(0.19 0.01 250)",   # #1f1f1f — 悬浮元素
    "bg-overlay":       "oklch(0.22 0.01 250)",   # #252525 — 遮罩层

    # ── 边框 Border ──
    "border-default":   "oklch(0.24 0.01 250)",   # #2e2e2e — 默认边框
    "border-subtle":    "oklch(0.19 0.01 250)",   # #222 — 弱边框
    "border-strong":    "oklch(0.32 0.01 250)",   # #404040 — 强调边框

    # ── 文字 Text ──
    # 层次从高到低：primary > secondary > muted > disabled
    "text-primary":     "oklch(0.93 0.01 250)",   # #e8e8e8 — 主要文字
    "text-secondary":   "oklch(0.75 0.01 250)",   # #a8a8a8 — 次要文字
    "text-muted":       "oklch(0.55 0.01 250)",   # #787878 — 辅助文字
    "text-disabled":    "oklch(0.40 0.01 250)",   # #555 — 禁用文字

    # ── 功能色 Functional ──
    "success":          "oklch(0.65 0.22 145)",   # #2EA043 — 成功
    "success-subtle":   "oklch(0.70 0.14 145)",   # 成功浅色
    "warning":          "oklch(0.75 0.20 85)",    # #D29922 — 警告
    "warning-subtle":   "oklch(0.78 0.14 85)",    # 警告浅色
    "error":            "oklch(0.63 0.24 25)",    # #DA3633 — 错误
    "error-subtle":     "oklch(0.67 0.16 25)",    # 错误浅色
    "info":             "oklch(0.65 0.20 250)",   # 同 primary

    # ── 强调色 Accent ──
    "accent":           "oklch(0.70 0.18 300)",   # #A371F7 — 紫色强调
    "accent-subtle":    "oklch(0.75 0.12 300)",   # 强调浅色

    # ── 进度/交互 Progress ──
    "progress-track":   "oklch(0.20 0.01 250)",   # 进度条轨道
    "focus-ring":       "oklch(0.65 0.20 250)",   # 焦点环（与 primary 同色）
}


# ─── 暗色模式专用（仅暗色模式时使用）────────────────────
DARK_TOKENS = {
    "bg-base":          "oklch(0.13 0.01 250)",
    "bg-surface":       "oklch(0.16 0.01 250)",
    "bg-elevated":      "oklch(0.19 0.01 250)",
    "text-primary":     "oklch(0.93 0.01 250)",
    "text-secondary":   "oklch(0.75 0.01 250)",
}


# ─── 亮色模式专用（预留）────────────────────────────────
LIGHT_TOKENS = {
    "bg-base":          "oklch(0.97 0.00 250)",
    "bg-surface":       "oklch(0.95 0.00 250)",
    "bg-elevated":      "oklch(0.99 0.00 250)",
    "text-primary":     "oklch(0.15 0.01 250)",
    "text-secondary":   "oklch(0.40 0.01 250)",
}


# ─── 字体 Typography ───────────────────────────────────────
# frontend-design-pro 规范：选有个性的字体，避免 Arial/Inter/system-ui
FONTS = {
    # 展示/标题字体
    "font-display": (
        '"SF Pro Display", "Inter var", "Geist", "DM Sans", '
        '"Sora", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    ),
    # 正文字体
    "font-body": (
        '"SF Pro Text", "Inter var", "Geist", "DM Sans", '
        '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
    ),
    # 等宽字体
    "font-mono": (
        '"SF Mono", "JetBrains Mono", "Fira Code", "Consolas", monospace'
    ),
}

# Modular Scale: 1.25 (Major Third)
# 基准: 14px
FONT_SIZES = {
    "xs":   "11px",
    "sm":   "12px",
    "base": "14px",
    "md":   "14px",
    "lg":   "16px",
    "xl":   "18px",
    "2xl":  "20px",
    "3xl":  "24px",
    "4xl":  "30px",
    "5xl":  "36px",
}

# 字重
FONT_WEIGHTS = {
    "regular":  400,
    "medium":   500,
    "semibold": 600,
    "bold":     700,
}


# ─── 间距 Spatial ─────────────────────────────────────────
# 4px 基础网格系统
SPACING = {
    "0":   "0px",
    "px":  "1px",
    "0.5": "2px",
    "1":   "4px",
    "2":   "8px",
    "3":   "12px",
    "4":   "16px",
    "5":   "20px",
    "6":   "24px",
    "8":   "32px",
    "10":  "40px",
    "12":  "48px",
    "16":  "64px",
    "20":  "80px",
}

# 内容宽度限制（frontend-design-pro 规范）
WIDTHS = {
    "content":  "65ch",     # 正文最大宽度
    "prose":    "60ch",     # 文章内容
    "wide":     "1280px",   # 宽容器上限
    "full":     "100%",
}


# ─── 圆角 Border Radius ──────────────────────────────────
BORDER_RADIUS = {
    "none":  "0px",
    "sm":   "4px",
    "md":   "8px",
    "lg":   "12px",
    "xl":   "16px",
    "2xl":  "24px",
    "full": "9999px",
}


# ─── 阴影 Shadows ─────────────────────────────────────────
SHADOWS = {
    "sm":   "0 1px 2px oklch(0.00 0.00 0.00 / 0.20)",
    "md":   "0 4px 12px oklch(0.00 0.00 0.00 / 0.30)",
    "lg":   "0 8px 24px oklch(0.00 0.00 0.00 / 0.40)",
    "xl":   "0 16px 48px oklch(0.00 0.00 0.00 / 0.50)",
    # 彩色阴影（配合主色发光效果）
    "glow-primary":  "0 0 20px oklch(0.65 0.20 250 / 0.35)",
    "glow-accent":   "0 0 20px oklch(0.70 0.18 300 / 0.35)",
}


# ─── 动效 Motion ──────────────────────────────────────────
# frontend-design-pro 规范：OutCubic 缓动，拒绝 bounce/elastic
EASING = {
    # 标准曲线
    "ease-out":     "cubic-bezier(0.16, 1, 0.3, 1)",   # OutCubic — 快入慢出（推荐）
    "ease-in":      "cubic-bezier(0.7, 0, 0.84, 0)",    # InCubic
    "ease-in-out":  "cubic-bezier(0.65, 0, 0.35, 1)",  # 标准缓入缓出
    # 特殊曲线
    "spring":       "cubic-bezier(0.34, 1.56, 0.64, 1)", # 轻微弹性（克制使用）
    "snappy":       "cubic-bezier(0.25, 0.46, 0.45, 0.94)", # 快速弹跳
}

# 时长（ms）
DURATIONS = {
    "instant":  "50ms",     # 极快（hover 反馈）
    "fast":     "100ms",    # 快（按钮状态切换）
    "normal":   "200ms",    # 标准（展开/收起）
    "slow":     "300ms",    # 慢（页面过渡）
    "slower":   "400ms",    # 更慢（大型模态框）
    "page":     "500ms",    # 页面级切换
}

# 禁用动画（prefers-reduced-motion）
REDUCED_MOTION = {
    "easing":  "ease-out",
    "duration": "1ms",
}


# ─── Z-Index 层级 ─────────────────────────────────────────
Z_INDEX = {
    "base":      "0",
    "dropdown":  "100",
    "sticky":   "200",
    "overlay":  "300",
    "modal":    "400",
    "toast":    "500",
    "tooltip":  "600",
}


# ─── 快捷生成 CSS 变量字符串 ─────────────────────────────
def generate_css_variables(mode: str = "dark") -> str:
    """生成 QSS 可用的 CSS 变量声明"""
    tokens = DARK_TOKENS if mode == "dark" else LIGHT_TOKENS

    lines = [":root {"]
    for key, value in COLORS.items():
        if key in tokens:
            lines.append(f"    --color-{key}: {value};")
        elif not key.startswith("_"):  # 跳过私有 key
            lines.append(f"    --color-{key}: {value};")
    lines.append("}")

    # 字体
    lines.append("")
    lines.append(":root {")
    for key, value in FONTS.items():
        lines.append(f"    --font-{key}: {value};")
    for key, value in FONT_SIZES.items():
        lines.append(f"    --text-{key}: {value};")
    lines.append("}")

    # 间距
    lines.append("")
    lines.append(":root {")
    for key, value in SPACING.items():
        lines.append(f"    --space-{key}: {value};")
    lines.append("}")

    # 圆角
    lines.append("")
    lines.append(":root {")
    for key, value in BORDER_RADIUS.items():
        lines.append(f"    --radius-{key}: {value};")
    lines.append("}")

    # 阴影
    lines.append("")
    lines.append(":root {")
    for key, value in SHADOWS.items():
        lines.append(f"    --shadow-{key}: {value};")
    lines.append("}")

    # 动效
    lines.append("")
    lines.append(":root {")
    for key, value in EASING.items():
        lines.append(f"    --ease-{key}: {value};")
    for key, value in DURATIONS.items():
        lines.append(f"    --duration-{key}: {value};")
    lines.append("}")

    return "\n".join(lines)
