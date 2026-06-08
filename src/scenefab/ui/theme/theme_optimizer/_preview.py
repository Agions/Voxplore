from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget


class ThemeColorPreview(QWidget):
    """主题颜色预览组件"""

    def __init__(self, colors: dict = None, parent=None):
        super().__init__(parent)
        self._colors = colors or {}
        self._setup_ui()

    def _setup_ui(self):
        self.setFixedSize(200, 120)
        self.setStyleSheet("""
            QWidget {
                background: transparent;
            }
        """)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制背景预览
        bg = self._colors.get("background", "#0A0A0F")
        painter.fillRect(self.rect(), QColor(bg))

        # 绘制色块
        colors_to_show = [
            ("primary", 10, 10),
            ("surface", 40, 10),
            ("card", 70, 10),
            ("accent", 100, 10),
            ("success", 130, 10),
            ("warning", 160, 10),
        ]

        for color_key, x, y in colors_to_show:
            color = self._colors.get(color_key, "#6366F1")
            painter.fillRect(x, y, 25, 15, QColor(color))

    def set_colors(self, colors: dict):
        """设置颜色"""
        self._colors = colors
        self.update()


