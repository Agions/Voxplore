"""
QSS CSS 变量注册
将 tokens.py 的值注册为 QSS 变量
"""
from .tokens import COLORS, SPACING, RADIUS, FONT, SHADOW, TRANSITION


def register_qss_variables() -> str:
    """生成 QSS 变量声明"""
    lines = ["/* === Voxplore Design Tokens === */"]

    # 颜色
    for key, val in COLORS.items():
        lines.append(f"    --color-{key}: {val};")

    # 间距
    for key, val in SPACING.items():
        lines.append(f"    --spacing-{key}: {val};")

    # 圆角
    for key, val in RADIUS.items():
        lines.append(f"    --radius-{key}: {val};")

    # 字体
    lines.append(f"    --font-family: {FONT['family']};")
    lines.append(f"    --font-mono: {FONT['mono']};")
    for key, val in FONT['size'].items():
        lines.append(f"    --font-size-{key}: {val};")

    # 阴影
    for key, val in SHADOW.items():
        lines.append(f"    --shadow-{key}: {val};")

    # 过渡
    for key, val in TRANSITION.items():
        lines.append(f"    --transition-{key}: {val};")

    return "\n".join(lines)
