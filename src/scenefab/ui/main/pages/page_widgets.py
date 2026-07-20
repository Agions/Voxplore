#!/usr/bin/env python3
"""Shared widgets for the production workspace pages."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...theme.ds_tokens import _C, FontSizes, FontWeights, Radii


def page_background_style(object_name: str) -> str:
    return f"""
        #{object_name} {{
            background: {_C.BG_BASE};
        }}
    """


def scroll_area() -> QScrollArea:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet("border: none; background: transparent;")
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    return scroll


def page_container() -> QWidget:
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(34, 30, 34, 30)
    layout.setSpacing(20)
    return container


def panel(name: str, elevated: bool = False) -> QFrame:
    frame = QFrame()
    frame.setObjectName(name)
    bg = _C.BG_SURFACE if not elevated else _C.BG_ELEVATED
    border = _C.BORDER_SUBTLE if not elevated else _C.BORDER_DEFAULT
    frame.setStyleSheet(f"""
        QFrame#{name} {{
            background: {bg};
            border: 1px solid {border};
            border-radius: {Radii.base};
        }}
    """)
    return frame


def header_panel(name: str, title: str, subtitle: str, *actions: QWidget) -> QFrame:
    frame = panel(name)
    layout = QHBoxLayout(frame)
    layout.setContentsMargins(24, 20, 24, 20)
    layout.setSpacing(20)

    text = QVBoxLayout()
    text.setSpacing(5)
    title_label = QLabel(title)
    title_label.setFont(QFont("", FontSizes.xxl, QFont.Weight.Bold))
    title_label.setStyleSheet(f"color: {_C.TEXT_PRIMARY}; letter-spacing: 0px;")
    text.addWidget(title_label)

    subtitle_label = QLabel(subtitle)
    subtitle_label.setFont(QFont("", FontSizes.sm))
    subtitle_label.setStyleSheet(f"color: {_C.TEXT_MUTED}; line-height: 18px;")
    text.addWidget(subtitle_label)
    layout.addLayout(text, 1)

    for action in actions:
        layout.addWidget(action)
    return frame


def section_title(text: str) -> QLabel:
    label = QLabel(text)
    label.setFont(QFont("", FontSizes.md, QFont.Weight.DemiBold))
    label.setStyleSheet(f"color: {_C.TEXT_PRIMARY}; letter-spacing: 0px;")
    return label


def action_button(text: str, primary: bool = False, height: int = 34) -> QPushButton:
    button = QPushButton(text)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setFixedHeight(height)
    button.setStyleSheet(action_button_style(primary))
    return button


def action_button_style(primary: bool = False, padding: int = 14) -> str:
    color = "#ffffff" if primary else _C.TEXT_SECONDARY
    bg = _C.PRIMARY if primary else _C.BG_SURFACE
    border = _C.PRIMARY if primary else _C.BORDER_DEFAULT
    hover = _C.PRIMARY_DARK if primary else _C.BG_ELEVATED
    hover_color = "#ffffff" if primary else _C.TEXT_PRIMARY
    pressed = _C.PRIMARY_DARKER if primary else _C.BG_OVERLAY
    return f"""
        QPushButton {{
            background: {bg};
            color: {color};
            border: 1px solid {border};
            border-radius: {Radii.base};
            padding: 0 {padding}px;
            font-size: {FontSizes.xs}px;
            font-weight: {FontWeights.SemiBold};
        }}
        QPushButton:hover {{
            background: {hover};
            color: {hover_color};
            border-color: {_C.PRIMARY if not primary else _C.PRIMARY_DARK};
        }}
        QPushButton:pressed {{
            background: {pressed};
        }}
    """


def key_value_row(label: str, value: str) -> QFrame:
    row = QFrame()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(10)

    key = QLabel(label)
    key.setFont(QFont("", FontSizes.xs))
    key.setStyleSheet(f"color: {_C.TEXT_MUTED};")
    layout.addWidget(key)
    layout.addStretch()

    val = QLabel(value)
    val.setFont(QFont("", FontSizes.xs, QFont.Weight.Medium))
    val.setStyleSheet(f"color: {_C.TEXT_PRIMARY};")
    layout.addWidget(val)
    return row


def empty_state(text: str, min_height: int, padding: int = 0) -> QLabel:
    label = QLabel(text)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setMinimumHeight(min_height)
    label.setWordWrap(True)
    label.setStyleSheet(f"""
        QLabel {{
            color: {_C.TEXT_DISABLED};
            background: {_C.BG_ELEVATED};
            border: 1px dashed {_C.BORDER_DEFAULT};
            border-radius: {Radii.base};
            padding: {padding}px;
        }}
    """)
    return label
