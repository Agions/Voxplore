"""
CFToastNotification 使用示例

运行方式：
    python test_toast.py
"""

import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PySide6.QtCore import Qt
from app.ui.components.design_system import CFToastNotification


class DemoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CFToastNotification Demo")
        self.setFixedSize(600, 400)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(40, 40, 40, 40)

        # 动态导入避免循环依赖
        from app.ui.components.design_system import CFButton

        # 成功提示
        btn_success = CFButton("显示成功提示", variant="primary")
        btn_success.clicked.connect(lambda: self._show_toast("保存成功！", "success"))
        layout.addWidget(btn_success)

        # 警告提示
        btn_warning = CFButton("显示警告提示", variant="secondary")
        btn_warning.clicked.connect(lambda: self._show_toast("确定要删除这个文件吗？", "warning"))
        layout.addWidget(btn_warning)

        # 错误提示
        btn_error = CFButton("显示错误提示", variant="danger")
        btn_error.clicked.connect(lambda: self._show_toast("网络连接失败", "error"))
        layout.addWidget(btn_error)

        # 信息提示
        btn_info = CFButton("显示信息提示", variant="ghost")
        btn_info.clicked.connect(lambda: self._show_toast("新版本已可用", "info"))
        layout.addWidget(btn_info)

        # 带操作按钮的提示
        btn_action = CFButton("显示带操作的提示", variant="primary")
        btn_action.clicked.connect(self._show_action_toast)
        layout.addWidget(btn_action)

    def _show_toast(self, message: str, type: str):
        toast = CFToastNotification(message, type=type)
        # 显示在窗口中央
        geo = self.geometry()
        toast.move(
            geo.x() + geo.width() // 2 - toast.width() // 2,
            geo.y() + geo.height() // 2 - toast.height() // 2,
        )
        toast.show()

    def _show_action_toast(self):
        toast = CFToastNotification("确定要永久删除吗？", type="warning", duration=0)  # 不自动消失
        toast.add_action("取消", lambda: print("取消"))
        toast.add_action("删除", lambda: print("删除"))
        geo = self.geometry()
        toast.move(
            geo.x() + geo.width() // 2 - toast.width() // 2,
            geo.y() + geo.height() // 2 - toast.height() // 2,
        )
        toast.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DemoWindow()
    win.show()
    sys.exit(app.exec())
