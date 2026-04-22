"""
BaseStepWindow - 步骤窗口基类
所有步骤窗口（上传/场景/配音/导出）继承此基类
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PySide6.QtCore import Signal


class BaseStepWindow(QWidget):
    """
    步骤窗口基类，提供统一的导航信号和布局结构。
    子类通过覆写 _setup_content() 来填充具体内容。
    """
    next_requested = Signal()   # 请求进入下一步
    prev_requested = Signal()   # 请求返回上一步

    def __init__(self, title: str, step_index: int, parent=None):
        super().__init__(parent)
        self._title = title
        self._step_index = step_index
        self._shared_data = {}  # MainWindow 设置的共享数据（上一步结果）
        self._setup_ui()

    def _setup_ui(self):
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(32, 24, 32, 24)
        self._main_layout.setSpacing(16)

        # 标题区
        title_label = QLabel(self._title)
        title_label.setObjectName("step_window_title")
        self._main_layout.addWidget(title_label)

        # 导航按钮区
        nav_layout = QHBoxLayout()
        self.btn_prev = QPushButton("← 上一步")
        self.btn_prev.setObjectName("secondary")
        self.btn_prev.clicked.connect(self.prev_requested.emit)

        self.step_label = QLabel(f"步骤 {self._step_index + 1}/4")
        self.step_label.setObjectName("step_counter")
        self.step_label.setAlignment(Qt.AlignCenter)

        self.btn_next = QPushButton("下一步 →")
        self.btn_next.setObjectName("primary")
        self.btn_next.clicked.connect(self.next_requested.emit)
        self.btn_next.setEnabled(False)

        nav_layout.addWidget(self.btn_prev)
        nav_layout.addStretch()
        nav_layout.addWidget(self.step_label)
        nav_layout.addStretch()
        nav_layout.addWidget(self.btn_next)
        self._main_layout.addLayout(nav_layout)

        # 内容区（子类实现）
        self._setup_content()

    def _setup_content(self):
        """子类覆写以填充具体内容"""
        pass

    def can_proceed(self) -> bool:
        """子类覆写以控制下一步是否可用"""
        return True

    def get_data(self) -> dict:
        """子类覆写以返回步骤数据"""
        return {}

    def set_shared_data(self, data: dict):
        """由 MainWindow 调用，设置来自上一步骤的共享数据"""
        self._shared_data = data
        self._on_shared_data_set(data)

    def _on_shared_data_set(self, data: dict):
        """子类可选覆写：当共享数据被设置时触发（用于初始化 UI）"""
        pass

    def set_step_label(self, step: int):
        """更新步骤指示"""
        self.step_label.setText(f"步骤 {step + 1}/4")

    def enable_next(self, enabled: bool = True):
        self.btn_next.setEnabled(enabled)

    def enable_prev(self, enabled: bool = True):
        self.btn_prev.setEnabled(enabled)

    def set_next_text(self, text: str):
        self.btn_next.setText(text)

    def set_prev_text(self, text: str):
        self.btn_prev.setText(text)
