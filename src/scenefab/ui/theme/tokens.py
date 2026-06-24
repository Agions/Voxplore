#!/usr/bin/env python3

"""
Runtime theme tokens — compatibility layer.

All values are derived from ds_tokens.py (the authoritative design token source).
Public names are kept stable for existing theme manager code.
"""

from .ds_tokens import Colors, FontSizes, Radii, Shadows

# ── Dark / Light palette dicts (used by ThemeManager) ─────────────

DARK_TOKENS = {
    "primary": "#0891b2",
    "primary-hover": "#06b6d4",
    "primary-pressed": "#0e7490",
    "primary-subtle": Colors.PRIMARY_DARKEST,
    "bg-base": "#0b1120",
    "bg-surface": "#111827",
    "bg-elevated": "#182235",
    "bg-overlay": "#1f2c43",
    "border": "#334155",
    "border-default": "#334155",
    "border-subtle": "#253247",
    "border-strong": Colors.BORDER_STRONG,
    "text-primary": "#e5edf6",
    "text-secondary": "#cbd5e1",
    "text-muted": "#91a4ba",
    "text-disabled": "#64748b",
    "success": Colors.SUCCESS,
    "success-subtle": "#163923",
    "warning": Colors.WARNING,
    "warning-subtle": "#422d12",
    "error": Colors.ERROR,
    "error-subtle": "#4c1d2f",
    "info": "#22d3ee",
    "accent": Colors.ACCENT,
    "accent-hover": Colors.ACCENT_NORMAL,
    "accent-subtle": "#4c1d2f",
}

LIGHT_TOKENS = {
    "primary": Colors.PRIMARY,
    "primary-hover": Colors.PRIMARY_DARK,
    "primary-pressed": Colors.PRIMARY_DARKER,
    "primary-subtle": Colors.PRIMARY_LIGHTEST,
    "bg-base": Colors.BG_BASE,
    "bg-surface": Colors.BG_SURFACE,
    "bg-elevated": Colors.BG_ELEVATED,
    "bg-overlay": Colors.BG_OVERLAY,
    "border": Colors.BORDER_DEFAULT,
    "border-default": Colors.BORDER_DEFAULT,
    "border-subtle": Colors.BORDER_SUBTLE,
    "border-strong": Colors.BORDER_STRONG,
    "text-primary": Colors.TEXT_PRIMARY,
    "text-secondary": Colors.TEXT_SECONDARY,
    "text-muted": Colors.TEXT_MUTED,
    "text-disabled": Colors.TEXT_DISABLED,
    "success": "#16a34a",
    "success-subtle": Colors.SUCCESS_LIGHT,
    "warning": "#d97706",
    "warning-subtle": Colors.WARNING_LIGHT,
    "error": Colors.ERROR,
    "error-subtle": Colors.ERROR_LIGHT,
    "info": Colors.PRIMARY,
    "accent": Colors.ACCENT,
    "accent-hover": Colors.ACCENT_DARK,
    "accent-subtle": Colors.ACCENT_LIGHT,
}

COLORS = LIGHT_TOKENS

# ── Spacing / Radius / Font / Shadow / Transition (dict form) ─────

SPACING = {
    "xs": f"{Radii.sm}px",
    "sm": "8px",
    "md": f"{Radii.base}px",
    "lg": "24px",
    "xl": "32px",
    "2xl": "48px",
}

RADIUS = {
    "sm": f"{Radii.sm}px",
    "md": "7px",
    "lg": f"{Radii.base}px",
    "xl": f"{Radii.lg}px",
    "full": f"{Radii.full}px",
}

FONT = {
    "family": (
        "system-ui, -apple-system, 'Segoe UI', 'Microsoft YaHei', "
        "'PingFang SC', 'Hiragino Sans GB', Arial, sans-serif"
    ),
    "mono": "'JetBrains Mono', 'SF Mono', Consolas, monospace",
    "size": {
        "xs": f"{FontSizes.xs}px",
        "sm": f"{FontSizes.sm}px",
        "md": f"{FontSizes.md}px",
        "lg": f"{FontSizes.lg}px",
        "xl": f"{FontSizes.xl}px",
        "2xl": f"{FontSizes.xxl}px",
        "3xl": f"{FontSizes.xxxl}px",
    },
}

SHADOW = {
    "sm": Shadows.SM,
    "md": Shadows.MD,
    "lg": Shadows.LG,
}

TRANSITION = {
    "fast": "120ms ease",
    "normal": "200ms ease",
    "slow": "300ms ease",
}
