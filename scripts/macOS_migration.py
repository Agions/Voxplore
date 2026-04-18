#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Voxplore macOS 设计系统迁移工具
自动将现有 UI 迁移到 macOS 设计系统

使用说明:
python macOS_migration.py --auto
"""

import os
import sys
import shutil
from pathlib import Path

# PyQt6 导入

class MigrationManager:
    """迁移管理器 - 负责UI迁移"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.resources_dir = self.project_root / "resources"
        self.styles_dir = self.resources_dir / "styles"
        self.macOS_styles_dir = self.styles_dir / "macOS"

        # 输出目标
        self.main_window_path = self.project_root / "app/ui/main/main_window.py"
        self.nav_bar_path = self.project_root / "app/ui/main/components/navigation_bar.py"
        self.home_page_path = self.project_root / "app/ui/main/pages/home_page.py"

    def execute_migration(self) -> bool:
        """执行完整迁移"""
        print("=" * 60)
        print("🚀 Voxplore macOS 设计系统迁移工具")
        print("=" * 60)

        steps = [
            ("1. 备份现有文件", self.backup_files),
            ("2. 验证样式文件", self.validate_styles),
            ("3. 创建主题管理器", self.create_theme_manager),
            ("4. 更新主窗口", self.update_main_window),
            ("5. 更新导航组件", self.update_navigation_bar),
            ("6. 更新首页", self.update_home_page),
            ("7. 创建资源文件", self.create_resources_qrc),
            ("8. 更新应用入口", self.update_main_entry),
        ]

        for step_name, step_func in steps:
            print(f"\n{'='*60}")
            print(f"⏳ {step_name}")
            print(f"{'='*60}")
            try:
                success = step_func()
                if success:
                    print(f"✅ {step_name} - 完成")
                else:
                    print(f"⚠️  {step_name} - 跳过或部分完成")
                    return False
            except Exception as e:
                print(f"❌ {step_name} - 失败: {e}")
                return False

        print(f"\n{'='*60}")
        print("🎉 迁移完成！")
        print("="*60)
        print("\n下一步：")
        print("1. 编译资源: pyrcc6 resources/resources.qrc -o app/resources_rc.py")
        print("2. 运行应用: python main.py")
        print("3. 检查视觉效果")
        return True

    def backup_files(self) -> bool:
        """备份原始文件"""
        backup_dir = self.project_root / "backup_20251217"

        if backup_dir.exists():
            print(f"备份目录已存在: {backup_dir}")
            confirm = input("是否重新备份? (y/n): ")
            if confirm.lower() != 'y':
                return True

        backup_dir.mkdir(exist_ok=True)

        files_to_backup = [
            self.main_window_path,
            self.nav_bar_path,
            self.home_page_path,
            self.styles_dir / "dark_theme.qss",
            self.styles_dir / "light_theme.qss",
            self.styles_dir / "antd_style.qss",
        ]

        for file_path in files_to_backup:
            if file_path.exists():
                target = backup_dir / file_path.name
                shutil.copy2(file_path, target)
                print(f"  📦 备份: {file_path.name}")

        print(f"\n📁 备份完成，保存至: {backup_dir}")
        return True

    def validate_styles(self) -> bool:
        """验证样式文件是否存在"""
        required_files = [
            "macOS_desktop_stylesheet.qss",
            "_reset.css", "_typography.css", "_layout.css",
            "_components.css", "_utils.css"
        ]

        missing = []
        for file in required_files:
            if not (self.macOS_styles_dir / file).exists():
                missing.append(file)

        if missing:
            print(f"❌ 缺少必要的样式文件: {missing}")
            print("请先运行之前的样式生成代码")
            return False

        print(f"✅ 找到 {len(required_files)} 个样式文件")
        for file in required_files:
            print(f"  📄 {file}")
        return True

    def create_theme_manager(self) -> bool:
        """创建新的主题管理器"""
        theme_manager_path = self.project_root / "app/core/macOS_theme_manager.py"
        theme_manager_path.parent.mkdir(parents=True, exist_ok=True)

        content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
macOS 主题管理器 - 负责应用和切换 macOS 设计系统
实现动态主题管理、资源加载和状态同步
"""

import os
from pathlib import Path
from typing import Optional, Callable
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QFile, QTextStream, Signal, QObject
from PySide6.QtGui import QFont


class macOS_ThemeManager(QObject):
    """macOS 设计系统主题管理器"""

    # 信号
    theme_changed = Signal(str)      # 主题切换信号
    before_apply = Signal()          # 样式应用前
    after_apply = Signal()           # 样式应用后

    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.current_theme = "dark"
        self._cache = {}
        self._fallback_stylesheet = ""

        # 获取项目根目录
        self.project_root = Path(__file__).parent.parent.parent
        self.styles_dir = self.project_root / "resources" / "styles" / "macOS"

        print(f"🖥️  macOS Theme Manager 初始化")
        print(f"   工作目录: {self.project_root}")
        print(f"   样式目录: {self.styles_dir}")

    def load_system(self, theme: str = "dark") -> bool:
        """加载 macOS 设计系统"""
        print(f"\\n🎨 加载 macOS 设计系统 ({theme} 模式)")

        self.before_apply.emit()

        try:
            # 优先使用 QSS 资源文件
            stylesheet = self._load_from_resources(theme)

            # 如果资源不可用，使用文件系统
            if not stylesheet:
                stylesheet = self._load_from_filesystem(theme)

            # 如果依然失败，使用回退样式
            if not stylesheet:
                print("⚠️  无法加载样式，使用回退样式")
                stylesheet = self._get_fallback_style()

            # 应用样式
            self.app.setStyleSheet(stylesheet)
            self.current_theme = theme

            # 设置应用字体
            self._set_app_font()

            self.after_apply.emit()
            self.theme_changed.emit(theme)

            print("✅ macOS 设计系统应用成功")
            print("   - 色彩系统已配置")
            print("   - 排版系统已配置")
            print("   - 组件样式已应用")
            return True

        except Exception as e:
            print(f"❌ 设计系统应用失败: {e}")
            return False

    def _load_from_resources(self, theme: str) -> str:
        """尝试从 Qt 资源加载"""
        if theme == "dark":
            resource_path = ":/styles/macOS/macOS_desktop_stylesheet.qss"
        else:
            resource_path = f":/styles/macOS/macOS_{theme}.qss"

        if resource_path in self._cache:
            return self._cache[resource_path]

        file = QFile(resource_path)
        if file.exists() and file.open(QFile.ReadOnly | QFile.Text):
            content = QTextStream(file).readAll()
            file.close()
            self._cache[resource_path] = content
            print(f"  ✅ 从资源加载: {resource_path}")
            return content

        return ""

    def _load_from_filesystem(self, theme: str) -> str:
        """从文件系统加载"""
        if theme == "dark":
            file_path = self.styles_dir / "macOS_desktop_stylesheet.qss"
        else:
            file_path = self.styles_dir / f"macOS_{theme}.qss"

        if file_path.exists():
            content = file_path.read_text(encoding='utf-8')
            self._cache[str(file_path)] = content
            print(f"  ✅ 从文件加载: {file_path}")
            return content

        print(f"  ❌ 文件不存在: {file_path}")
        return ""

    def _set_app_font(self):
        """设置应用字体 - 使用系统字体栈"""
        font = QFont()
        font.setFamily("-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif")
        font.setPixelSize(13)  # macOS 默认字号
        self.app.setFont(font)
        print("  ✅ 字体已设置: macOS 系统字体")

    def _get_fallback_style(self) -> str:
        """获取回退样式"""
        return """
            QWidget {
                background-color: #1E1E1E;
                color: #FFFFFF;
                font-family: -apple-system, sans-serif;
                font-size: 13px;
            }
            QPushButton {
                background-color: #3A3A3A;
                color: #FFFFFF;
                border: 1px solid rgba(255,255,255,0.1);
                padding: 6px 16px;
                border-radius: 6px;
                min-height: 28px;
            }
            QPushButton:hover {
                background-color: #2D2D2D;
                border-color: rgba(255,255,255,0.2);
            }
            QLineEdit {
                background-color: #3A3A3A;
                color: #FFFFFF;
                border: 1px solid rgba(255,255,255,0.1);
                padding: 6px 12px;
                border-radius: 6px;
                min-height: 28px;
            }
        """

    def get_current_theme(self) -> str:
        """获取当前主题"""
        return self.current_theme

    def toggle_theme(self) -> str:
        """切换主题"""
        new_theme = "light" if self.current_theme == "dark" else "dark"
        self.load_system(new_theme)
        return new_theme

    def refresh(self):
        """刷新当前主题"""
        self.load_system(self.current_theme)


# 全局实例
_theme_manager_instance = None


def get_theme_manager(app: Optional[QApplication] = None) -> macOS_ThemeManager:
    """获取主题管理器单例"""
    global _theme_manager_instance
    if _theme_manager_instance is None:
        if app is None:
            app = QApplication.instance()
        _theme_manager_instance = macOS_ThemeManager(app)
    return _theme_manager_instance


def apply_macos_theme(app: QApplication, theme: str = "dark") -> bool:
    """快速应用 macOS 主题的便捷函数"""
    manager = get_theme_manager(app)
    return manager.load_system(theme)


__all__ = ["macOS_ThemeManager", "get_theme_manager", "apply_macos_theme"]
'''

        theme_manager_path.write_text(content, encoding='utf-8')
        print(f"  📄 创建: {theme_manager_path.name}")
        return True

    def update_main_window(self) -> bool:
        """更新主窗口"""
        print(f"  📝 正在迁移: {self.main_window_path.name}")

        # 读取原始内容
        content = self.main_window_path.read_text(encoding='utf-8')

        # 修改导入
        new_imports = '''from ...core.macOS_theme_manager import get_theme_manager, apply_macos_theme'''

        # 在现有 imports 末尾添加
        if "from ...core.icon_manager import" in content:
            content = content.replace(
                "from ...core.icon_manager import get_icon_manager, get_icon",
                "from ...core.icon_manager import get_icon_manager, get_icon\n" + new_imports
            )

        # 修改 _apply_theme 方法
        old_apply_theme = '''    def _apply_theme(self):
        """应用主题"""
        try:
            import os

            # 使用正确的资源文件路径
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            styles_dir = os.path.join(project_root, "resources", "styles")

            # 检查样式文件是否存在
            dark_stylesheet_path = os.path.join(styles_dir, "dark_theme.qss")
            light_stylesheet_path = os.path.join(styles_dir, "light_theme.qss")

            # 读取主题样式表
            stylesheet = ""
            if self.is_dark_theme and os.path.exists(dark_stylesheet_path):
                with open(dark_stylesheet_path, "r", encoding="utf-8") as f:
                    stylesheet = f.read()
            elif os.path.exists(light_stylesheet_path):
                with open(light_stylesheet_path, "r", encoding="utf-8") as f:
                    stylesheet = f.read()

            # 应用样式表
            self.setStyleSheet(stylesheet)

            # 更新图标主题
            from ...core.icon_manager import set_icon_theme
            set_icon_theme("dark" if self.is_dark_theme else "light")

            self.theme_changed.emit("dark" if self.is_dark_theme else "light")
            self.logger.info("主题应用成功")

        except Exception as e:
            self.logger.error(f"应用主题失败: {e}")
            # 应用基础样式作为回退
            self.setStyleSheet("")'''

        new_apply_theme = '''    def _apply_theme(self):
        """应用 macOS 设计系统主题"""
        try:
            # 使用新的 macOS 主题管理器
            theme_name = "dark" if self.is_dark_theme else "light"
            success = apply_macos_theme(self.application, theme_name)

            if success:
                # 更新图标主题
                from ...core.icon_manager import set_icon_theme
                set_icon_theme(theme_name)

                self.theme_changed.emit(theme_name)
                self.logger.info("macOS 设计系统应用成功")
            else:
                # 回退到无样式
                self.setStyleSheet("")
                self.logger.warning("macOS 主题应用失败，使用默认样式")

        except Exception as e:
            self.logger.error(f"应用主题失败: {e}")
            self.setStyleSheet("")'''

        content = content.replace(old_apply_theme, new_apply_theme)

        # 修改 _apply_style 方法（可选，我们可能不需要这个了）
        if "def _apply_style(self):" in content:
            old_style = '''    def _apply_style(self):
        """应用样式表"""
        try:
            # 设置应用程序样式
            QApplication.setStyle(self.window_config.style)
        except Exception as e:
            self.logger.error(f"应用样式失败: {e}")'''

            new_style = '''    def _apply_style(self):
        """应用基础样式（被 macOS 主题管理器处理）"""
        # macOS 主题管理器已处理所有样式
        # 此方法保留用于未来扩展
        pass'''

            content = content.replace(old_style, new_style)

        # 修改 _init_ui，简化样式应用
        if "# 应用样式" in content:
            content = content.replace(
                "# 应用样式\n        self._apply_style()\n        self._apply_theme()",
                "# 应用 macOS 设计系统\n        self._apply_theme()"
            )

        self.main_window_path.write_text(content, encoding='utf-8')
        print("    ✅ 主窗口样式逻辑已更新")
        return True

    def update_navigation_bar(self) -> bool:
        """更新导航组件"""
        print(f"  📝 正在迁移: {self.nav_bar_path.name}")

        content = self.nav_bar_path.read_text(encoding='utf-8')

        # 替换 NavigationButton 类 - 移除内联样式
        old_nav_button = '''from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel,
    QFrame, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QColor, QPalette


class NavigationButtonStyle:
    \"\"\"导航按钮样式\"\"\"

    def __init__(self):
        self.normal_bg = QColor(45, 45, 45)
        self.hover_bg = QColor(60, 60, 60)
        self.selected_bg = QColor(33, 150, 243)
        self.normal_text = QColor(200, 200, 200)
        self.hover_text = QColor(255, 255, 255)
        self.selected_text = QColor(255, 255, 255)
        self.border_radius = 8
        self.padding = 12
        self.font_size = 14
        self.font_weight = QFont.Weight.Normal


class NavigationButton(QPushButton):
    \"\"\"导航按钮\"\"\"

    def __init__(self, text: str, icon: str = \"\", style: NavigationButtonStyle = None):
        super().__init__()
        self.text = text
        self.icon = icon
        self.style = style or NavigationButtonStyle()
        self.is_selected = False
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        \"\"\"设置UI\"\"\"\n        if self.icon:\n            self.setText(f"{self.icon} {self.text}")\n        else:\n            self.setText(self.text)\n        # 设置字体\n        font = QFont("Microsoft YaHei", self.style.font_size)\n        font.setWeight(self.style.font_weight)\n        self.setFont(font)\n        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)\n        self.setFixedHeight(50)\n        self._update_style()

    def _connect_signals(self) -> None:
        \"\"\"连接信号\"\"\"
        self.pressed.connect(self._on_pressed)
        self.released.connect(self._on_released)

    def _update_style(self) -> None:
        \"\"\"更新样式\"\"\"
        if self.is_selected:
            bg_color = self.style.selected_bg
            text_color = self.style.selected_text
            font_weight = QFont.Weight.Bold
        else:
            bg_color = self.style.normal_bg
            text_color = self.style.normal_text
            font_weight = QFont.Weight.Normal

        stylesheet = f\"\"\"
            QPushButton {{
                background-color: {bg_color.name()};
                color: {text_color.name()};
                border: none;
                border-radius: {self.style.border_radius}px;
                padding: {self.style.padding}px;
                font-weight: {font_weight};
            }}
            QPushButton:hover {{
                background-color: {self.style.hover_bg.name()};
                color: {self.style.hover_text.name()};
            }}
            QPushButton:pressed {{
                background-color: {self.style.selected_bg.name()};
            }}
        \"\"\"
        self.setStyleSheet(stylesheet)

    def set_selected(self, selected: bool) -> None:
        \"\"\"设置选中状态\"\"\"
        if self.is_selected != selected:
            self.is_selected = selected
            self._update_style()

    def _on_pressed(self) -> None:
        \"\"\"按下事件\"\"\"
        self._update_style()

    def _on_released(self) -> None:
        \"\"\"释放事件\"\"\"
        self._update_style()'''

        new_nav_button = '''from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel,
    QFrame, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, Signal, QSize


class NavigationButton(QPushButton):
    """导航按钮 - 使用 QSS 类名，支持 macOS 风格"""

    def __init__(self, text: str, icon: str = ""):
        super().__init__()
        self.text = text
        self.icon = icon
        self.is_selected = False

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """设置UI - 仅配置结构，样式由QSS管理"""
        # 设置文本
        if self.icon:
            self.setText(f"{self.icon} {self.text}")
        else:
            self.setText(self.text)

        # 设置大小策略
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(32)  # macOS 导航项标准高度

        # 应用 macOS 样式类
        self.setProperty("class", "nav-item")

        # 启用悬停检测
        self.setAttribute(Qt.WA_Hover, True)

        # 设置鼠标指针
        self.setCursor(Qt.PointingHandCursor)

    def _connect_signals(self) -> None:
        """连接信号"""
        self.pressed.connect(self._on_pressed)
        self.released.connect(self._on_released)

    def _on_pressed(self) -> None:
        """按下事件 - 视觉反馈"""
        self.setProperty("pressed", True)
        self.style().unpolish(self)
        self.style().polish(self)

    def _on_released(self) -> None:
        """释放事件 - 恢复状态"""
        self.setProperty("pressed", False)
        self.style().unpolish(self)
        self.style().polish(self)

    def set_selected(self, selected: bool) -> None:
        """设置选中状态"""
        if self.is_selected != selected:
            self.is_selected = selected
            if selected:
                self.setProperty("class", "nav-item active")
                self.setCheckable(True)
                self.setChecked(True)
            else:
                self.setProperty("class", "nav-item")
                self.setCheckable(False)
                self.setChecked(False)

            # 刷新样式
            self.style().unpolish(self)
            self.style().polish(self)
            self.update()'''

        content = content.replace(old_nav_button, new_nav_button)

        # 更新 NavigationBar 的背景和布局
        old_nav_bar_init = '''    def _setup_ui(self) -> None:
        \"\"\"设置UI\"\"\"
        # 设置窗口部件属性
        self.setObjectName(\"navigation_bar\")\n        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)\n        self.setFixedHeight(60)\n\n        # 设置背景色\n        self.setAutoFillBackground(True)\n        palette = self.palette()\n        palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))\n        self.setPalette(palette)'''

        new_nav_bar_init = '''    def _setup_ui(self) -> None:
        """设置UI - 使用 macOS 样式编辑器"""
        # 设置窗口部件属性 \n        self.setObjectName(\"nav_sidebar\")  # 匹配 QSS 选择器\n        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)\n        self.setFixedHeight(32)  # 紧凑设计\n\n        # 不再手动设置背景，由 QSS 管理\n        # 仍需设置以避免闪烁\n        self.setAttribute(Qt.WA_StyledBackground, True)'''

        content = content.replace(old_nav_bar_init, new_nav_bar_init)

        # 更新左侧创建区域
        old_left = '''    def _create_left_section(self) -> QHBoxLayout:
        \"\"\"创建左侧区域\"\"\"
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Logo
        logo_label = QLabel(\"🎬\")\n        logo_label.setStyleSheet(\"font-size: 24px;\")\n        layout.addWidget(logo_label)\n\n        # 标题\n        title_label = QLabel(\"Voxplore\")\n        title_label.setStyleSheet(\"\"\"\n            QLabel {\n                color: #FFFFFF;\n                font-size: 18px;\n                font-weight: bold;\n            }\n        \"\"\")\n        layout.addWidget(title_label)\n\n        return layout'''

        new_left = '''    def _create_left_section(self) -> QHBoxLayout:
        """创建左侧区域 - 应用 macOS 样式"""
        layout = QHBoxLayout()
        layout.setContentsMargins(16, 0, 0, 0)  # 左侧内边距
        layout.setSpacing(10)

        # Logo
        logo_label = QLabel(\"🎬\")\n        logo_label.setProperty("class", "app-icon")\n        layout.addWidget(logo_label)\n\n        # 标题\n        title_label = QLabel(\"Voxplore\")\n        title_label.setProperty("class", "app-title")\n        layout.addWidget(title_label)\n\n        return layout'''

        content = content.replace(old_left, new_left)

        self.nav_bar_path.write_text(content, encoding='utf-8')
        print("    ✅ 导航组件已更新")
        return True

    def update_home_page(self) -> bool:
        """更新首页"""
        print(f"  📝 正在迁移: {self.home_page_path.name}")

        content = self.home_page_path.read_text(encoding='utf-8')

        # 修改标题区域
        content = self._update_home_title_section(content)

        # 修改快捷操作区域
        content = self._update_home_quick_actions(content)

        # 修改欢迎区域
        content = self._update_home_welcome(content)

        # 修改其他区域
        content = self._update_home_sections(content)

        self.home_page_path.write_text(content, encoding='utf-8')
        print("    ✅ 首页组件已更新")
        return True

    def _update_home_title_section(self, content: str) -> str:
        """迁移标题区域"""

        # 匹配标题创建方法
        _pattern = r'(def _create_title_section\(self\).*?)(return widget)'

        def replace_title(match):
            old_code = match.group(1)
            return old_code + '''# 主标题
        title_label = QLabel("Voxplore")
        title_label.setProperty("class", "title-4xl")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("")  # 清除旧样式，使用类名

        # 副标题
        subtitle_label = QLabel("专业的AI视频编辑器")
        subtitle_label.setProperty("class", "text-lg text-muted")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("")  # 清除旧样式

        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)

        # 添加垂直间距
        layout.addSpacing(8)

        return widget'''

        # 这里的替换逻辑需要调整，因为原有代码结构复杂
        # 简化成直接替换核心部分
        old_title_styles = '''        # 主标题
        title_label = QLabel("Voxplore")
        title_label.setObjectName("mainTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(\"\"\"
            QLabel#mainTitle {
                font-size: 36px;
                font-weight: bold;
                color: #2196F3;
                margin: 10px;
            }
        \"\"\")

        # 副标题
        subtitle_label = QLabel("专业的AI视频编辑器")
        subtitle_label.setObjectName("subTitle")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet(\"\"\"
            QLabel#subTitle {
                font-size: 18px;
                color: #666;
                margin: 5px;
            }
        \"\"\")'''

        new_title_styles = '''        # 主标题
        title_label = QLabel("Voxplore")
        title_label.setProperty("class", "title-4xl")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 副标题
        subtitle_label = QLabel("专业的AI视频编辑器")
        subtitle_label.setProperty("class", "text-lg text-muted")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)'''

        return content.replace(old_title_styles, new_title_styles)

    def _update_home_quick_actions(self, content: str) -> str:
        """迁移快捷操作区域"""
        old_button = '''            btn = QPushButton(icon, text)
            btn.setMinimumSize(140, 80)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(tooltip)
            btn.setStyleSheet(\"\"\"
                QPushButton {
                    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                    color: #2c3e50;
                    border: none;
                    border-radius: 12px;
                    font-size: 13px;
                    font-weight: 500;
                    padding: 12px 8px;
                    text-align: center;
                }
                QPushButton:hover {
                    background: linear-gradient(135deg, #e0e7ff 0%, #a5b4fc 100%);
                    color: #1e40af;
                }
                QPushButton:pressed {
                    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                    color: white;
                }
            \"\"\")'''

        new_button = '''            btn = QPushButton(icon, text)
            btn.setMinimumSize(120, 48)  # 紧凑型按钮，适配 macOS
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(tooltip)
            btn.setProperty("class", "secondary")  # 使用次级按钮样式
            # 自动应用 QSS，无需内联样式'''

        return content.replace(old_button, new_button)

    def _update_home_welcome(self, content: str) -> str:
        """迁移欢迎区域"""
        old_welcome = '''        widget.setStyleSheet(\"\"\"
            QFrame#welcomeSection {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border: none;
                border-radius: 12px;
            }
        \"\"\")'''

        # macOS 风格：简洁，无渐变，使用卡片样式
        new_welcome = '''        # 使用 macOS 风格的卡片替代渐变
        widget.setProperty("class", "card card-elevated")
        widget.setStyleSheet("")  # 由 QSS 管理
        # 不再使用渐变背景，改用深色卡片'''

        return content.replace(old_welcome, new_welcome)

    def _update_home_sections(self, content: str) -> str:
        """迁移其他区域"""
        # 更新所有部分的样式，移除内联 CSS，添加 property 类名
        updates = [
            ('widget.setObjectName("quickActionsSection")', 'widget.setProperty("class", "card")\n        widget.setStyleSheet("")'),
            ('widget.setObjectName("aiConfigSection")', 'widget.setProperty("class", "card")\n        widget.setStyleSheet("")'),
            ('widget.setObjectName("statusSection")', 'widget.setProperty("class", "card")\n        widget.setStyleSheet("")'),
            ('widget.setObjectName("recentProjectsSection")', 'widget.setProperty("class", "card")\n        widget.setStyleSheet("")'),
            # 状态标签
            ('title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px 0;")', 'title_label.setProperty("class", "title-xl")'),
            ('value_widget.setStyleSheet(f"color: {color};")', '# 颜色在 QSS 中定义，保留文字内容\n            # value_widget.setStyleSheet("")  # 如果需要状态色，使用 badge 类'),
            # 项目按钮
            ('project_btn.setStyleSheet("text-align: left; padding: 8px; border: 1px solid #ddd; background-color: white;")', 'project_btn.setProperty("class", "secondary")'),
        ]

        for old, new in updates:
            content = content.replace(old, new)

        return content

    def create_resources_qrc(self) -> bool:
        """创建 Qt 资源文件"""
        qrc_path = self.resources_dir / "resources.qrc"
        qrc_content = '''<?xml version="1.0" encoding="UTF-8"?>
<RCC version="1.0">
    <qresource prefix="/styles/macOS">
        <file alias="macOS_desktop_stylesheet.qss">resources/styles/macOS/macOS_desktop_stylesheet.qss</file>
        <file alias="_reset.css">resources/styles/macOS/_reset.css</file>
        <file alias="_typography.css">resources/styles/macOS/_typography.css</file>
        <file alias="_layout.css">resources/styles/macOS/_layout.css</file>
        <file alias="_components.css">resources/styles/macOS/_components.css</file>
        <file alias="_utils.css">resources/styles/macOS/_utils.css</file>
    </qresource>
</RCC>'''

        qrc_path.write_text(qrc_content, encoding='utf-8')
        print(f"  📄 创建: {qrc_path.name}")
        return True

    def update_main_entry(self) -> bool:
        """更新应用启动入口"""
        main_file = self.project_root / "main.py"

        if not main_file.exists():
            print(f"  ⚠️  主入口文件不存在: {main_file}")
            return False

        content = main_file.read_text(encoding='utf-8')

        # 检查是否已更新
        if "apply_macos_theme" in content:
            print("  ℹ️  主入口已包含 macOS 主题，无需更新")
            return True

        # 在 import 区域后添加资源导入
        old_imports = '''from app.core.application import Application
from app.ui.main.main_window import MainWindow'''

        new_imports = '''from app.core.application import Application
from app.ui.main.main_window import MainWindow
from app.core.macOS_theme_manager import apply_macos_theme  # 新主题管理器'''

        content = content.replace(old_imports, new_imports)

        # 在主窗口显示之前应用主题
        old_startup = '''        # 创建并显示主窗口
        main_window = MainWindow(app)
        main_window.show()

        # 进入事件循环
        sys.exit(app.exec())'''

        new_startup = '''        # 创建主窗口
        main_window = MainWindow(app)

        # 应用 macOS 设计系统（在显示前应用，避免闪烁）
        apply_macos_theme(app, "dark")

        # 显示窗口
        main_window.show()

        # 进入事件循环
        sys.exit(app.exec())'''

        content = content.replace(old_startup, new_startup)

        main_file.write_text(content, encoding='utf-8')
        print(f"  📄 更新: {main_file.name}")
        print("    ✅ 添加了主入口的 macOS 主题应用")
        return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Voxplore macOS 设计系统迁移工具")
    parser.add_argument("--project", default=".", help="项目根目录路径")
    parser.add_argument("--auto", action="store_true", help="自动执行完整迁移")

    args = parser.parse_args()

    project_root = os.path.abspath(args.project)

    if not os.path.exists(project_root):
        print(f"❌ 项目目录不存在: {project_root}")
        sys.exit(1)

    print(f"📁 项目根目录: {project_root}")

    migrator = MigrationManager(project_root)

    if args.auto:
        success = migrator.execute_migration()
        if success:
            print("\\n" + "="*60)
            print("🎉 迁移成功！")
            print("="*60)
            print("\\n📋 后续步骤：")
            print("1. 编译资源：pyrcc6 resources/resources.qrc -o app/resources_rc.py")
            print("2. 运行测试：python main.py")
            sys.exit(0)
        else:
            print("\\n❌ 迁移失败")
            sys.exit(1)
    else:
        print("\n可用选项：")
        print("  python macOS_migration.py --auto  # 自动执行完整迁移")
        print("\n手动步骤：")
        print("  1. 单独运行每个迁移步骤")
        print("  2. 编译 Qt 资源")
        print("  3. 测试并验证")
        print("\n使用 --auto 执行全自动迁移。")