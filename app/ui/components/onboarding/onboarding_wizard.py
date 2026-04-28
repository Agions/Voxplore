"""
首次使用引导 - 分步引导向导
引导用户完成初始设置
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame, QComboBox, QCheckBox,
                             QLineEdit)
from PySide6.QtCore import Qt, Signal
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


class OnboardingWizard(QWidget):
    """首次使用引导向导"""

    # 信号定义
    finished = Signal(dict)  # 完成信号，传递配置数据
    skipped = Signal()  # 跳过信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_step = 0
        self._setup_ui()

    def _setup_ui(self):
        """设置 UI"""
        self.setFixedSize(550, 500)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Dialog
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 主容器
        main_widget = QWidget(self)
        main_widget.setFixedSize(550, 500)
        main_widget.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {COLORS["background"]},
                    stop:0.5 {COLORS["surface"]},
                    stop:1 {COLORS["background"]});
                border: 1px solid {COLORS["border"]};
                border-radius: 20px;
            }}
        """)

        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(20)

        # 步骤指示器
        self.step_indicator = StepIndicator(["欢迎", "AI 配置", "偏好设置"])
        layout.addWidget(self.step_indicator)

        # 分隔线
        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"background: {COLORS['border']};")
        layout.addWidget(separator)

        # 步骤内容区域
        self.content_stack = QWidget()
        self.content_layout = QVBoxLayout(self.content_stack)
        self.content_layout.setContentsMargins(16, 16, 16, 16)

        # 创建各步骤
        self.steps = [
            WelcomeStep(),
            AIProviderStep(),
            PreferencesStep(),
            CompletionStep()
        ]

        for step in self.steps:
            self.content_layout.addWidget(step)

        # 初始显示第一步
        self._show_step(0)

        layout.addWidget(self.content_stack)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        # 上一步按钮
        self.prev_btn = QPushButton("上一步")
        self.prev_btn.setFixedHeight(40)
        self.prev_btn.setCursor(Qt.CursorShape.PointingHand)
        self.prev_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["surface"]};
                color: {COLORS["text_secondary"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 10px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {COLORS["card"]};
                border-color: {COLORS["primary"]};
                color: {COLORS["text"]};
            }}
        """)
        self.prev_btn.clicked.connect(self._prev_step)
        button_layout.addWidget(self.prev_btn)

        button_layout.addStretch()

        # 跳过按钮
        self.skip_btn = QPushButton("跳过")
        self.skip_btn.setCursor(Qt.CursorShape.PointingHand)
        self.skip_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLORS["text_tertiary"]};
                border: none;
                font-size: 13px;
            }}
            QPushButton:hover {{
                color: {COLORS["text_secondary"]};
            }}
        """)
        self.skip_btn.clicked.connect(self._on_skip)
        button_layout.addWidget(self.skip_btn)

        # 下一步/完成按钮
        self.next_btn = QPushButton("下一步")
        self.next_btn.setFixedHeight(40)
        self.next_btn.setFixedWidth(120)
        self.next_btn.setCursor(Qt.CursorShape.PointingHand)
        self.next_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {COLORS["primary"]},
                    stop:1 {COLORS["primary_end"]});
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {COLORS["primary_light"]},
                    stop:1 {COLORS["primary_end"]});
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4F46E5,
                    stop:1 #7C3AED);
            }}
        """)
        self.next_btn.clicked.connect(self._next_step)
        button_layout.addWidget(self.next_btn)

        layout.addLayout(button_layout)

    def _show_step(self, step_index: int):
        """显示指定步骤"""
        for i, step in enumerate(self.steps):
            step.setVisible(i == step_index)

        # 更新按钮状态
        self.prev_btn.setVisible(step_index > 0 and step_index < len(self.steps) - 1)

        if step_index == len(self.steps) - 1:
            self.next_btn.setText("开始使用")
            self.skip_btn.setVisible(False)
        else:
            self.next_btn.setText("下一步")
            self.skip_btn.setVisible(True)

    def _next_step(self):
        """下一步"""
        if self._current_step < len(self.steps) - 1:
            self._current_step += 1
            self._show_step(self._current_step)
        else:
            # 完成
            self._collect_and_finish()

    def _prev_step(self):
        """上一步"""
        if self._current_step > 0:
            self._current_step -= 1
            self._show_step(self._current_step)

    def _on_skip(self):
        """跳过引导"""
        self.skipped.emit()

    def _collect_and_finish(self):
        """收集数据并完成"""
        # 收集所有步骤的数据
        all_data = {}
        for step in self.steps:
            if hasattr(step, 'get_values'):
                all_data.update(step.get_values())

        self.finished.emit(all_data)
