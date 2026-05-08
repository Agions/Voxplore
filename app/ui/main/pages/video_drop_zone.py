#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拖放区组件

从 step_upload.py 提取 VideoDropZone
"""

import os
from pathlib import Path

from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog
from PySide6.QtCore import Signal
from PySide6.QtGui import QFont, QDragEnterEvent, QDropEvent


# ── OKLCH Design Tokens ──────────────────────────────────────
_T = {
    "bg_input":    "oklch(0.13 0.01 250)",
    "bg_hover":    "oklch(0.14 0.01 250)",
    "bg_active":   "oklch(0.17 0.01 250)",
    "border":      "oklch(0.24 0.01 250)",
    "primary":     "oklch(0.65 0.20 250)",
    "text_muted":  "oklch(0.55 0.01 250)",
}

# 视频扩展名
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


# ── 拖放区（支持文件夹 + 多文件）────────────────────────────
class VideoDropZone(QFrame):
    """支持文件夹选择和多文件 Ctrl 多选的视频拖放区"""
    files_selected = Signal(list)  # 发送文件列表

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.setAcceptDrops(True)
        self.setMinimumHeight(120)

    def _setup_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                border: 2px dashed {_T['border']};
                border-radius: 16px;
                background: {_T['bg_input']};
            }}
            QFrame:hover {{
                border-color: {_T['primary']};
                background: {_T['bg_hover']};
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)

        self._icon = QLabel("🎬")
        self._icon.setFont(QFont("", 36))
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._icon)

        self._text = QLabel("拖放视频或文件夹到此处")
        self._text.setFont(QFont("", 13))
        self._text.setStyleSheet(f"color: {_T['text_muted']};")
        self._text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._text)

        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._sel_file_btn = QPushButton("选择文件")
        self._sel_file_btn.setObjectName("secondary_btn")
        self._sel_file_btn.setFixedSize(100, 32)
        self._sel_file_btn.clicked.connect(self._select_files)
        btn_row.addWidget(self._sel_file_btn)

        self._sel_folder_btn = QPushButton("选择文件夹")
        self._sel_folder_btn.setObjectName("secondary_btn")
        self._sel_folder_btn.setFixedSize(100, 32)
        self._sel_folder_btn.clicked.connect(self._select_folder)
        btn_row.addWidget(self._sel_folder_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)
        self.setMinimumWidth(400)

    def _select_files(self):
        """Ctrl 多选文件"""
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择视频文件", "",
            "视频文件 (*.mp4 *.mov *.avi *.mkv *.webm);;所有文件 (*)"
        )
        if paths:
            self.files_selected.emit(paths)

    def _select_folder(self):
        """选择文件夹，扫描视频"""
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹", "")
        if folder:
            paths = self._scan_folder(folder)
            if paths:
                self.files_selected.emit(paths)

    def _scan_folder(self, folder: str) -> list:
        """递归扫描文件夹内所有视频"""
        paths = []
        for root, _, files in os.walk(folder):
            for f in files:
                if Path(f).suffix.lower() in VIDEO_EXTS:
                    paths.append(os.path.join(root, f))
        return paths

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(f"""
                QFrame {{
                    border: 2px solid {_T['primary']};
                    border-radius: 16px;
                    background: {_T['bg_active']};
                }}
            """)

    def dragLeaveEvent(self, event):
        self.setStyleSheet(f"""
            QFrame {{
                border: 2px dashed {_T['border']};
                border-radius: 16px;
                background: {_T['bg_input']};
            }}
        """)

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet(f"""
            QFrame {{
                border: 2px dashed {_T['border']};
                border-radius: 16px;
                background: {_T['bg_input']};
            }}
        """)
        paths = []
        for url in event.mimeData().urls():
            p = url.toLocalFile()
            if os.path.isdir(p):
                paths.extend(self._scan_folder(p))
            elif os.path.isfile(p) and Path(p).suffix.lower() in VIDEO_EXTS:
                paths.append(p)
        if paths:
            self.files_selected.emit(paths)
