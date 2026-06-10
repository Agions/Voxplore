"""
首次使用引导 - 分步引导向导
引导用户完成初始设置
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from scenefab.ui.theme.ds_tokens import _C

# ── 通用 QSS 模板 — 消除 5 处 ComboBox / QLineEdit / CheckBox 重复 ──────

_COMBO_QSS = (
    "QComboBox {{ background-color: {_c.BG_SURFACE}; color: {_c.TEXT_PRIMARY};"
    "  border: 1px solid {_c.BORDER_DEFAULT}; border-radius: 10px;"
    "  padding: 0 16px; font-size: 14px; }}"
    "QComboBox:hover {{ border-color: {_c.PRIMARY}; }}"
    "QComboBox::drop-down {{ border: none; width: 32px; }}"
    "QComboBox QAbstractItemView {{ background-color: {_c.BG_SURFACE};"
    "  color: {_c.TEXT_PRIMARY}; border: 1px solid {_c.BORDER_DEFAULT};"
    "  border-radius: 8px; padding: 4px; }}"
)

_INPUT_QSS = (
    "QLineEdit {{ background-color: {_c.BG_SURFACE}; color: {_c.TEXT_PRIMARY};"
    "  border: 1px solid {_c.BORDER_DEFAULT}; border-radius: 10px;"
    "  padding: 0 16px; font-size: 14px; }}"
    "QLineEdit:hover {{ border-color: {_c.PRIMARY}; }}"
    "QLineEdit:focus {{ border-color: {_c.PRIMARY}; background-color: {_c.BG_ELEVATED}; }}"
)

_CHECKBOX_QSS = (
    "QCheckBox {{ color: {_c.TEXT_SECONDARY}; font-size: 13px; spacing: 10px; }}"
    "QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 4px;"
    "  border: 2px solid {_c.BORDER_DEFAULT}; background-color: transparent; }}"
    "QCheckBox::indicator:checked {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
    "  stop:0 {_c.PRIMARY}, stop:1 {_c.PRIMARY_DARK}); border-color: {_c.PRIMARY}; }}"
)


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
            step_dot = QLabel(str(i + 1))
            step_dot.setFixedSize(32, 32)
            step_dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
            step_dot.setStyleSheet(
                f"QLabel {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                f"  stop:0 {_C.PRIMARY}, stop:1 {_C.PRIMARY_DARK});"
                f"  color: white; border-radius: 16px; font-weight: 600; font-size: 13px; }}"
            )
            layout.addWidget(step_dot)

            if i < len(self._steps) - 1:
                step_label = QLabel(step)
                step_label.setStyleSheet(f"color: {_C.TEXT_MUTED}; font-size: 12px;")
                layout.addWidget(step_label)

                separator = QFrame()
                separator.setFixedSize(40, 2)
                separator.setStyleSheet(f"background: {_C.BORDER_DEFAULT}; border-radius: 1px;")
                layout.addWidget(separator)

        layout.addStretch()

    def set_current_step(self, step: int):
        """设置当前步骤"""
        self._current_step = step


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

        icon_label = QLabel("👋")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("font-size: 64px; background: transparent;")
        layout.addWidget(icon_label)

        title = QLabel("欢迎使用 SceneFab")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {_C.TEXT_PRIMARY}; background: transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        desc = QLabel("让我们用几分钟时间来配置您的创作环境")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {_C.TEXT_MUTED}; font-size: 14px; background: transparent;")
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
        title.setStyleSheet(f"color: {_C.TEXT_PRIMARY}; background: transparent;")
        layout.addWidget(title)

        desc = QLabel("选择您要使用的 AI 服务提供商")
        desc.setStyleSheet(f"color: {_C.TEXT_MUTED}; font-size: 13px; background: transparent;")
        layout.addWidget(desc)

        # 提供商选择
        provider_label = QLabel("AI 服务提供商")
        provider_label.setStyleSheet(
            f"color: {_C.TEXT_SECONDARY}; font-size: 13px; font-weight: 600; background: transparent;"
        )
        layout.addWidget(provider_label)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["DeepSeek", "Kimi", "Qwen", "Claude", "Gemini", "本地模型"])
        self.provider_combo.setFixedHeight(44)
        self.provider_combo.setStyleSheet(_COMBO_QSS.format(_c=_C))
        layout.addWidget(self.provider_combo)

        # API Key 输入
        api_label = QLabel("API Key（可选）")
        api_label.setStyleSheet(
            f"color: {_C.TEXT_SECONDARY}; font-size: 13px; font-weight: 600; background: transparent;"
        )
        layout.addWidget(api_label)

        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("输入您的 API Key（可选）")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setFixedHeight(44)
        self.api_key_input.setStyleSheet(_INPUT_QSS.format(_c=_C))
        layout.addWidget(self.api_key_input)

        hint = QLabel("💡 您可以在设置中随时修改 AI 配置")
        hint.setStyleSheet(f"color: {_C.TEXT_MUTED}; font-size: 12px; background: transparent;")
        layout.addWidget(hint)
        layout.addStretch()

    def get_values(self) -> dict:
        """获取配置数据"""
        return {
            "provider": self.provider_combo.currentText(),
            "api_key": self.api_key_input.text(),
        }


class PreferencesStep(StepContent):
    """偏好设置步骤"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(24)

        title = QLabel("个性化设置")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {_C.TEXT_PRIMARY}; background: transparent;")
        layout.addWidget(title)

        desc = QLabel("根据您的使用习惯进行定制")
        desc.setStyleSheet(f"color: {_C.TEXT_MUTED}; font-size: 13px; background: transparent;")
        layout.addWidget(desc)

        # 主题选择
        theme_label = QLabel("界面主题")
        theme_label.setStyleSheet(
            f"color: {_C.TEXT_SECONDARY}; font-size: 13px; font-weight: 600; background: transparent;"
        )
        layout.addWidget(theme_label)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["深色主题", "浅色主题", "蓝调深色", "森林绿色", "紫色主题", "橙色主题"])
        self.theme_combo.setCurrentText("深色主题")
        self.theme_combo.setFixedHeight(44)
        self.theme_combo.setStyleSheet(_COMBO_QSS.format(_c=_C))
        layout.addWidget(self.theme_combo)

        # 输出目录
        output_label = QLabel("默认输出目录")
        output_label.setStyleSheet(
            f"color: {_C.TEXT_SECONDARY}; font-size: 13px; font-weight: 600; background: transparent;"
        )
        layout.addWidget(output_label)

        self.output_input = QLineEdit()
        self.output_input.setPlaceholderText("留空使用默认目录")
        self.output_input.setFixedHeight(44)
        self.output_input.setStyleSheet(_INPUT_QSS.format(_c=_C))
        layout.addWidget(self.output_input)

        # 选项
        options_layout = QVBoxLayout()
        options_layout.setSpacing(12)

        self.auto_save_check = QCheckBox("自动保存项目")
        self.auto_save_check.setChecked(True)
        self.auto_save_check.setStyleSheet(_CHECKBOX_QSS.format(_c=_C))
        options_layout.addWidget(self.auto_save_check)

        self.telemetry_check = QCheckBox("发送匿名使用统计帮助改进产品")
        self.telemetry_check.setChecked(False)
        self.telemetry_check.setStyleSheet(_CHECKBOX_QSS.format(_c=_C))
        options_layout.addWidget(self.telemetry_check)

        layout.addLayout(options_layout)
        layout.addStretch()

    def get_values(self) -> dict:
        """获取设置数据"""
        return {
            "theme": self.theme_combo.currentText(),
            "output_dir": self.output_input.text(),
            "auto_save": self.auto_save_check.isChecked(),
            "telemetry": self.telemetry_check.isChecked(),
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

        icon_label = QLabel("🎉")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("font-size: 64px; background: transparent;")
        layout.addWidget(icon_label)

        title = QLabel("设置完成！")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setWeight(QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {_C.TEXT_PRIMARY}; background: transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        desc = QLabel("一切准备就绪，开始您的创作之旅吧！")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {_C.TEXT_MUTED}; font-size: 14px; background: transparent;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

        # 快捷操作提示
        tips_widget = QWidget()
        tips_widget.setStyleSheet(
            f"QWidget {{ background-color: {_C.BG_ELEVATED};"
            f"  border: 1px solid {_C.BORDER_DEFAULT}; border-radius: 12px; padding: 16px; }}"
        )
        tips_layout = QVBoxLayout(tips_widget)
        tips_layout.setSpacing(12)

        tips_title = QLabel("💡 快捷提示")
        tips_title.setStyleSheet(
            f"color: {_C.TEXT_PRIMARY}; font-weight: 600; font-size: 13px; background: transparent;"
        )
        tips_layout.addWidget(tips_title)

        for tip in ["拖放视频文件到窗口开始处理", "使用快捷键 Ctrl+N 创建新项目", "在设置中切换主题和配置 AI"]:
            tip_label = QLabel(tip)
            tip_label.setWordWrap(True)
            tip_label.setStyleSheet(f"color: {_C.TEXT_MUTED}; font-size: 12px; background: transparent;")
            tips_layout.addWidget(tip_label)

        layout.addWidget(tips_widget)
        layout.addStretch()
