"""
首次使用引导 - 分步引导向导
引导用户完成初始设置
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QFrame, QComboBox, QCheckBox,
                             QLineEdit)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# 色彩系统
COLORS = {
    "primary": "#6366F1",
    "primary_end": "#8B5CF6",
    "primary_light": "#818CF8",
    "accent": "#06B6D4",
    "background": "#0A0A0F",
    "surface": "#12121A",
    "card": "#1A1A24",
    "card_elevated": "#22222E",
    "text": "#E6EDF3",
    "text_secondary": "#C9D1D9",
    "text_tertiary": "#8B949E",
    "border": "#30363D",
    "success": "#238636",
    "warning": "#D29922",
}


class StepIndicator(QWidget):
    """步骤指示器"""

    def __init__(self, steps: list, parent=None):
        super().__init__(parent)
        self._steps = steps
        self._current_step = 0
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        for i, step in enumerate(self._steps):
            # 步骤圆点
            step_dot = QLabel()
            step_dot.setFixedSize(32, 32)
            step_dot.setAlignment(Qt.AlignmentFlag.AlignCenter)

            if i == 0:
                step_dot.setText("1")
            elif i == 1:
                step_dot.setText("2")
            elif i == 2:
                step_dot.setText("3")
            else:
                step_dot.setText(str(i + 1))

            step_dot.setStyleSheet(f"""
                QLabel {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {COLORS["primary"]},
                        stop:1 {COLORS["primary_end"]});
                    color: white;
                    border-radius: 16px;
                    font-weight: 600;
                    font-size: 13px;
                }}
            """)
            layout.addWidget(step_dot)

            # 步骤名称
            if i < len(self._steps) - 1:
                step_label = QLabel(step)
                step_label.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 12px;")
                layout.addWidget(step_label)

                # 分隔线
                separator = QFrame()
                separator.setFixedSize(40, 2)
                separator.setStyleSheet(f"background: {COLORS['border']}; border-radius: 1px;")
                layout.addWidget(separator)

        layout.addStretch()

    def set_current_step(self, step: int):
        """设置当前步骤"""
        self._current_step = step
        # 更新指示器样式可以在这里添加


class StepContent(QWidget):
    """步骤内容基类"""

    def get_values(self) -> dict:
        """获取步骤数据"""
        return {}


class WelcomeStep(StepContent):
    """欢迎步骤"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 欢迎图标
        icon_label = QLabel("👋")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("font-size: 64px; background: transparent;")
        layout.addWidget(icon_label)

        # 标题
        title = QLabel("欢迎使用 Voxplore")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {COLORS['text']}; background: transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # 描述
        desc = QLabel("让我们用几分钟时间来配置您的创作环境")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 14px; background: transparent;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

        layout.addStretch()


class AIProviderStep(StepContent):
    """AI 提供商配置步骤"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(24)

        # 标题
        title = QLabel("配置 AI 服务")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {COLORS['text']}; background: transparent;")
        layout.addWidget(title)

        # 描述
        desc = QLabel("选择您要使用的 AI 服务提供商")
        desc.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 13px; background: transparent;")
        layout.addWidget(desc)

        # 提供商选择
        provider_label = QLabel("AI 服务提供商")
        provider_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px; font-weight: 600; background: transparent;")
        layout.addWidget(provider_label)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["DeepSeek", "Kimi", "Qwen", "Claude", "Gemini", "本地模型"])
        self.provider_combo.setFixedHeight(44)
        self.provider_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS["surface"]};
                color: {COLORS["text"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 10px;
                padding: 0 16px;
                font-size: 14px;
            }}
            QComboBox:hover {{
                border-color: {COLORS["primary"]};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 32px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS["surface"]};
                color: {COLORS["text"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 8px;
                padding: 4px;
            }}
        """)
        layout.addWidget(self.provider_combo)

        # API Key 输入
        api_label = QLabel("API Key（可选）")
        api_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px; font-weight: 600; background: transparent;")
        layout.addWidget(api_label)

        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("输入您的 API Key（可选）")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setFixedHeight(44)
        self.api_key_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS["surface"]};
                color: {COLORS["text"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 10px;
                padding: 0 16px;
                font-size: 14px;
            }}
            QLineEdit:hover {{
                border-color: {COLORS["primary"]};
            }}
            QLineEdit:focus {{
                border-color: {COLORS["primary"]};
                background-color: {COLORS["card"]};
            }}
        """)
        layout.addWidget(self.api_key_input)

        # 提示
        hint = QLabel("💡 您可以在设置中随时修改 AI 配置")
        hint.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 12px; background: transparent;")
        layout.addWidget(hint)

        layout.addStretch()

    def get_values(self) -> dict:
        """获取配置数据"""
        return {
            "provider": self.provider_combo.currentText(),
            "api_key": self.api_key_input.text()
        }


class PreferencesStep(StepContent):
    """偏好设置步骤"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(24)

        # 标题
        title = QLabel("个性化设置")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {COLORS['text']}; background: transparent;")
        layout.addWidget(title)

        # 描述
        desc = QLabel("根据您的使用习惯进行定制")
        desc.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 13px; background: transparent;")
        layout.addWidget(desc)

        # 主题选择
        theme_label = QLabel("界面主题")
        theme_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px; font-weight: 600; background: transparent;")
        layout.addWidget(theme_label)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["深色主题", "浅色主题", "蓝调深色", "森林绿色", "紫色主题", "橙色主题"])
        self.theme_combo.setCurrentText("深色主题")
        self.theme_combo.setFixedHeight(44)
        self.theme_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS["surface"]};
                color: {COLORS["text"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 10px;
                padding: 0 16px;
                font-size: 14px;
            }}
            QComboBox:hover {{
                border-color: {COLORS["primary"]};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 32px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS["surface"]};
                color: {COLORS["text"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 8px;
                padding: 4px;
            }}
        """)
        layout.addWidget(self.theme_combo)

        # 输出目录
        output_label = QLabel("默认输出目录")
        output_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px; font-weight: 600; background: transparent;")
        layout.addWidget(output_label)

        self.output_input = QLineEdit()
        self.output_input.setPlaceholderText("留空使用默认目录")
        self.output_input.setFixedHeight(44)
        self.output_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS["surface"]};
                color: {COLORS["text"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 10px;
                padding: 0 16px;
                font-size: 14px;
            }}
            QLineEdit:hover {{
                border-color: {COLORS["primary"]};
            }}
            QLineEdit:focus {{
                border-color: {COLORS["primary"]};
                background-color: {COLORS["card"]};
            }}
        """)
        layout.addWidget(self.output_input)

        # 选项
        options_layout = QVBoxLayout()
        options_layout.setSpacing(12)

        self.auto_save_check = QCheckBox("自动保存项目")
        self.auto_save_check.setChecked(True)
        self.auto_save_check.setStyleSheet(f"""
            QCheckBox {{
                color: {COLORS["text_secondary"]};
                font-size: 13px;
                spacing: 10px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid {COLORS["border"]};
                background-color: transparent;
            }}
            QCheckBox::indicator:checked {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {COLORS["primary"]},
                    stop:1 {COLORS["primary_end"]});
                border-color: {COLORS["primary"]};
            }}
        """)
        options_layout.addWidget(self.auto_save_check)

        self.telemetry_check = QCheckBox("发送匿名使用统计帮助改进产品")
        self.telemetry_check.setChecked(False)
        self.telemetry_check.setStyleSheet(f"""
            QCheckBox {{
                color: {COLORS["text_secondary"]};
                font-size: 13px;
                spacing: 10px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 2px solid {COLORS["border"]};
                background-color: transparent;
            }}
            QCheckBox::indicator:checked {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {COLORS["primary"]},
                    stop:1 {COLORS["primary_end"]});
                border-color: {COLORS["primary"]};
            }}
        """)
        options_layout.addWidget(self.telemetry_check)

        layout.addLayout(options_layout)

        layout.addStretch()

    def get_values(self) -> dict:
        """获取设置数据"""
        return {
            "theme": self.theme_combo.currentText(),
            "output_dir": self.output_input.text(),
            "auto_save": self.auto_save_check.isChecked(),
            "telemetry": self.telemetry_check.isChecked()
        }


class CompletionStep(StepContent):
    """完成步骤"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 完成图标
        icon_label = QLabel("🎉")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("font-size: 64px; background: transparent;")
        layout.addWidget(icon_label)

        # 标题
        title = QLabel("设置完成！")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {COLORS['text']}; background: transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # 描述
        desc = QLabel("一切准备就绪，开始您的创作之旅吧！")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 14px; background: transparent;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

        # 快捷操作提示
        tips_widget = QWidget()
        tips_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS["card"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 12px;
                padding: 16px;
            }}
        """)
        tips_layout = QVBoxLayout(tips_widget)
        tips_layout.setSpacing(12)

        tips_title = QLabel("💡 快捷提示")
        tips_title.setStyleSheet(f"color: {COLORS['text']}; font-weight: 600; font-size: 13px; background: transparent;")
        tips_layout.addWidget(tips_title)

        tips = [
            "拖放视频文件到窗口开始处理",
            "使用快捷键 Ctrl+N 创建新项目",
            "在设置中切换主题和配置 AI",
        ]

        for tip in tips:
            tip_label = QLabel(tip)
            tip_label.setWordWrap(True)
            tip_label.setStyleSheet(f"color: {COLORS['text_tertiary']}; font-size: 12px; background: transparent;")
            tips_layout.addWidget(tip_label)

        layout.addWidget(tips_widget)

        layout.addStretch()

