"""
主题切换组件 - 快速切换主题
"""

from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
                             QPushButton, QMenu)
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QColor, QPainter

from .theme_optimizer import ThemePresets


class ThemeColorDot(QWidget):
    """主题颜色小圆点"""
    
    def __init__(self, color: str, size: int = 12, parent=None):
        super().__init__(parent)
        self._color = color
        self._size = size
        self.setFixedSize(size, size)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制圆点
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self._color))
        painter.drawEllipse(self.rect())


class ThemeToggleButton(QWidget):
    """主题切换按钮"""
    
    # 信号
    theme_changed = Signal(str, bool)  # 主题名称, 是否深色
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_theme = "Midnight"
        self._is_dark = True
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # 主题图标
        self.icon_label = QLabel("🎨")
        self.icon_label.setStyleSheet("font-size: 16px; background: transparent;")
        layout.addWidget(self.icon_label)
        
        # 主题名称
        self.theme_label = QLabel(self._current_theme)
        self.theme_label.setStyleSheet("color: #C9D1D9; font-size: 12px; background: transparent;")
        layout.addWidget(self.theme_label)
        
        # 下拉箭头
        arrow = QLabel("▼")
        arrow.setStyleSheet("color: #8B949E; font-size: 8px; background: transparent;")
        layout.addWidget(arrow)
        
        # 设置为可点击
        self.setCursor(Qt.CursorShape.PointingHand)
        self.setStyleSheet("""
            QWidget {
                background-color: #1A1A24;
                border: 1px solid #30363D;
                border-radius: 8px;
                padding: 4px 8px;
            }
        """)
        
        # 点击显示菜单
        self._menu = None
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._show_theme_menu()
        super().mousePressEvent(event)
        
    def _show_theme_menu(self):
        """显示主题菜单"""
        self._menu = QMenu(self)
        self._menu.setStyleSheet("""
            QMenu {
                background-color: #1A1A24;
                border: 1px solid #30363D;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 32px 8px 12px;
                border-radius: 4px;
                color: #C9D1D9;
            }
            QMenu::item:selected {
                background-color: #6366F1;
                color: white;
            }
        """)
        
        # 深色主题组
        dark_group = self._menu.addMenu("🌙 深色主题")
        for name in ThemePresets.DARK_THEMES.keys():
            action = dark_group.addAction(name)
            action.triggered.connect(lambda checked, n=name: self._select_theme(n, True))
            
        # 浅色主题组  
        light_group = self._menu.addMenu("☀️ 浅色主题")
        for name in ThemePresets.LIGHT_THEMES.keys():
            action = light_group.addAction(name)
            action.triggered.connect(lambda checked, n=name: self._select_theme(n, False))
            
        # 显示菜单
        pos = self.mapToGlobal(QPoint(0, self.height()))
        self._menu.exec(pos)
        
    def _select_theme(self, name: str, is_dark: bool):
        """选择主题"""
        self._current_theme = name
        self._is_dark = is_dark
        self.theme_label.setText(name)
        self.theme_changed.emit(name, is_dark)
        
    def get_current_theme(self):
        """获取当前主题"""
        return self._current_theme, self._is_dark


class QuickThemeSwitcher(QWidget):
    """快速主题切换器 - 侧边栏用"""
    
    # 信号
    theme_selected = Signal(str, dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # 标题
        title = QLabel("主题")
        title.setStyleSheet("color: #8B949E; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;")
        layout.addWidget(title)
        
        # 主题选项网格
        grid_layout = QHBoxLayout()
        grid_layout.setSpacing(8)
        
        # 深色主题选项
        dark_themes = [
            ("Midnight", "#6366F1"),
            ("Ocean", "#0EA5E9"),
            ("Forest", "#22C55E"),
            ("Sunset", "#F97316"),
            ("Purple", "#A855F7"),
            ("Rose", "#F43F5E"),
        ]
        
        for name, color in dark_themes:
            btn = self._create_theme_btn(name, color, True)
            grid_layout.addWidget(btn)
            
        layout.addLayout(grid_layout)
        
        # 浅色主题选项
        grid_layout2 = QHBoxLayout()
        grid_layout2.setSpacing(8)
        
        light_themes = [
            ("Snow", "#0969DA"),
            ("Mint", "#059669"),
            ("Sky", "#0284C7"),
            ("Peach", "#EA580C"),
            ("Lavender", "#7C3AED"),
        ]
        
        for name, color in light_themes:
            btn = self._create_theme_btn(name, color, False)
            grid_layout2.addWidget(btn)
            
        layout.addLayout(grid_layout2)
        
    def _create_theme_btn(self, name: str, color: str, is_dark: bool):
        """创建主题按钮"""
        btn = QPushButton()
        btn.setFixedSize(32, 32)
        btn.setCursor(Qt.CursorShape.PointingHand)
        btn.setToolTip(name)
        
        bg = "#0A0A0F" if is_dark else "#FFFFFF"
        _border = "#30363D" if is_dark else "#D0D7DE"
        
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                border: 2px solid {color};
                border-radius: 16px;
            }}
            QPushButton:hover {{
                transform: scale(1.1);
            }}
        """)
        
        # 点击事件
        if is_dark:
            colors = ThemePresets.DARK_THEMES.get(name, {})
        else:
            colors = ThemePresets.LIGHT_THEMES.get(name, {})
            
        btn.clicked.connect(lambda: self.theme_selected.emit(name, colors))
        
        return btn


class ThemePreviewCard(QWidget):
    """主题预览卡片"""
    
    def __init__(self, name: str, colors: dict, is_dark: bool, parent=None):
        super().__init__(parent)
        self._name = name
        self._colors = colors
        self._is_dark = is_dark
        self._setup_ui()
        
    def _setup_ui(self):
        self.setFixedSize(140, 100)
        self.setCursor(Qt.CursorShape.PointingHand)
        
        # 主色
        primary = self._colors.get("primary", "#6366F1")
        bg = self._colors.get("background", "#0A0A0F")
        
        self.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {bg},
                    stop:0.5 {self._colors.get('surface', bg)},
                    stop:1 {bg});
                border: 1px solid {self._colors.get('border', '#30363D')};
                border-radius: 12px;
            }}
            QWidget:hover {{
                border-color: {primary};
            }}
        """)
        
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制预览元素
        colors = [
            self._colors.get("primary", "#6366F1"),
            self._colors.get("accent", "#06B6D4"),
            self._colors.get("success", "#238636"),
            self._colors.get("warning", "#D29922"),
        ]
        
        # 小色块
        for i, color in enumerate(colors):
            painter.fillRect(10 + i * 30, 60, 24, 12, QColor(color))
            
        # 绘制主题名称
        from PySide6.QtGui import QFont
        painter.setPen(QColor(self._colors.get("text", "#E6EDF3")))
        font = QFont()
        font.setPointSize(10)
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(self.rect().adjusted(8, 8, -8, -50), 0, self._name)
