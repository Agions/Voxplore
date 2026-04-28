#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step 1: 上传配置 — OKLCH Design Tokens

Task 2.1 UX 改善:
- 文件夹选择：QFileDialog.getExistingDirectory 扫描 mp4/mov/avi/webm
- Ctrl 多选文件：QFileDialog.getOpenFileNames 支持多选
- 视频预览缩略图：QVideoWidget / QLabel 显示选定视频
- 上传进度条：QProgressBar 显示分析进度
"""

import os
import json
import subprocess
import logging
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QFrame, QFileDialog, QProgressBar,
    QScrollArea, QCheckBox
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont, QDragEnterEvent, QDropEvent, QPixmap
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget

from ...components import MacCard

# ── OKLCH Design Tokens ──────────────────────────────────────
_T = {
    "bg_card":    "oklch(0.16 0.01 250)",
    "bg_input":   "oklch(0.13 0.01 250)",
    "bg_hover":   "oklch(0.14 0.01 250)",
    "bg_active":  "oklch(0.17 0.01 250)",
    "border":     "oklch(0.24 0.01 250)",
    "border_h":   "oklch(0.30 0.02 250)",
    "text":       "oklch(0.93 0.01 250)",
    "text_sub":   "oklch(0.75 0.01 250)",
    "text_muted": "oklch(0.55 0.01 250)",
    "text_disabled":"oklch(0.40 0.01 250)",
    "primary":    "oklch(0.65 0.20 250)",
    "primary_l":  "oklch(0.70 0.24 250)",
    "success":    "oklch(0.65 0.22 145)",
}

# 视频扩展名
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


# ── 缩略图生成线程 ──────────────────────────────────────────
class ThumbnailWorker(QThread):
    """后台线程生成缩略图"""
    thumbnail_ready = Signal(str, str)  # path, thumbnail_path
    finished = Signal()

    def __init__(self, video_paths: list, parent=None):
        super().__init__(parent)
        self._paths = video_paths

    def run(self):
        for path in self._paths:
            thumb = self._generate_one(path)
            self.thumbnail_ready.emit(path, thumb)
        self.finished.emit()

    def _generate_one(self, video_path: str) -> str:
        """生成单个视频缩略图"""
        thumb_dir = os.path.join(os.path.dirname(video_path), ".voxplore_thumbs")
        os.makedirs(thumb_dir, exist_ok=True)
        thumb_path = os.path.join(thumb_dir, f"{Path(video_path).stem}_thumb.jpg")

        if os.path.exists(thumb_path):
            return thumb_path

        try:
            subprocess.run([
                "ffmpeg", "-y", "-ss", "1",
                "-i", video_path,
                "-vframes", "1",
                "-q:v", "3",
                "-vf", "scale=160:90",
                thumb_path,
            ], capture_output=True, timeout=15)
        except Exception:
            pass

        return thumb_path if os.path.exists(thumb_path) else ""


# ── 视频缩略图列表项 ────────────────────────────────────────
class VideoThumbnailItem(QWidget):
    """单个视频缩略图卡片（用于列表展示）"""
    clicked = Signal(str)
    selection_changed = Signal(str, bool)  # path, selected

    _CHECKED_FILES = set()  # 类级别已选中文件集合

    def __init__(self, video_path: str, parent=None):
        super().__init__(parent)
        self._path = video_path
        self._thumb_path = ""
        self._selected = False
        self._setup_ui()

    def _setup_ui(self):
        self.setFixedSize(160, 140)
        self.setStyleSheet(f"""
            QWidget {{
                background: {_T['bg_card']};
                border: 1px solid {_T['border']};
                border-radius: 10px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # 复选框行
        cb_layout = QHBoxLayout()
        cb_layout.addStretch()
        self._cb = QCheckBox()
        self._cb.setFixedSize(18, 18)
        self._cb.stateChanged.connect(self._on_check)
        self._cb_layout = QVBoxLayout()
        self._cb_layout.addWidget(self._cb)
        self._cb_layout.addStretch()
        cb_layout.addLayout(self._cb_layout)
        layout.addLayout(cb_layout)

        # 缩略图
        self._thumb_label = QLabel()
        self._thumb_label.setFixedSize(148, 84)
        self._thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumb_label.setStyleSheet("border-radius: 6px; background: #0a0a0a;")
        self._thumb_label.setText("🎬")
        self._thumb_label.setFont(QFont("", 28))
        layout.addWidget(self._thumb_label)

        # 文件名
        self._name_label = QLabel(Path(self._path).name)
        self._name_label.setFont(QFont("", 9))
        self._name_label.setStyleSheet(f"color: {_T['text_muted']};")
        self._name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._name_label.setWordWrap(True)
        self._name_label.setFixedHeight(24)
        layout.addWidget(self._name_label)

    def set_thumbnail(self, thumb_path: str):
        """设置缩略图路径"""
        self._thumb_path = thumb_path
        if thumb_path and os.path.exists(thumb_path):
            pixmap = QPixmap(thumb_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(148, 84, Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
                self._thumb_label.setPixmap(scaled)
                self._thumb_label.setText("")

    def _on_check(self, state):
        self._selected = state == Qt.CheckState.Checked.value
        if self._selected:
            VideoThumbnailItem._CHECKED_FILES.add(self._path)
        else:
            VideoThumbnailItem._CHECKED_FILES.discard(self._path)
        self.selection_changed.emit(self._path, self._selected)
        self._update_border()

    def _update_border(self):
        color = _T['primary'] if self._selected else _T['border']
        self.setStyleSheet(f"""
            QWidget {{
                background: {_T['bg_card']};
                border: 2px solid {color};
                border-radius: 10px;
            }}
        """)

    @property
    def video_path(self) -> str:
        return self._path

    @classmethod
    def get_checked_files(cls) -> set:
        return cls._CHECKED_FILES.copy()

    @classmethod
    def clear_checked(cls):
        cls._CHECKED_FILES.clear()


# ── 视频预览播放器（小窗）────────────────────────────────────
class VideoPreviewWidget(QFrame):
    """小尺寸视频预览（用于选择文件后预览）"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._player = QMediaPlayer()
        self._audio = QAudioOutput()
        self._player.setAudioOutput(self._audio)
        self._setup_ui()

    def _setup_ui(self):
        self.setFixedSize(320, 180)
        self.setStyleSheet(f"""
            QFrame {{
                background: #000;
                border-radius: 12px;
                border: 1px solid {_T['border']};
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._video_widget = QVideoWidget()
        self._video_widget.setMinimumSize(320, 180)
        self._player.setVideoOutput(self._video_widget)
        layout.addWidget(self._video_widget)

        # 底部信息栏
        self._info_label = QLabel("未选择视频")
        self._info_label.setFont(QFont("", 10))
        self._info_label.setStyleSheet(f"""
            color: {_T['text_muted']};
            background: rgba(0,0,0,0.7);
            padding: 4px 8px;
        """)
        self._info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._info_label.setFixedHeight(24)

    def load(self, path: str):
        """加载视频预览"""
        if os.path.exists(path):
            from PySide6.QtCore import QUrl
            self._player.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
            self._info_label.setText(Path(path).name)
            self._player.play()

    def stop(self):
        self._player.stop()


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


# ── 视频元数据面板 ─────────────────────────────────────────
class VideoMetadataPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background: {_T['bg_card']};
                border-radius: 12px;
                border: 1px solid {_T['border']};
            }}
        """)
        layout = QGridLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setHorizontalSpacing(24)
        layout.setVerticalSpacing(8)
        self.labels = {}
        for i, (key, label_text) in enumerate([
            ("duration", "时长"), ("resolution", "分辨率"),
            ("size", "文件大小"), ("format", "格式"),
        ]):
            lbl_name = QLabel(label_text)
            lbl_name.setStyleSheet(f"color: {_T['text_muted']}; font-size: 12px;")
            layout.addWidget(lbl_name, i, 0)
            lbl_value = QLabel("—")
            lbl_value.setStyleSheet(f"color: {_T['text']}; font-size: 12px; font-weight: 600;")
            layout.addWidget(lbl_value, i, 1)
            self.labels[key] = lbl_value

    def set_metadata(self, path: str):
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json",
                 "-show_format", "-show_streams", path],
                capture_output=True, text=True, timeout=10
            )
            data = json.loads(result.stdout)
            fmt = data.get("format", {})
            dur = float(fmt.get("duration", 0))
            self.labels["duration"].setText(f"{int(dur//60):02d}:{int(dur%60):02d}")
            for s in data.get("streams", []):
                if s.get("codec_type") == "video":
                    self.labels["resolution"].setText(f"{s.get('width','?')}×{s.get('height','?')}")
                    break
            size = int(fmt.get("size", 0))
            if size > 1024**3: self.labels["size"].setText(f"{size/1024**3:.1f} GB")
            elif size > 1024**2: self.labels["size"].setText(f"{size/1024**2:.0f} MB")
            else: self.labels["size"].setText(f"{size/1024:.0f} KB")
            self.labels["format"].setText(fmt.get("format_name", "").split(",")[0])
        except Exception as e:
            logging.getLogger(__name__).warning(f"获取文件信息失败: {e}")


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
        self._style_combo(self._emotion_combo)
        gl.addWidget(self._emotion_combo, 1, 1, 1, 2)

        style_lbl = QLabel("解说长度")
        style_lbl.setStyleSheet(f"color: {_T['text_sub']}; font-size: 13px;")
        gl.addWidget(style_lbl, 2, 0)
        self._style_combo_widget = QComboBox()
        self._style_combo_widget.addItems(["简洁版", "标准版", "详细版"])
        self._style_combo(self._style_combo_widget)
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

    def _style_combo(self, combo: QComboBox):
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
