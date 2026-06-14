#!/usr/bin/env python3

"""
Runtime theme tokens aligned with resources/styles.

Qt style sheets require conservative color syntax, so all runtime tokens use
plain HEX values. Public names are kept stable for existing theme manager code.
"""

DARK_TOKENS = {
    "primary": "#0891b2",
    "primary-hover": "#06b6d4",
    "primary-pressed": "#0e7490",
    "primary-subtle": "#164e63",
    "bg-base": "#0b1120",
    "bg-surface": "#111827",
    "bg-elevated": "#182235",
    "bg-overlay": "#1f2c43",
    "border": "#334155",
    "border-default": "#334155",
    "border-subtle": "#253247",
    "border-strong": "#38bdf8",
    "text-primary": "#e5edf6",
    "text-secondary": "#cbd5e1",
    "text-muted": "#91a4ba",
    "text-disabled": "#64748b",
    "success": "#22c55e",
    "success-subtle": "#163923",
    "warning": "#f59e0b",
    "warning-subtle": "#422d12",
    "error": "#e11d48",
    "error-subtle": "#4c1d2f",
    "info": "#22d3ee",
    "accent": "#f43f5e",
    "accent-hover": "#fb7185",
    "accent-subtle": "#4c1d2f",
}

LIGHT_TOKENS = {
    "primary": "#0891b2",
    "primary-hover": "#0e7490",
    "primary-pressed": "#155e75",
    "primary-subtle": "#e0f7fb",
    "bg-base": "#f6f8fb",
    "bg-surface": "#ffffff",
    "bg-elevated": "#f1f5f9",
    "bg-overlay": "#e2e8f0",
    "border": "#cbd5e1",
    "border-default": "#cbd5e1",
    "border-subtle": "#dbe3ee",
    "border-strong": "#0891b2",
    "text-primary": "#182235",
    "text-secondary": "#334155",
    "text-muted": "#64748b",
    "text-disabled": "#94a3b8",
    "success": "#16a34a",
    "success-subtle": "#dcfce7",
    "warning": "#d97706",
    "warning-subtle": "#fef3c7",
    "error": "#e11d48",
    "error-subtle": "#ffe4e6",
    "info": "#0891b2",
    "accent": "#f43f5e",
    "accent-hover": "#be123c",
    "accent-subtle": "#ffe4e6",
}

COLORS = DARK_TOKENS

SPACING = {
    "xs": "4px",
    "sm": "8px",
    "md": "16px",
    "lg": "24px",
    "xl": "32px",
    "2xl": "48px",
}

RADIUS = {
    "sm": "4px",
    "md": "7px",
    "lg": "8px",
    "xl": "12px",
    "full": "9999px",
}

FONT = {
    "family": (
        "system-ui, -apple-system, 'Segoe UI', 'Microsoft YaHei', "
        "'PingFang SC', 'Hiragino Sans GB', Arial, sans-serif"
    ),
    "mono": "'JetBrains Mono', 'SF Mono', Consolas, monospace",
    "size": {
        "xs": "11px",
        "sm": "12px",
        "md": "14px",
        "lg": "16px",
        "xl": "18px",
        "2xl": "22px",
        "3xl": "28px",
    },
}

SHADOW = {
    "sm": "0 1px 2px rgba(15,23,42,0.16)",
    "md": "0 2px 8px rgba(15,23,42,0.22)",
    "lg": "0 4px 16px rgba(15,23,42,0.28)",
}

TRANSITION = {
    "fast": "120ms ease",
    "normal": "200ms ease",
    "slow": "300ms ease",
}
