#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step 1: 上传配置 — OKLCH Design Tokens

Task 2.1 UX 改善:
- 文件夹选择：QFileDialog.getExistingDirectory 扫描 mp4/mov/avi/webm
- Ctrl 多选文件：QFileDialog.getOpenFileNames 支持多选
- 视频预览缩略图：QVideoWidget / QLabel 显示选定视频
- 上传进度条：QProgressBar 显示分析进度

组件拆分:
- ThumbnailWorker -> thumbnail_worker.py
- VideoThumbnailItem -> video_thumbnail_item.py
- VideoPreviewWidget -> video_preview_widget.py
- VideoDropZone -> video_drop_zone.py
- VideoMetadataPanel -> video_metadata_panel.py
"""

import os
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QFrame, QProgressBar,
    QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from ...components import MacCard
from .thumbnail_worker import ThumbnailWorker
from .video_thumbnail_item import VideoThumbnailItem
from .video_preview_widget import VideoPreviewWidget
from .video_drop_zone import VideoDropZone
from .video_metadata_panel import VideoMetadataPanel


# ── OKLCH Design Tokens ──────────────────────────────────────
_T = {
    "bg_card":    "oklch(0.16 0.01 250)",
    "bg_input":   "oklch(0.13 0.01 250)",
    "border":     "oklch(0.24 0.01 250)",
    "border_h":   "oklch(0.30 0.02 250)",
    "text":       "oklch(0.93 0.01 250)",
    "text_sub":   "oklch(0.75 0.01 250)",
    "text_muted": "oklch(0.55 0.01 250)",
    "primary":    "oklch(0.65 0.20 250)",
    "primary_l":  "oklch(0.70 0.24 250)",
}


# ── StepUpload 主组件 ────────────────────────────────────────
class StepUpload(QWidget):
    """Step 1 — 上传交互优化版本"""
    config_ready = Signal(str, str, object, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._video_paths = []      # 当前选中的视频路径列表
        self._thumbnail_worker = None
        self._current_preview_path = ""
        self._progress_value = 0
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        # 标题行
        title_row = QHBoxLayout()
        title = QLabel("创作新解说")
        title.setFont(QFont("", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {_T['text']};")
        title_row.addWidget(title)
        title_row.addStretch()

        # 文件计数标签
        self._count_label = QLabel("未选择文件")
        self._count_label.setStyleSheet(f"color: {_T['text_muted']}; font-size: 12px;")
        self._count_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        title_row.addWidget(self._count_label)
        layout.addLayout(title_row)

        hint = QLabel("上传视频后，AI 将代入主角视角生成解说词")
        hint.setStyleSheet(f"color: {_T['text_muted']}; font-size: 12px;")
        layout.addWidget(hint)

        # ── 拖放区 ──
        self._drop_zone = VideoDropZone()
        self._drop_zone.files_selected.connect(self._on_files_selected)
        layout.addWidget(self._drop_zone)

        # ── 预览 + 列表 横排布局 ──
        preview_layout = QHBoxLayout()

        # 左侧：视频预览
        self._preview = VideoPreviewWidget()
        preview_layout.addWidget(self._preview, stretch=0)

        # 右侧：视频列表（缩略图网格）
        list_card = MacCard()
        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(12, 12, 12, 12)
        list_layout.setSpacing(8)

        list_title = QLabel("已选视频")
        list_title.setFont(QFont("", 12, QFont.Weight.SemiBold))
        list_title.setStyleSheet(f"color: {_T['text_sub']};")
        list_layout.addWidget(list_title)

        # 缩略图网格（滚动区域）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: {_T['bg_input']};
                border-radius: 4px;
                width: 6px;
                margin: 2px 0;
            }}
            QScrollBar::handle:vertical {{
                background: {_T['border_h']};
                border-radius: 3px;
            }}
        """)
        self._thumb_container = QWidget()
        self._thumb_layout = QGridLayout(self._thumb_container)
        self._thumb_layout.setSpacing(8)
        self._thumb_items = {}  # path -> VideoThumbnailItem
        scroll.setWidget(self._thumb_container)
        list_layout.addWidget(scroll)
        preview_layout.addWidget(list_card, stretch=1)

        layout.addLayout(preview_layout)

        # ── 元数据面板 ──
        self._meta_panel = VideoMetadataPanel()
        self._meta_panel.setVisible(False)
        layout.addWidget(self._meta_panel)

        # ── 进度条（分析进度）────────────────────────────
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setVisible(False)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {_T['bg_input']};
                border: 1px solid {_T['border']};
                border-radius: 6px;
                height: 8px;
                text-align: center;
                color: transparent;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {_T['primary']}, stop:1 {_T['primary_l']});
                border-radius: 6px;
            }}
        """)
        layout.addWidget(self._progress_bar)

        # ── 配置卡片 ──
        config_card = MacCard()
        gl = QGridLayout(config_card)
        gl.setContentsMargins(20, 20, 20, 20)
        gl.setSpacing(16)

        ctx_lbl = QLabel("解说场景")
        ctx_lbl.setStyleSheet(f"color: {_T['text_sub']}; font-size: 13px;")
        gl.addWidget(ctx_lbl, 0, 0)
        self._ctx_input = QLineEdit()
        self._ctx_input.setPlaceholderText("例如：在咖啡馆独自工作，感受午后阳光...")
        self._ctx_input.setMinimumHeight(40)
        self._ctx_input.setStyleSheet(f"""
            QLineEdit {{
                background: {_T['bg_input']};
                color: {_T['text']};
                border: 1px solid {_T['border']};
                border-radius: 10px;
                padding: 0 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{ border-color: {_T['primary']}; }}
            QLineEdit::placeholder {{ color: {_T['text_muted']}; }}
        """)
        gl.addWidget(self._ctx_input, 0, 1, 1, 2)

        emotion_lbl = QLabel("情感风格")
        emotion_lbl.setStyleSheet(f"color: {_T['text_sub']}; font-size: 13px;")
        gl.addWidget(emotion_lbl, 1, 0)
        self._emotion_combo = QComboBox()
        self._emotion_combo.addItems(["治愈", "悬疑", "励志", "怀旧", "浪漫"])
        self._apply_combo_style(self._emotion_combo)
        gl.addWidget(self._emotion_combo, 1, 1, 1, 2)

        style_lbl = QLabel("解说长度")
        style_lbl.setStyleSheet(f"color: {_T['text_sub']}; font-size: 13px;")
        gl.addWidget(style_lbl, 2, 0)
        self._style_combo_widget = QComboBox()
        self._style_combo_widget.addItems(["简洁版", "标准版", "详细版"])
        self._apply_combo_style(self._style_combo_widget)
        gl.addWidget(self._style_combo_widget, 2, 1, 1, 2)

        layout.addWidget(config_card)

        # ── 底部按钮 ──
        btn_layout = QHBoxLayout()
        self._clear_btn = QPushButton("清空")
        self._clear_btn.setObjectName("secondary_btn")
        self._clear_btn.setFixedSize(80, 40)
        self._clear_btn.clicked.connect(self._clear_all)
        btn_layout.addWidget(self._clear_btn)
        btn_layout.addStretch()

        self._next_btn = QPushButton("开始创作 →")
        self._next_btn.setObjectName("primary_btn")
        self._next_btn.setFixedSize(140, 44)
        self._next_btn.clicked.connect(self._on_next)
        self._next_btn.setEnabled(False)
        btn_layout.addWidget(self._next_btn)
        layout.addLayout(btn_layout)

        layout.addStretch()

    def _apply_combo_style(self, combo: QComboBox):
        combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {_T['bg_card']};
                color: {_T['text']};
                border: 1px solid {_T['border']};
                border-radius: 10px;
                padding: 10px 16px;
                font-size: 13px;
            }}
            QComboBox:hover {{ border-color: {_T['border_h']}; }}
            QComboBox:focus {{ border-color: {_T['primary']}; }}
            QComboBox QAbstractItemView {{
                background-color: {_T['bg_card']};
                border: 1px solid {_T['border']};
                border-radius: 10px;
                color: {_T['text']};
                selection-background-color: {_T['bg_active']};
                padding: 4px;
            }}
        """)

    def _on_files_selected(self, paths: list):
        """收到文件列表后处理"""
        from .thumbnail_worker import VIDEO_EXTS

        # 过滤有效视频
        valid = [p for p in paths if Path(p).suffix.lower() in VIDEO_EXTS and os.path.isfile(p)]
        if not valid:
            return

        # 追加（去重）
        existing = set(self._video_paths)
        new_paths = [p for p in valid if p not in existing]
        self._video_paths.extend(new_paths)

        # 启动缩略图生成
        self._start_thumbnail_worker(new_paths)

        # 更新计数
        self._update_count_label()
        self._next_btn.setEnabled(len(self._video_paths) > 0)

    def _start_thumbnail_worker(self, paths: list):
        """启动缩略图后台生成"""
        if self._thumbnail_worker and self._thumbnail_worker.isRunning():
            return

        self._progress_bar.setVisible(True)
        self._progress_value = 0
        self._progress_bar.setValue(0)

        self._thumbnail_worker = ThumbnailWorker(paths, self)
        self._thumbnail_worker.thumbnail_ready.connect(self._on_thumbnail_ready)
        self._thumbnail_worker.finished.connect(self._on_thumbnails_done)
        self._thumbnail_worker.start()

    def _on_thumbnail_ready(self, path: str, thumb_path: str):
        """缩略图生成完成"""
        if path in self._thumb_items:
            self._thumb_items[path].set_thumbnail(thumb_path)

    def _on_thumbnails_done(self):
        """所有缩略图生成完成"""
        self._progress_bar.setVisible(False)

    def _add_thumbnail_item(self, path: str):
        """向缩略图网格添加一个条目"""
        item = VideoThumbnailItem(path)
        item.clicked.connect(self._on_thumb_clicked)
        item.selection_changed.connect(self._on_selection_changed)

        # 计算网格位置（每行3个）
        count = len(self._thumb_items)
        row = count // 3
        col = count % 3
        self._thumb_layout.addWidget(item, row, col)
        self._thumb_items[path] = item

        # 立即生成缩略图
        self._generate_single_thumbnail(path, item)

    def _generate_single_thumbnail(self, path: str, item: VideoThumbnailItem):
        """立即生成单个缩略图（同步）"""
        import threading
        def worker():
            thumb = ThumbnailWorker._generate_one(None, path)  # type: ignore
            if thumb:
                from PySide6.QtCore import QMetaObject, Qt, Q_ARG
                def update():
                    item.set_thumbnail(thumb)
                QMetaObject.invokeMethod(item, "set_thumbnail",
                                        Qt.QueuedConnection, Q_ARG(str, thumb))
        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def _on_thumb_clicked(self, path: str):
        """点击缩略图预览"""
        self._current_preview_path = path
        self._preview.load(path)
        self._meta_panel.set_metadata(path)
        self._meta_panel.setVisible(True)

    def _on_selection_changed(self, path: str, selected: bool):
        """选中状态变化"""
        self._update_count_label()

    def _update_count_label(self):
        """更新文件计数标签"""
        checked = VideoThumbnailItem.get_checked_files()
        total = len(self._video_paths)
        if total == 0:
            self._count_label.setText("未选择文件")
        elif len(checked) == 0:
            self._count_label.setText(f"已选 {total} 个视频（无选中）")
        else:
            self._count_label.setText(f"已选 {total} 个视频，{len(checked)} 个已勾选")

    def _clear_all(self):
        """清空所有选择"""
        self._video_paths.clear()
        VideoThumbnailItem.clear_checked()

        # 清理缩略图网格
        for item in self._thumb_items.values():
            item.setParent(None)
            item.deleteLater()
        self._thumb_items.clear()

        self._preview.stop()
        self._meta_panel.setVisible(False)
        self._progress_bar.setVisible(False)
        self._update_count_label()
        self._next_btn.setEnabled(False)

    def _on_next(self):
        checked = VideoThumbnailItem.get_checked_files()
        paths_to_use = list(checked) if checked else self._video_paths
        if not paths_to_use:
            return

        emotion_map = {"治愈": "healing", "悬疑": "suspense", "励志": "inspiring",
                       "怀旧": "nostalgic", "浪漫": "romantic"}
        style_map = {"简洁版": "concise", "标准版": "standard", "详细版": "detailed"}

        # 传递第一个视频路径（主视频）
        main_path = paths_to_use[0]
        self.config_ready.emit(
            main_path,
            self._ctx_input.text().strip(),
            emotion_map.get(self._emotion_combo.currentText(), "healing"),
            style_map.get(self._style_combo_widget.currentText(), "standard"),
            ",".join(paths_to_use)  # 传递所有选中路径
        )
