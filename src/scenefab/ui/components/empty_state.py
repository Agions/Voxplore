"""
SceneFab 空状态组件 - 品牌升级版
带引导语的插画风格空状态
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from scenefab.ui.theme.ds_tokens import _C, QSSComponents

# 图标渐变色定义 — 提取为常量，消除 paintEvent 中的 if/elif 链
_ICON_GRADIENTS: dict[str, tuple[str, str]] = {
    "projects": ("#388BFD", "#79C0FF"),
    "media": ("#A371F7", "#D2A8FF"),
    "files": ("#22C55E", "#79C0FF"),
    "default": (_C.PRIMARY, _C.ACCENT),
}

_ICON_SYMBOLS: dict[str, str] = {
    "projects": "📁",
    "media": "🎬",
    "files": "📄",
    "search": "🔍",
    "error": "⚠️",
    "default": "📭",
}


class EmptyStateIcon(QFrame):
    """空状态图标 - 渐变风格插画"""

    def __init__(self, icon_type: str = "default", size: int = 120, parent=None):
        super().__init__(parent)
        self._icon_type = icon_type
        self._size = size
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center = self.rect().center()
        radius = self._size // 2 - 10

        # 外圈渐变
        gradient = QLinearGradient(
            center.x() - radius, center.y() - radius,
            center.x() + radius, center.y() + radius,
        )
        c1, c2 = _ICON_GRADIENTS.get(self._icon_type, _ICON_GRADIENTS["default"])
        gradient.setColorAt(0, QColor(c1).withAlpha(40))  # type: ignore[attr-defined]
        gradient.setColorAt(1, QColor(c2).withAlpha(30))  # type: ignore[attr-defined]

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawEllipse(center, radius, radius)

        # 内圈高光
        inner = QLinearGradient(
            center.x() - radius + 15, center.y() - radius + 15,
            center.x() + radius - 15, center.y() + radius - 15,
        )
        inner.setColorAt(0, QColor("#FFFFFF").withAlpha(20))  # type: ignore[attr-defined]
        inner.setColorAt(1, QColor("#FFFFFF").withAlpha(5))  # type: ignore[attr-defined]
        painter.setBrush(inner)
        painter.drawEllipse(center, radius - 12, radius - 12)

        # 图标符号
        painter.setPen(QColor(_C.TEXT_SECONDARY))
        icon_font = QFont("Arial")
        icon_font.setPointSize(int(radius * 0.5))
        painter.setFont(icon_font)
        icon = _ICON_SYMBOLS.get(self._icon_type, _ICON_SYMBOLS["default"])
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, icon)


class EmptyStateButton(QPushButton):
    """空状态操作按钮"""

    def __init__(self, text: str, primary: bool = True, parent=None):
        super().__init__(text, parent)
        self._primary = primary
        self._setup_style()

    def _setup_style(self):
        if self._primary:
            self.setStyleSheet(QSSComponents.btn_primary())
        else:
            self.setStyleSheet(QSSComponents.btn_secondary())
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class MacEmptyStateV2(QWidget):
    """增强版空状态组件 - 品牌升级"""

    # 信号定义
    action_clicked = Signal(str)  # 操作点击信号

    def __init__(
        self,
        icon_type: str = "default",
        title: str = "暂无内容",
        description: str = "",
        primary_action_text: str = "",
        secondary_action_text: str = "",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._icon_type = icon_type
        self._title = title
        self._description = description
        self._primary_action_text = primary_action_text
        self._secondary_action_text = secondary_action_text
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(24)
        layout.setContentsMargins(40, 60, 40, 60)

        # 图标
        self.icon_widget = EmptyStateIcon(self._icon_type, 120)
        layout.addWidget(self.icon_widget)

        # 标题
        self.title_label = QLabel(self._title)
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setWeight(QFont.Weight.Bold)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet(f"color: {_C.TEXT_PRIMARY};")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        # 描述
        if self._description:
            self.desc_label = QLabel(self._description)
            desc_font = QFont()
            desc_font.setPointSize(14)
            self.desc_label.setFont(desc_font)
            self.desc_label.setStyleSheet(f"color: {_C.TEXT_MUTED}; line-height: 1.6;")
            self.desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.desc_label.setWordWrap(True)
            self.desc_label.setMaximumWidth(400)
            layout.addWidget(self.desc_label)

        # 操作按钮
        if self._primary_action_text or self._secondary_action_text:
            button_layout = QHBoxLayout()
            button_layout.setSpacing(12)
            button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            if self._primary_action_text:
                self.primary_btn = EmptyStateButton(self._primary_action_text, primary=True)
                self.primary_btn.clicked.connect(lambda: self.action_clicked.emit("primary"))
                button_layout.addWidget(self.primary_btn)

            if self._secondary_action_text:
                self.secondary_btn = EmptyStateButton(self._secondary_action_text, primary=False)
                self.secondary_btn.clicked.connect(lambda: self.action_clicked.emit("secondary"))
                button_layout.addWidget(self.secondary_btn)

            layout.addLayout(button_layout)

    def set_title(self, title: str):
        """设置标题"""
        self._title = title
        self.title_label.setText(title)

    def set_description(self, description: str):
        """设置描述"""
        self._description = description
        self.desc_label.setText(description)

    def set_icon_type(self, icon_type: str):
        """设置图标类型"""
        self._icon_type = icon_type
        self.layout().itemAt(0).widget().deleteLater()  # type: ignore[union-attr]
        self.icon_widget = EmptyStateIcon(self._icon_type, 120)
        self.layout().insertWidget(0, self.icon_widget)  # type: ignore[union-attr]


class ProjectsEmptyState(MacEmptyStateV2):
    """项目列表空状态"""

    def __init__(self, parent=None):
        super().__init__(
            icon_type="projects",
            title="暂无项目",
            description="创建您的第一个视频项目，开始创作之旅",
            primary_action_text="创建项目",
            secondary_action_text="导入项目",
            parent=parent,
        )


class MediaLibraryEmptyState(MacEmptyStateV2):
    """素材库空状态"""

    def __init__(self, parent=None):
        super().__init__(
            icon_type="media",
            title="素材库为空",
            description="导入视频、图片和音频素材，开始您的创作",
            primary_action_text="导入素材",
            parent=parent,
        )


class SearchEmptyState(MacEmptyStateV2):
    """搜索结果空状态"""

    def __init__(self, keyword: str = "", parent=None):
        super().__init__(
            icon_type="search",
            title="未找到结果",
            description=f"没有找到与「{keyword}」相关的内容，请尝试其他关键词",
            parent=parent,
        )


class ErrorEmptyState(MacEmptyStateV2):
    """错误空状态"""

    def __init__(self, error_message: str = "出了点问题", parent=None):
        super().__init__(
            icon_type="error",
            title=error_message,
            description="请稍后重试，或联系技术支持",
            primary_action_text="重试",
            parent=parent,
        )
