"""
首次使用引导 - 功能介绍弹窗
用于在应用中随时展示功能介绍
"""

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from scenefab.ui.theme.ds_tokens import _C

# 渐变按钮 QSS 模板 — 提取重复的按钮样式
_GRADIENT_BTN_QSS = (
    "QPushButton {{"
    "  background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
    "    stop:0 {c1}, stop:1 {c2});"
    "  color: white; border: none; border-radius: {r}px;"
    "  font-size: {fs}px; font-weight: {fw};"
    "}}"
    "QPushButton:hover {{"
    "  background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
    "    stop:0 {h1}, stop:1 {c2});"
    "}}"
)


def _gradient_btn(
    c1: str, c2: str, h1: str, radius: int = 8, font_size: int = 13, font_weight: int = 600
) -> str:
    """生成渐变按钮样式 — 消除 5 处重复 QSS"""
    return _GRADIENT_BTN_QSS.format(
        c1=c1, c2=c2, h1=h1, r=radius, fs=font_size, fw=font_weight
    )


class FeatureTooltip(QWidget):
    """功能提示弹窗 - 浮动在界面元素旁边"""

    # 信号定义
    dismissed = Signal()  # 关闭信号
    action_clicked = Signal()  # 操作按钮点击

    def __init__(self, title: str, content: str, action_text: str = None, parent=None):  # type: ignore[assignment]
        super().__init__(parent)
        self._title = title
        self._content = content
        self._action_text = action_text
        self._setup_ui()

    def _setup_ui(self):
        self.setFixedWidth(280)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.ToolTip)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 主容器
        container = QWidget(self)
        container.setStyleSheet(
            f"QWidget {{ background-color: {_C.BG_ELEVATED};"
            f" border: 1px solid {_C.BORDER_DEFAULT}; border-radius: 12px; padding: 16px; }}"
        )

        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 标题行
        title_layout = QHBoxLayout()
        title_label = QLabel(self._title)
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setWeight(QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet(f"color: {_C.TEXT_PRIMARY}; background: transparent;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        # 关闭按钮
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.CursorShape.PointingHand)  # type: ignore[attr-defined]
        close_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {_C.TEXT_MUTED}; border: none; font-size: 14px; }}"
            f"QPushButton:hover {{ color: {_C.TEXT_PRIMARY}; background: {_C.BG_SURFACE}; border-radius: 4px; }}"
        )
        close_btn.clicked.connect(self.dismissed.emit)
        title_layout.addWidget(close_btn)
        layout.addLayout(title_layout)

        # 内容
        content_label = QLabel(self._content)
        content_label.setWordWrap(True)
        content_label.setStyleSheet(
            f"color: {_C.TEXT_MUTED}; font-size: 12px; line-height: 1.5; background: transparent;"
        )
        layout.addWidget(content_label)

        # 操作按钮（如果有）
        if self._action_text:
            action_btn = QPushButton(self._action_text)
            action_btn.setCursor(Qt.CursorShape.PointingHand)  # type: ignore[attr-defined]
            action_btn.setFixedHeight(32)
            action_btn.setStyleSheet(
                _gradient_btn(_C.PRIMARY_DARK, _C.PRIMARY, _C.PRIMARY_LIGHT, font_size=12)
            )
            action_btn.clicked.connect(self.action_clicked.emit)
            layout.addWidget(action_btn)

    def show_at(self, x: int, y: int):
        """在指定位置显示"""
        self.move(x, y)
        self.show()
        self.setWindowOpacity(0)
        animation = QPropertyAnimation(self, b"windowOpacity")
        animation.setDuration(200)
        animation.setStartValue(0)
        animation.setEndValue(1)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        animation.start()


class FeatureHighlight(QWidget):
    """功能高亮框 - 用于引导用户关注特定区域"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.ToolTip)

    def highlight_widget(self, widget):
        """高亮指定部件"""
        if widget:
            rect = widget.rect()
            global_rect = (
                widget.mapToGlobal(rect.topLeft()),
                widget.mapToGlobal(rect.bottomRight()),
            )
            self.setGeometry(
                min(global_rect[0].x(), global_rect[1].x()) - 10,
                min(global_rect[0].y(), global_rect[1].y()) - 10,
                abs(global_rect[1].x() - global_rect[0].x()) + 20,
                abs(global_rect[1].y() - global_rect[0].y()) + 20,
            )
            self.show()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor(_C.PRIMARY_DARK))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)


class FeatureTourDialog(QWidget):
    """功能导览对话框 - 完整的功能介绍弹窗"""

    # 信号定义
    closed = Signal()  # 关闭信号
    next_feature = Signal()  # 下一个功能
    prev_feature = Signal()  # 上一个功能

    def __init__(self, features: list = None, parent=None):  # type: ignore[assignment]
        super().__init__(parent)
        self._features = features or self._default_features()
        self._current_index = 0
        self._setup_ui()

    def _default_features(self) -> list:
        """默认功能列表"""
        return [
            {"icon": "📁", "title": "导入视频",
             "content": "拖放视频文件到此处，或点击选择文件。支持 MP4、AVI、MOV 等常见格式。",
             "action": "选择文件"},
            {"icon": "✂️", "title": "智能剪辑",
             "content": "AI 自动识别视频中的精彩片段，您也可以手动调整剪辑点。",
             "action": None},
            {"icon": "📝", "title": "脚本生成",
             "content": "基于视频内容自动生成解说脚本，支持多种风格自定义。",
             "action": None},
            {"icon": "🎤", "title": "语音合成",
             "content": "选择喜欢的 AI 语音进行配音，多种音色可选。",
             "action": None},
            {"icon": "📤", "title": "导出项目",
             "content": "导出为 Premiere、剪映、DaVinci 等项目文件，或直接渲染视频。",
             "action": "查看格式"},
        ]

    # ── UI 拆分: 原 _setup_ui (175行) → 4 个职责单一的方法 ──────────

    def _setup_ui(self):
        """设置 UI — 组装各子区域"""
        self.setFixedSize(420, 320)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        main_widget = QWidget(self)
        main_widget.setFixedSize(420, 320)
        main_widget.setStyleSheet(
            f"QWidget {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            f"  stop:0 {_C.BG_BASE}, stop:0.5 {_C.BG_SURFACE}, stop:1 {_C.BG_BASE});"
            f"  border: 1px solid {_C.BORDER_DEFAULT}; border-radius: 16px; }}"
        )

        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        layout.addLayout(self._build_header())       # 顶部: 图标+标题+进度
        layout.addWidget(self._build_content_frame()) # 内容卡片
        layout.addStretch()
        layout.addLayout(self._build_button_bar())    # 底部: 关闭+导航

        self._update_buttons()

    def _build_header(self) -> QHBoxLayout:
        """顶部区域: 图标 + 标题 + 进度指示器"""
        header = QHBoxLayout()
        header.setSpacing(12)

        self.icon_label = QLabel(self._features[0]["icon"])
        self.icon_label.setStyleSheet("font-size: 32px; background: transparent;")
        header.addWidget(self.icon_label)

        self.title_label = QLabel(self._features[0]["title"])
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setWeight(QFont.Weight.Bold)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet(f"color: {_C.TEXT_PRIMARY}; background: transparent;")
        header.addWidget(self.title_label)
        header.addStretch()

        progress_label = QLabel(f"{self._current_index + 1}/{len(self._features)}")
        progress_label.setStyleSheet(
            f"color: {_C.TEXT_MUTED}; font-size: 12px; background: transparent;"
        )
        header.addWidget(progress_label)
        return header

    def _build_content_frame(self) -> QFrame:
        """内容区域卡片"""
        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame {{ background-color: {_C.BG_ELEVATED};"
            f"  border: 1px solid {_C.BORDER_DEFAULT}; border-radius: 12px; padding: 16px; }}"
        )
        layout = QVBoxLayout(frame)
        layout.setSpacing(8)

        self.content_label = QLabel(self._features[0]["content"])
        self.content_label.setWordWrap(True)
        self.content_label.setStyleSheet(
            f"color: {_C.TEXT_SECONDARY}; font-size: 13px; line-height: 1.6; background: transparent;"
        )
        layout.addWidget(self.content_label)

        # 操作按钮（如果有）
        if self._features[0].get("action"):
            self.action_btn = QPushButton(self._features[0]["action"])
            self.action_btn.setCursor(Qt.CursorShape.PointingHand)  # type: ignore[attr-defined]
            self.action_btn.setFixedHeight(36)
            self.action_btn.setStyleSheet(
                _gradient_btn(_C.PRIMARY_DARK, _C.PRIMARY, _C.PRIMARY_LIGHT)
            )
            layout.addWidget(self.action_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        return frame

    def _build_button_bar(self) -> QHBoxLayout:
        """底部按钮栏: 关闭 + 上一个 + 下一个"""
        bar = QHBoxLayout()
        bar.setSpacing(12)

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.setCursor(Qt.CursorShape.PointingHand)  # type: ignore[attr-defined]
        close_btn.setFixedHeight(36)
        close_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {_C.TEXT_MUTED};"
            f"  border: 1px solid {_C.BORDER_DEFAULT}; border-radius: 8px; font-size: 13px; }}"
            f"QPushButton:hover {{ background: {_C.BG_SURFACE}; color: {_C.TEXT_SECONDARY}; }}"
        )
        close_btn.clicked.connect(self.closed.emit)
        bar.addWidget(close_btn)
        bar.addStretch()

        # 上一个按钮
        self.prev_btn = QPushButton("←")
        self.prev_btn.setCursor(Qt.CursorShape.PointingHand)  # type: ignore[attr-defined]
        self.prev_btn.setFixedSize(36, 36)
        self.prev_btn.clicked.connect(self._show_prev)
        bar.addWidget(self.prev_btn)

        # 下一个按钮
        self.next_btn = QPushButton("→")
        self.next_btn.setCursor(Qt.CursorShape.PointingHand)  # type: ignore[attr-defined]
        self.next_btn.setFixedSize(36, 36)
        self.next_btn.clicked.connect(self._show_next)
        bar.addWidget(self.next_btn)

        return bar

    # ── 更新逻辑 ───────────────────────────────────────────────

    def _update_content(self):
        """更新当前功能的内容显示"""
        feature = self._features[self._current_index]
        self.icon_label.setText(feature["icon"])
        self.title_label.setText(feature["title"])
        self.content_label.setText(feature["content"])
        self._update_buttons()

    def _update_buttons(self):
        """根据当前索引更新导航按钮状态"""
        # 上一个按钮
        self.prev_btn.setEnabled(self._current_index > 0)
        self.prev_btn.setStyleSheet(
            f"QPushButton {{ background: {_C.BG_SURFACE}; color: {_C.TEXT_SECONDARY};"
            f"  border: 1px solid {_C.BORDER_DEFAULT}; border-radius: 8px; font-size: 14px; }}"
            f"QPushButton:hover {{ background: {_C.BG_ELEVATED}; border-color: {_C.PRIMARY_DARK}; }}"
            f"QPushButton:disabled {{ background: transparent; color: {_C.TEXT_MUTED}; border-color: transparent; }}"
        )

        # 下一个按钮 — 最后一页变为完成态
        is_last = self._current_index >= len(self._features) - 1
        if is_last:
            self.next_btn.setText("✓")
            self.next_btn.setStyleSheet(
                _gradient_btn(_C.SUCCESS, "#2EA043", _C.SUCCESS, radius=8, font_size=14)
            )
        else:
            self.next_btn.setText("→")
            self.next_btn.setStyleSheet(
                _gradient_btn(_C.PRIMARY_DARK, _C.PRIMARY, _C.PRIMARY_LIGHT, radius=8, font_size=14)
            )

    def _show_prev(self):
        """显示上一个功能"""
        if self._current_index > 0:
            self._current_index -= 1
            self._update_content()
            self.prev_feature.emit()

    def _show_next(self):
        """显示下一个功能"""
        if self._current_index < len(self._features) - 1:
            self._current_index += 1
            self._update_content()
            self.next_feature.emit()
        else:
            self.closed.emit()

    def show_at_center(self):
        """在父窗口中央显示"""
        if self.parent():
            parent_rect = self.parent().rect()  # type: ignore[union-attr]
            x = (parent_rect.width() - self.width()) // 2
            y = (parent_rect.height() - self.height()) // 2
            self.move(
                self.parent().mapToGlobal(self.parent().rect().topLeft()).x() + x,  # type: ignore[union-attr]
                self.parent().mapToGlobal(self.parent().rect().topLeft()).y() + y,  # type: ignore[union-attr]
            )
        self.show()
        self._animate_in()

    def _animate_in(self):
        """入场动画"""
        self.setWindowOpacity(0)
        animation = QPropertyAnimation(self, b"windowOpacity")
        animation.setDuration(300)
        animation.setStartValue(0)
        animation.setEndValue(1)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        animation.start()

    def _animate_out(self):
        """离场动画"""
        animation = QPropertyAnimation(self, b"windowOpacity")
        animation.setDuration(200)
        animation.setStartValue(1)
        animation.setEndValue(0)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        animation.finished.connect(self.close)
        animation.start()
