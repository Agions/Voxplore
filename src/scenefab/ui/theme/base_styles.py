"""
SceneFab 基础样式系统
所有样式基于 tokens.py，不硬编码颜色值
"""

from string import Template

from .tokens import COLORS, FONT, RADIUS


def get_base_qss() -> str:
    """返回全局基础 QSS"""
    values = {
        "bg_base": COLORS["bg-base"],
        "bg_elevated": COLORS["bg-elevated"],
        "bg_overlay": COLORS["bg-overlay"],
        "bg_surface": COLORS["bg-surface"],
        "border": COLORS["border"],
        "border_strong": COLORS["border-strong"],
        "border_subtle": COLORS["border-subtle"],
        "font_family": FONT["family"],
        "font_md": FONT["size"]["md"],
        "font_sm": FONT["size"]["sm"],
        "primary": COLORS["primary"],
        "primary_hover": COLORS["primary-hover"],
        "primary_pressed": COLORS["primary-pressed"],
        "radius_full": RADIUS["full"],
        "radius_lg": RADIUS["lg"],
        "radius_md": RADIUS["md"],
        "text_disabled": COLORS["text-disabled"],
        "text_muted": COLORS["text-muted"],
        "text_primary": COLORS["text-primary"],
        "text_secondary": COLORS["text-secondary"],
    }
    return Template("""
    /* === 全局 === */
    QWidget {
        background-color: $bg_base;
        color: $text_primary;
        font-family: $font_family;
        font-size: $font_md;
    }

    /* === 按钮 === */
    QPushButton {
        background-color: $bg_elevated;
        color: $text_primary;
        border: 1px solid $border;
        border-radius: $radius_md;
        padding: 8px 16px;
        font-size: $font_md;
    }
    QPushButton:hover {
        background-color: $bg_overlay;
        border-color: $border_strong;
    }
    QPushButton:pressed {
        background-color: $bg_surface;
    }
    QPushButton:disabled {
        color: $text_disabled;
        border-color: $border_subtle;
    }

    /* 主按钮 */
    QPushButton.primary {
        background-color: $primary;
        color: white;
        border: none;
    }
    QPushButton.primary:hover {
        background-color: $primary_hover;
    }
    QPushButton.primary:pressed {
        background-color: $primary_pressed;
    }

    /* 次要按钮 */
    QPushButton.secondary {
        background-color: transparent;
        color: $text_secondary;
        border: 1px solid $border;
    }
    QPushButton.secondary:hover {
        color: $text_primary;
        border-color: $border_strong;
    }

    /* === 卡片 === */
    QFrame.card {
        background-color: $bg_surface;
        border: 1px solid $border;
        border-radius: $radius_lg;
    }

    /* === 输入框 === */
    QLineEdit {
        background-color: $bg_surface;
        color: $text_primary;
        border: 1px solid $border;
        border-radius: $radius_md;
        padding: 8px 12px;
        font-size: $font_md;
    }
    QLineEdit:focus {
        border-color: $primary;
    }
    QLineEdit::placeholder {
        color: $text_muted;
    }

    /* === 标签 === */
    QLabel {
        background: transparent;
        color: $text_primary;
    }
    QLabel.subtitle {
        color: $text_secondary;
        font-size: $font_sm;
    }

    /* === 进度条 === */
    QProgressBar {
        background-color: $bg_surface;
        border: none;
        border-radius: $radius_full;
        height: 4px;
    }
    QProgressBar::chunk {
        background-color: $primary;
        border-radius: $radius_full;
    }

    /* === 滚动条 === */
    QScrollBar:vertical {
        background: transparent;
        width: 6px;
    }
    QScrollBar::handle:vertical {
        background: $border_strong;
        border-radius: 3px;
        min-height: 40px;
    }
    QScrollBar::handle:vertical:hover {
        background: $text_muted;
    }
    """).substitute(values)
