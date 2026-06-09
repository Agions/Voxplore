"""
macOS 设计系统 - 通用组件库
向后兼容层 - 从新模块导入
"""

# 从新模块导入所有组件，保持向后兼容
# 保留自定义辅助函数

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from scenefab.ui.components.buttons import MacSecondaryButton
from scenefab.ui.components.containers import MacCard
from scenefab.ui.components.labels import MacBadge, MacLabel, MacTitleLabel
from scenefab.ui.components.layout import MacEmptyState


class MacIconButton(QPushButton):
    """图标按钮 — 简单封装: 图标字符 + 固定尺寸."""

    def __init__(self, icon_text: str = "", size: int = 24, parent=None):
        super().__init__(icon_text, parent)
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)  # type: ignore[attr-defined]
        self.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                font-size: 16px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.1);
                border-radius: 4px;
            }
        """)


def create_icon_text_row(
    icon: str, text: str, parent: QWidget | None = None
) -> QWidget:
    """创建图标+文字行"""
    widget = QWidget(parent)
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    icon_label = QLabel(icon)
    text_label = MacLabel(text)

    layout.addWidget(icon_label)
    layout.addWidget(text_label)

    return widget


def create_status_badge_row(status: str, parent: QWidget | None = None) -> QWidget:
    """创建状态徽章行"""
    widget = QWidget(parent)
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    status_badge = MacBadge(status)

    layout.addWidget(status_badge)
    layout.addStretch()

    return widget
