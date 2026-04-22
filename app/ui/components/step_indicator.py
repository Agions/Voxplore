"""
步骤指示器组件
4步流程：上传 → 场景理解 → 配音编辑 → 导出
"""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, Signal


class StepIndicator(QWidget):
    step_changed = Signal(int)  # 当前步骤索引

    STEPS = ["上传", "场景理解", "配音编辑", "导出"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_step = 0
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        for i, name in enumerate(self.STEPS):
            # 步骤圆圈
            circle = QLabel(str(i + 1))
            circle.setFixedSize(28, 28)
            circle.setAlignment(Qt.AlignCenter)
            circle.setObjectName(f"step_circle_{i}")

            # 步骤名称
            label = QLabel(name)
            label.setObjectName(f"step_label_{i}")

            # 连接线（除最后一个）
            if i < len(self.STEPS) - 1:
                line = QLabel()
                line.setFixedHeight(1)
                line.setObjectName("step_line")

            layout.addWidget(circle)
            layout.addWidget(label)
            if i < len(self.STEPS) - 1:
                layout.addWidget(line)

    def set_step(self, step: int):
        """设置当前步骤 (0-3)"""
        self._current_step = step
        self._update_styles()
        self.step_changed.emit(step)

    def _update_styles(self):
        """更新样式：已完成/当前/未完成"""
        # 使用 tokens 颜色
        # 已完成: primary + ✓ 图标
        # 当前: primary 高亮
        # 未完成: muted 灰色
        pass  # 简化版，后续接入 theme_manager
