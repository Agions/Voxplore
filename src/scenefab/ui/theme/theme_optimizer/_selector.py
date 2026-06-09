from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from scenefab.ui.components.design_system import Colors
from scenefab.ui.theme.theme_optimizer._presets import ThemePresets


class ThemePresetSelector(QWidget):
    """主题预设选择器 - 图形化选择界面"""

    # 信号
    theme_selected = Signal(str, dict)  # 主题名称, 配色

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # 标题
        title = QLabel("选择主题")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {Colors.TextPrimary};")
        layout.addWidget(title)

        # 深色主题区域
        dark_label = QLabel("深色主题")
        dark_label.setStyleSheet(
            f"color: {Colors.TextSecondary}; font-size: 12px; font-weight: 600;"
        )
        layout.addWidget(dark_label)

        dark_grid = QHBoxLayout()
        dark_grid.setSpacing(12)

        for name, colors in ThemePresets.DARK_THEMES.items():
            btn = self._create_theme_button(name, colors, is_dark=True)
            dark_grid.addWidget(btn)

        layout.addLayout(dark_grid)

        # 浅色主题区域
        light_label = QLabel("浅色主题")
        light_label.setStyleSheet(
            f"color: {Colors.TextSecondary}; font-size: 12px; font-weight: 600;"
        )
        layout.addWidget(light_label)

        light_grid = QHBoxLayout()
        light_grid.setSpacing(12)

        for name, colors in ThemePresets.LIGHT_THEMES.items():
            btn = self._create_theme_button(name, colors, is_dark=False)
            light_grid.addWidget(btn)

        layout.addLayout(light_grid)

    def _create_theme_button(self, name: str, colors: dict, is_dark: bool):
        """创建主题预览按钮"""
        btn = QPushButton()
        btn.setFixedSize(60, 50)
        btn.setCursor(Qt.CursorShape.PointingHand)
        btn.setToolTip(name)

        # 预览样式
        bg = colors.get("background", "#0A0A0F")
        primary = colors.get("primary", "#6366F1")

        btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {bg},
                    stop:0.5 {colors.get("surface", bg)},
                    stop:1 {bg});
                border: 2px solid {colors.get("border", "#30363D")};
                border-radius: 8px;
            }}
            QPushButton:hover {{
                border-color: {primary};
            }}
        """)

        # 点击事件
        btn.clicked.connect(lambda: self.theme_selected.emit(name, colors))

        return btn
