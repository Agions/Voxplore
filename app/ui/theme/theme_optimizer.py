"""
主题优化模块 - 提供完整的主题切换和管理功能
包含多种配色方案
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QPainter

from app.ui.components.design_system import Colors


# 预定义主题配色方案
class ThemePresets:
    """主题配色方案预设"""
    
    # 深色主题系列
    DARK_THEMES = {
        "Midnight": {
            "primary": "#6366F1",
            "primary_end": "#8B5CF6",
            "accent": "#06B6D4",
            "background": "#0A0A0F",
            "surface": "#12121A",
            "card": "#1A1A24",
            "card_elevated": "#22222E",
            "text": "#E6EDF3",
            "text_secondary": "#C9D1D9",
            "text_tertiary": "#8B949E",
            "border": "#30363D",
            "divider": "#21262D",
            "success": "#238636",
            "warning": "#D29922",
            "error": "#DA3633",
            "info": "#388BFD",
        },
        "Ocean": {
            "primary": "#0EA5E9",
            "primary_end": "#06B6D4",
            "accent": "#14B8A6",
            "background": "#0C1929",
            "surface": "#132F4C",
            "card": "#173A5E",
            "card_elevated": "#1E4976",
            "text": "#E3F2FD",
            "text_secondary": "#90CAF9",
            "text_tertiary": "#64B5F6",
            "border": "#2196F3",
            "divider": "#1565C0",
            "success": "#2E7D32",
            "warning": "#F57C00",
            "error": "#D32F2F",
            "info": "#1976D2",
        },
        "Forest": {
            "primary": "#22C55E",
            "primary_end": "#16A34A",
            "accent": "#14B8A6",
            "background": "#052E16",
            "surface": "#064E3B",
            "card": "#14532D",
            "card_elevated": "#166534",
            "text": "#ECFDF5",
            "text_secondary": "#A7F3D0",
            "text_tertiary": "#6EE7B7",
            "border": "#16A34A",
            "divider": "#15803D",
            "success": "#22C55E",
            "warning": "#F59E0B",
            "error": "#EF4444",
            "info": "#3B82F6",
        },
        "Sunset": {
            "primary": "#F97316",
            "primary_end": "#EF4444",
            "accent": "#F43F5E",
            "background": "#1A0A0A",
            "surface": "#2C1010",
            "card": "#3D1515",
            "card_elevated": "#4E1A1A",
            "text": "#FEE2E2",
            "text_secondary": "#FCA5A5",
            "text_tertiary": "#F87171",
            "border": "#DC2626",
            "divider": "#B91C1C",
            "success": "#22C55E",
            "warning": "#F59E0B",
            "error": "#EF4444",
            "info": "#3B82F6",
        },
        "Purple": {
            "primary": "#A855F7",
            "primary_end": "#7C3AED",
            "accent": "#EC4899",
            "background": "#1E1B2E",
            "surface": "#2D2A42",
            "card": "#3D3856",
            "card_elevated": "#4D456A",
            "text": "#F5F3FF",
            "text_secondary": "#C4B5FD",
            "text_tertiary": "#A78BFA",
            "border": "#7C3AED",
            "divider": "#6D28D9",
            "success": "#22C55E",
            "warning": "#F59E0B",
            "error": "#EF4444",
            "info": "#3B82F6",
        },
        "Rose": {
            "primary": "#F43F5E",
            "primary_end": "#E11D48",
            "accent": "#FB7185",
            "background": "#1A0F13",
            "surface": "#2B131A",
            "card": "#3C1821",
            "card_elevated": "#4D1D28",
            "text": "#FFE4E6",
            "text_secondary": "#FDA4AF",
            "text_tertiary": "#FB7185",
            "border": "#BE123C",
            "divider": "#9F1239",
            "success": "#22C55E",
            "warning": "#F59E0B",
            "error": "#F43F5E",
            "info": "#3B82F6",
        },
    }
    
    # 浅色主题系列
    LIGHT_THEMES = {
        "Snow": {
            "primary": "#0969DA",
            "primary_end": "#8250DF",
            "accent": "#BF3989",
            "background": "#FFFFFF",
            "surface": "#F6F8FA",
            "card": "#FFFFFF",
            "card_elevated": "#FFFFFF",
            "text": "#1F2328",
            "text_secondary": "#656D76",
            "text_tertiary": "#8C959F",
            "border": "#D0D7DE",
            "divider": "#D8DEE4",
            "success": "#1A7F37",
            "warning": "#9A6700",
            "error": "#CF222E",
            "info": "#0969DA",
        },
        "Mint": {
            "primary": "#059669",
            "primary_end": "#0891B2",
            "accent": "#0D9488",
            "background": "#ECFDF5",
            "surface": "#D1FAE5",
            "card": "#FFFFFF",
            "card_elevated": "#FFFFFF",
            "text": "#022C22",
            "text_secondary": "#064E3B",
            "text_tertiary": "#047857",
            "border": "#A7F3D0",
            "divider": "#D1FAE5",
            "success": "#059669",
            "warning": "#D97706",
            "error": "#DC2626",
            "info": "#0284C7",
        },
        "Sky": {
            "primary": "#0284C7",
            "primary_end": "#6366F1",
            "accent": "#8B5CF6",
            "background": "#F0F9FF",
            "surface": "#E0F2FE",
            "card": "#FFFFFF",
            "card_elevated": "#FFFFFF",
            "text": "#0C4A6E",
            "text_secondary": "#075985",
            "text_tertiary": "#0369A1",
            "border": "#BAE6FD",
            "divider": "#E0F2FE",
            "success": "#059669",
            "warning": "#D97706",
            "error": "#DC2626",
            "info": "#0284C7",
        },
        "Peach": {
            "primary": "#EA580C",
            "primary_end": "#DC2626",
            "accent": "#F43F5E",
            "background": "#FFF7ED",
            "surface": "#FFEDD5",
            "card": "#FFFFFF",
            "card_elevated": "#FFFFFF",
            "text": "#7C2D12",
            "text_secondary": "#9A3412",
            "text_tertiary": "#C2410C",
            "border": "#FED7AA",
            "divider": "#FFEDD5",
            "success": "#059669",
            "warning": "#D97706",
            "error": "#DC2626",
            "info": "#0284C7",
        },
        "Lavender": {
            "primary": "#7C3AED",
            "primary_end": "#A855F7",
            "accent": "#EC4899",
            "background": "#FAF5FF",
            "surface": "#F3E8FF",
            "card": "#FFFFFF",
            "card_elevated": "#FFFFFF",
            "text": "#5B21B6",
            "text_secondary": "#6D28D9",
            "text_tertiary": "#7C3AED",
            "border": "#E9D5FF",
            "divider": "#F3E8FF",
            "success": "#059669",
            "warning": "#D97706",
            "error": "#DC2626",
            "info": "#0284C7",
        },
    }
    
    @classmethod
    def get_all_themes(cls):
        """获取所有主题"""
        return {
            "深色主题": cls.DARK_THEMES,
            "浅色主题": cls.LIGHT_THEMES,
        }
    
    @classmethod
    def get_theme_names(cls, theme_type: str = None):
        """获取主题名称列表"""
        if theme_type == "dark":
            return list(cls.DARK_THEMES.keys())
        elif theme_type == "light":
            return list(cls.LIGHT_THEMES.keys())
        else:
            return list(cls.DARK_THEMES.keys()) + list(cls.LIGHT_THEMES.keys())


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
        dark_label.setStyleSheet(f"color: {Colors.TextSecondary}; font-size: 12px; font-weight: 600;")
        layout.addWidget(dark_label)
        
        dark_grid = QHBoxLayout()
        dark_grid.setSpacing(12)
        
        for name, colors in ThemePresets.DARK_THEMES.items():
            btn = self._create_theme_button(name, colors, is_dark=True)
            dark_grid.addWidget(btn)
            
        layout.addLayout(dark_grid)
        
        # 浅色主题区域
        light_label = QLabel("浅色主题")
        light_label.setStyleSheet(f"color: {Colors.TextSecondary}; font-size: 12px; font-weight: 600;")
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
                    stop:0.5 {colors.get('surface', bg)},
                    stop:1 {bg});
                border: 2px solid {colors.get('border', '#30363D')};
                border-radius: 8px;
            }}
            QPushButton:hover {{
                border-color: {primary};
            }}
        """)
        
        # 点击事件
        btn.clicked.connect(lambda: self.theme_selected.emit(name, colors))
        
        return btn


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


def generate_theme_stylesheet(colors: dict, is_dark: bool = True) -> str:
    """根据配色生成完整的主题样式表"""
    
    if is_dark:
        template = """
/* Generated Theme Stylesheet - {name} */

QWidget {{
    background-color: {background};
    color: {text};
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', sans-serif;
    font-size: 13px;
}}

QMainWindow {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {background},
        stop:0.5 {surface},
        stop:1 {background});
}}

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

QPushButton[class="primary"]:pressed {{
    transform: scale(0.98);
}}

QPushButton[class="secondary"] {{
    background-color: transparent;
    border: 1px solid {border};
    color: {text_secondary};
    border-radius: 8px;
    padding: 8px 16px;
}}

QPushButton[class="secondary"]:hover {{
    background-color: {card};
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
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {primary},
        stop:1 {primary_end});
    color: white;
}}

QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {primary},
        stop:1 {primary_end});
}}

QMenu {{
    background-color: {surface};
    border: 1px solid {border};
    border-radius: 8px;
}}

QMenu::item:selected {{
    background-color: {primary};
}}

QToolTip {{
    background-color: {card_elevated};
    color: {text};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 6px 10px;
}}
"""
    else:
        template = """
/* Generated Theme Stylesheet - {name} */

QWidget {{
    background-color: {background};
    color: {text};
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', sans-serif;
    font-size: 13px;
}}

QMainWindow {{
    background-color: {background};
}}

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

QPushButton[class="secondary"] {{
    background-color: transparent;
    border: 1px solid {border};
    color: {text_secondary};
    border-radius: 8px;
    padding: 8px 16px;
}}

QPushButton[class="secondary"]:hover {{
    background-color: {surface};
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
    background-color: {primary};
    color: white;
}}

QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {primary},
        stop:1 {primary_end});
}}

QMenu {{
    background-color: {card};
    border: 1px solid {border};
    border-radius: 8px;
}}

QMenu::item:selected {{
    background-color: {primary};
    color: white;
}}

QToolTip {{
    background-color: {card_elevated};
    color: {text};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 6px 10px;
}}
"""
    
    # 填充颜色
    primary_light = colors.get("primary", "#6366F1")
    if is_dark:
        # 浅化主色
        primary_light = primary_light  # 可以进一步处理变亮
    
    result = template.format(
        name=colors.get("name", "Custom Theme"),
        **colors,
        primary_light=primary_light
    )
    
    return result
