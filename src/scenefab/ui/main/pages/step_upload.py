#!/usr/bin/env python3
"""
上传步骤页面
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QFont
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...main.pages.step_base import ContentCard, StepPage
from ...theme.ds_tokens import Colors, FontSizes, Radii


class VideoDropZone(QFrame):
    """视频拖放区"""

    files_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFixedHeight(240)
        self.setObjectName("drop_zone")
        self._setup_style()
        self._setup_ui()

    def _setup_style(self):
        self.setStyleSheet(f"""
            #drop_zone {{
                background: {Colors.BG_SURFACE};
                border: 2px dashed {Colors.BORDER_DEFAULT};
                border-radius: {Radii.lg};
            }}
            #drop_zone:hover, #drop_zone.drag_over {{
                border-color: {Colors.PRIMARY_500};
                background: rgba(139, 92, 246, 0.05);
            }}
        """)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("📤")
        icon.setFont(QFont("", 48))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

        title = QLabel("拖放视频文件到这里")
        title.setFont(QFont("", FontSizes.lg, QFont.Weight.Medium))
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("或点击选择文件（支持 MP4, MOV, AVI, MKV）")
        subtitle.setFont(QFont("", FontSizes.sm))
        subtitle.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        browse_btn = QPushButton("浏览文件")
        browse_btn.setObjectName("browse_btn")
        browse_btn.setFixedSize(120, 36)
        browse_btn.clicked.connect(self._browse)
        layout.addSpacing(8)
        layout.addWidget(browse_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)

    def _browse(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择视频文件",
            "",
            "视频文件 (*.mp4 *.mov *.avi *.mkv *.flv *.wmv);;所有文件 (*)",
        )
        if files:
            self.files_dropped.emit(files)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setProperty("drag_over", True)
            self.style().unpolish(self)
            self.style().polish(self)

    def dragLeaveEvent(self, event):
        self.setProperty("drag_over", False)
        self.style().unpolish(self)
        self.style().polish(self)

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        files = [u.toLocalFile() for u in urls if u.isLocalFile()]
        if files:
            self.files_dropped.emit(files)


class FileListItem(QFrame):
    """文件列表项"""

    removed = Signal()

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self._file_path = file_path
        import os

        self._name = os.path.basename(file_path)
        self.setFixedHeight(56)
        self.setObjectName("file_item")
        self._setup_style()
        self._setup_ui()

    def _setup_style(self):
        self.setStyleSheet(f"""
            #file_item {{
                background: {Colors.BG_SURFACE};
                border: 1px solid {Colors.BORDER_SUBTLE};
                border-radius: {Radii.base};
            }}
            #file_item:hover {{
                background: {Colors.BG_ELEVATED};
            }}
        """)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        icon = QLabel("🎬")
        icon.setFont(QFont("", 20))
        layout.addWidget(icon)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(1)

        name = QLabel(self._name)
        name.setFont(QFont("", FontSizes.sm, QFont.Weight.Medium))
        name.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        name.setElideMode(Qt.TextElideMode.ElideMiddle)
        info_layout.addWidget(name)

        path = QLabel(self._file_path)
        path.setFont(QFont("", FontSizes.xs))
        path.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        path.setElideMode(Qt.TextElideMode.ElideMiddle)
        info_layout.addWidget(path)

        layout.addLayout(info_layout, 1)
        layout.addStretch()

        remove_btn = QPushButton("×")
        remove_btn.setObjectName("remove_btn")
        remove_btn.setFixedSize(24, 24)
        remove_btn.setStyleSheet(f"""
            QPushButton#remove_btn {{
                background: transparent;
                color: {Colors.TEXT_MUTED};
                border: none;
                font-size: 18px;
            }}
            QPushButton#remove_btn:hover {{
                color: {Colors.ERROR};
            }}
        """)
        remove_btn.clicked.connect(self.removed.emit)
        layout.addWidget(remove_btn)


class StepUploadPage(StepPage):
    """上传步骤页 (step 0)"""

    files_selected = Signal(list)

    def __init__(self, parent=None):
        super().__init__(0, parent)
        self._files = []

    def _build_content(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(24)

        # 说明卡片
        info_card = ContentCard("支持格式")
        info_layout = info_card.layout()
        formats = QLabel(
            "MP4 • MOV • AVI • MKV • FLV • WMV\n推荐分辨率: 1080P 以上 | 单文件建议 < 2GB"
        )
        formats.setFont(QFont("", FontSizes.sm))
        formats.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        formats.setWordWrap(True)
        info_layout.addWidget(formats)
        layout.addWidget(info_card)

        # 拖放区
        self.drop_zone = VideoDropZone()
        self.drop_zone.files_dropped.connect(self._on_files_dropped)
        layout.addWidget(self.drop_zone)

        # 文件列表
        self.file_list = QFrame()
        self.file_list.setObjectName("file_list")
        self.file_list.setStyleSheet("#file_list { border: none; }")
        file_list_layout = QVBoxLayout(self.file_list)
        file_list_layout.setContentsMargins(0, 0, 0, 0)
        file_list_layout.setSpacing(8)
        file_list_layout.addWidget(QLabel("已选择 0 个文件"))
        layout.addWidget(self.file_list)

        return container

    def _on_files_dropped(self, files: list):
        self._files.extend(files)
        self._refresh_file_list()

    def _refresh_file_list(self):
        layout = self.file_list.layout()
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        count_label = QLabel(f"已选择 {len(self._files)} 个文件")
        count_label.setFont(QFont("", FontSizes.sm, QFont.Weight.Medium))
        count_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        layout.addWidget(count_label)

        for f in self._files:
            item = FileListItem(f)
            item.removed.connect(lambda p=f: self._remove_file(p))
            layout.addWidget(item)

        layout.addStretch()
