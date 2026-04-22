"""
视频上传窗口（Step 1）
支持拖拽上传 + 文件列表管理
"""
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QListWidget, QListWidgetItem, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent

from app.ui.windows.base_step_window import BaseStepWindow


class UploadWindow(BaseStepWindow):
    """
    Step 1: 视频上传窗口
    功能：
    - 拖拽上传区域（支持多文件）
    - 已选文件列表（显示名称、时长、大小）
    - 移除单个文件 / 清空全部
    - 进入下一步前验证至少有一个文件
    """

    files_selected = Signal(list)  # 通知主窗口已选择的文件

    def __init__(self, parent=None):
        super().__init__("视频上传", 0, parent)
        self._selected_files = []
        self._setup_content()

    def _setup_content(self):
        """构建上传窗口内容"""
        content_layout = QVBoxLayout()
        content_layout.setSpacing(24)

        # 拖拽上传区
        self.drop_zone = DropZone()
        self.drop_zone.file_dropped.connect(self._on_files_dropped)
        content_layout.addWidget(self.drop_zone, stretch=1)

        # 文件列表区
        list_label = QLabel("已选文件")
        list_label.setObjectName("section_title")
        content_layout.addWidget(list_label)

        self.file_list = QListWidget()
        self.file_list.setObjectName("file_list")
        self.file_list.setAlternatingRowColors(False)
        content_layout.addWidget(self.file_list, stretch=2)

        # 底部操作栏
        actions = QHBoxLayout()
        btn_clear = QPushButton("清空列表")
        btn_clear.setObjectName("secondary")
        btn_clear.clicked.connect(self._clear_files)

        btn_browse = QPushButton("从文件夹选择")
        btn_browse.setObjectName("secondary")
        btn_browse.clicked.connect(self._browse_files)

        actions.addWidget(btn_clear)
        actions.addWidget(btn_browse)
        actions.addStretch()

        content_layout.addLayout(actions)

        # 将内容加入主布局
        self._content_wrapper = QFrame()
        self._content_wrapper.setLayout(content_layout)
        self._main_layout.insertWidget(1, self._content_wrapper)  # 在导航栏下方

    def _on_files_dropped(self, paths: list):
        """处理拖拽来的文件"""
        for path in paths:
            if path not in self._selected_files:
                self._selected_files.append(path)
                self._add_file_item(path)
        self._update_navigation()

    def _add_file_item(self, path: str):
        """向列表添加文件项"""
        item = QListWidgetItem(path.split("/")[-1])
        item.setData(Qt.UserRole, path)
        self.file_list.addItem(item)

    def _clear_files(self):
        self._selected_files.clear()
        self.file_list.clear()
        self._update_navigation()

    def _browse_files(self):
        """打开文件选择对话框"""
        from PySide6.QtWidgets import QFileDialog
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择视频文件",
            "",
            "视频文件 (*.mp4 *.mov *.avi *.mkv *.webm);;所有文件 (*)"
        )
        if paths:
            self._on_files_dropped(paths)

    def _update_navigation(self):
        """根据文件数量更新导航按钮状态"""
        has_files = len(self._selected_files) > 0
        self.btn_next.setEnabled(has_files)
        if has_files:
            self.btn_next.setText(f"下一步 ({len(self._selected_files)} 个文件) →")
        else:
            self.btn_next.setText("下一步 →")

    def can_proceed(self) -> bool:
        return len(self._selected_files) > 0

    def get_data(self) -> dict:
        return {"files": self._selected_files.copy()}


class DropZone(QFrame):
    """
    拖拽上传区域
    支持视频文件拖拽，显示视觉提示
    """

    file_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.setAcceptDrops(True)
        self.setObjectName("drop_zone")

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        self.icon = QLabel("📁")
        self.icon.setAlignment(Qt.AlignCenter)
        self.icon.setObjectName("drop_icon")
        self.icon.setStyleSheet("font-size: 48px;")

        self.title = QLabel("拖拽视频文件到这里")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setObjectName("drop_title")

        self.subtitle = QLabel("支持 MP4 / MOV / AVI / MKV / WebM")
        self.subtitle.setAlignment(Qt.AlignCenter)
        self.subtitle.setObjectName("drop_subtitle")

        self.btn = QPushButton("或点击选择文件")
        self.btn.setObjectName("primary")
        self.btn.clicked.connect(self._on_click)

        layout.addWidget(self.icon)
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addWidget(self.btn)
        layout.addSpacing(8)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setProperty("dragging", True)
            self.style().unpolish(self)
            self.style().polish(self)

    def dragLeaveEvent(self, event):
        self.setProperty("dragging", False)
        self.style().unpolish(self)
        self.style().polish(self)

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
        if paths:
            self.file_dropped.emit(paths)
        event.acceptProposedAction()

    def _on_click(self):
        from PySide6.QtWidgets import QFileDialog
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择视频文件",
            "",
            "视频文件 (*.mp4 *.mov *.avi *.mkv *.webm);;所有文件 (*)"
        )
        if paths:
            self.file_dropped.emit(paths)
