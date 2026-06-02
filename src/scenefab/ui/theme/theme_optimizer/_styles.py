from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from scenefab.ui.components.design_system import Colors


def generate_theme_stylesheet(colors: dict, is_dark: bool = True) -> str:
    """根据配色生成完整的主题样式表"""
    primary_light = colors.get("primary", "#6366F1")

    _BASE = """
/* Generated Theme Stylesheet - {name} */

QWidget {{
    background-color: {background};
    color: {text};
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', sans-serif;
    font-size: 13px;
}}

{_qmainwindow}

QPushButton[class="primary"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {primary},
        stop:1 {primary_end});
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
}}

QPushButton[class="primary"]:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {primary_light},
        stop:1 {primary_end});
}}

{_primary_pressed}

QPushButton[class="secondary"] {{
    background-color: transparent;
    border: 1px solid {border};
    color: {text_secondary};
    border-radius: 8px;
    padding: 8px 16px;
}}

QPushButton[class="secondary"]:hover {{
    background-color: {_sec_hover_bg};
    border-color: {primary};
}}

QLineEdit, QTextEdit {{
    background-color: {background};
    color: {text};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 8px 12px;
}}

QLineEdit:focus, QTextEdit:focus {{
    border-color: {primary};
    background-color: {surface};
}}

QScrollBar::handle:vertical {{
    background: {border};
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: {text_tertiary};
}}

QListWidget::item:selected {{
    {_list_selected_bg}
    color: white;
}}

QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {primary},
        stop:1 {primary_end});
}}

QMenu {{
    background-color: {_menu_bg};
    border: 1px solid {border};
    border-radius: 8px;
}}

QMenu::item:selected {{
    background-color: {primary};
{_menu_selected_color}}}

QToolTip {{
    background-color: {card_elevated};
    color: {text};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 6px 10px;
}}
"""

    if is_dark:
        _qmainwindow = """QMainWindow {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {background},
        stop:0.5 {surface},
        stop:1 {background});
}}"""
        _primary_pressed = """QPushButton[class="primary"]:pressed {{
    transform: scale(0.98);
}}"""
        _sec_hover_bg = "{card}"
        _list_selected_bg = """    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {primary},
        stop:1 {primary_end});"""
        _menu_bg = "{surface}"
        _menu_selected_color = ""
    else:
        _qmainwindow = "QMainWindow {\n    background-color: {background};\n}"
        _primary_pressed = ""
        _sec_hover_bg = "{surface}"
        _list_selected_bg = "    background-color: {primary};"
        _menu_bg = "{card}"
        _menu_selected_color = "    color: white;"

    return _BASE.format(
        name=colors.get("name", "Custom Theme"),
        primary_light=primary_light,
        _qmainwindow=_qmainwindow,
        _primary_pressed=_primary_pressed,
        _sec_hover_bg=_sec_hover_bg,
        _list_selected_bg=_list_selected_bg,
        _menu_bg=_menu_bg,
        _menu_selected_color=_menu_selected_color,
        **{k: v for k, v in colors.items() if k not in ("name", "primary")}
    )

