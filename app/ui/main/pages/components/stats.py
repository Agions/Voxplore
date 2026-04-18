#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统计组件

提供项目管理页面中使用的统计相关 UI 组件。
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt

from app.ui.components import MacLabel


def create_stat_item(icon: str, label: str, value: str) -> QWidget:
    """
    创建统计项组件

    Args:
        icon: 图标 emoji
        label: 标签文字
        value: 显示数值

    Returns:
        统计项容器组件
    """
    container = QWidget()
    container.setProperty("class", "stat-item")
    layout = QVBoxLayout(container)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(4)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

    # 图标
    icon_label = QLabel(icon)
    icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_label.setStyleSheet("font-size: 20px;")
    layout.addWidget(icon_label)

    # 数值
    value_label = MacLabel(value, css_class="text-lg text-bold")
    value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    value_label.setObjectName("stat_value")
    layout.addWidget(value_label)

    # 标签
    label_widget = MacLabel(label, css_class="text-sm text-muted")
    label_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(label_widget)

    # 保存引用以便后续更新
    container.stat_value_label = value_label

    return container


def create_detail_row(label: str, value_label: MacLabel) -> QWidget:
    """
    创建详情行

    Args:
        label: 行标签
        value_label: 已有或新建的 MacLabel 组件

    Returns:
        详情行容器
    """
    row = QWidget()
    row.setProperty("class", "stat-row")
    row_layout = QHBoxLayout(row)
    row_layout.setContentsMargins(0, 0, 0, 0)
    row_layout.setSpacing(8)

    label_widget = MacLabel(label, css_class="text-secondary text-bold")
    row_layout.addWidget(label_widget)
    row_layout.addWidget(value_label, 1)

    return row


def create_stats_grid(stat_items: list) -> QWidget:
    """
    创建统计网格

    Args:
        stat_items: [(icon, label, value), ...] 元组列表

    Returns:
        统计网格容器
    """
    from PySide6.QtWidgets import QHBoxLayout

    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(16)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

    for icon, label, value in stat_items:
        stat_widget = create_stat_item(icon, label, value)
        layout.addWidget(stat_widget)

    return container


__all__ = [
    "create_stat_item",
    "create_detail_row",
    "create_stats_grid",
]
