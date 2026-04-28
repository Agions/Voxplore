#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""智能分组结果展示页面

Task 2.2 UX 改善:
- 分组预览卡片：每组视频缩略图网格（2-3列）
- 手动合并/拆分：用户可拖拽视频到不同分组
- 置信度显示：每组显示AI分组置信度百分比
"""

import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QSizePolicy, QProgressBar, QLineEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap, QDrag


# ── OKLCH Design Tokens ──────────────────────────────────────
_T = {
    "bg_card":     "oklch(0.16 0.01 250)",
    "bg_input":    "oklch(0.13 0.01 250)",
    "bg_hover":    "oklch(0.14 0.01 250)",
    "bg_active":   "oklch(0.17 0.01 250)",
    "border":      "oklch(0.24 0.01 250)",
    "border_h":    "oklch(0.30 0.02 250)",
    "text":        "oklch(0.93 0.01 250)",
    "text_sub":    "oklch(0.75 0.01 250)",
    "text_muted":  "oklch(0.55 0.01 250)",
    "primary":     "oklch(0.65 0.20 250)",
    "primary_l":   "oklch(0.70 0.24 250)",
    "success":     "oklch(0.65 0.22 145)",
    "warning":     "oklch(0.75 0.20 85)",
    "error":       "oklch(0.63 0.24 25)",
}

VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


# ── 分组卡片（可接收拖拽）───────────────────────────────────
class GroupCard(QFrame):
    """
    单个分组卡片，内含缩略图网格
    支持视频项拖入（合并）/拖出（拆分）
    """
    video_dropped = Signal(str, object)  # video_path, group_id
    confidence_changed = Signal(object, float)  # group_id, new_confidence

    def __init__(self, group_id: object, group_label: str, confidence: float = 0.0,
                 parent=None):
        super().__init__(parent)
        self._group_id = group_id
        self._group_label = group_label
        self._confidence = confidence
        self._video_items = []  # 当前分组内的视频路径列表
        self._setup_ui()
        self.setAcceptDrops(True)

    def _setup_ui(self):
        # 动态边框颜色（置信度 > 80% 绿色，60-80% 黄色，< 60% 红色）
        conf_color = self._get_confidence_color()

        self.setStyleSheet(f"""
            QFrame {{
                background: {_T['bg_card']};
                border: 2px solid {conf_color};
                border-radius: 16px;
                padding: 0px;
            }}
        """)
        self.setMinimumWidth(340)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── 头部：分组标题 + 置信度 + 操作按钮 ──
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background: {_T['bg_input']};
                border-bottom: 1px solid {_T['border']};
                border-radius: 14px 14px 0 0;
            }}
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(12)

        # 拖拽手柄
        self._drag_handle = QLabel("⋮⋮")
        self._drag_handle.setFont(QFont("", 14))
        self._drag_handle.setStyleSheet(f"color: {_T['text_muted']};")
        self._drag_handle.setCursor(Qt.CursorShape.SizeAllCursor)
        header_layout.addWidget(self._drag_handle)

        # 分组标签
        self._label_edit = QLineEdit(self._group_label)
        self._label_edit.setFont(QFont("", 13, QFont.Weight.SemiBold))
        self._label_edit.setStyleSheet(f"""
            QLineEdit {{
                background: transparent;
                color: {_T['text']};
                border: none;
                padding: 2px 4px;
            }}
            QLineEdit:focus {{
                border: 1px solid {_T['border_h']};
                border-radius: 4px;
            }}
        """)
        self._label_edit.textChanged.connect(self._on_label_changed)
        header_layout.addWidget(self._label_edit, stretch=1)

        # 置信度标签
        self._conf_label = QLabel(f"{self._confidence:.0%}")
        self._conf_label.setFont(QFont("", 11, QFont.Weight.Bold))
        self._conf_label.setStyleSheet(f"""
            color: {conf_color};
            background: {conf_color}20;
            padding: 3px 8px;
            border-radius: 8px;
        """)
        self._conf_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self._conf_label)

        # 视频计数
        self._count_label = QLabel("0 个视频")
        self._count_label.setStyleSheet(f"color: {_T['text_muted']}; font-size: 11px;")
        header_layout.addWidget(self._count_label)

        layout.addWidget(header)

        # ── 缩略图网格 ──
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

        self._thumb_grid = QGridLayout()
        self._thumb_grid.setSpacing(8)
        self._thumb_grid.setContentsMargins(12, 12, 12, 12)

        grid_widget = QWidget()
        grid_widget.setLayout(self._thumb_grid)
        scroll.setWidget(grid_widget)
        layout.addWidget(scroll, stretch=1)

        # ── 底部操作栏 ──
        footer = QFrame()
        footer.setStyleSheet(f"""
            QFrame {{
                background: {_T['bg_input']};
                border-top: 1px solid {_T['border']};
                border-radius: 0 0 14px 14px;
            }}
        """)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(12, 8, 12, 8)
        footer_layout.setSpacing(8)

        self._split_btn = QPushButton("拆分")
        self._split_btn.setObjectName("secondary_btn")
        self._split_btn.setFixedSize(60, 28)
        self._split_btn.clicked.connect(self._on_split)
        footer_layout.addWidget(self._split_btn)

        footer_layout.addStretch()

        self._delete_btn = QPushButton("删除分组")
        self._delete_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {_T['error']};
                border: 1px solid {_T['error']}60;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: {_T['error']}20;
            }}
        """)
        self._delete_btn.setFixedSize(80, 28)
        self._delete_btn.clicked.connect(self._on_delete_group)
        footer_layout.addWidget(self._delete_btn)

        layout.addWidget(footer)

    def _get_confidence_color(self) -> str:
        if self._confidence >= 0.8:
            return _T['success']
        elif self._confidence >= 0.6:
            return _T['warning']
        return _T['error']

    def _on_label_changed(self, text: str):
        self._group_label = text

    def add_video(self, video_path: str, thumb_path: str = ""):
        """添加一个视频到当前分组"""
        if video_path in self._video_items:
            return
        self._video_items.append(video_path)
        self._add_thumbnail_item(video_path, thumb_path)
        self._update_count()

    def _add_thumbnail_item(self, path: str, thumb_path: str = ""):
        """添加缩略图到网格"""
        # 计算位置
        count = self._thumb_grid.count()
        row = count // 3
        col = count % 3

        thumb = _GroupThumbItem(path, thumb_path, parent=self)
        thumb.remove_requested.connect(self._on_video_remove)
        thumb.drag_started.connect(lambda p=path: self._on_item_drag_start(p))
        self._thumb_grid.addWidget(thumb, row, col)

    def _on_video_remove(self, path: str):
        """移除视频"""
        if path in self._video_items:
            self._video_items.remove(path)
        # 找到并移除缩略图组件
        for i in range(self._thumb_grid.count()):
            w = self._thumb_grid.itemAt(i).widget()
            if hasattr(w, 'video_path') and w.video_path == path:
                w.setParent(None)
                w.deleteLater()
                break
        self._rearrange_grid()
        self._update_count()

    def _rearrange_grid(self):
        """重新排列网格中的组件"""
        items = []
        for i in range(self._thumb_grid.count()):
            items.append(self._thumb_grid.itemAt(i).widget())
        # 重新按列排
        for i, w in enumerate(items):
            self._thumb_grid.removeWidget(w)
            row = i // 3
            col = i % 3
            self._thumb_grid.addWidget(w, row, col)

    def _on_item_drag_start(self, path: str):
        """视频项开始拖拽"""
        drag = QDrag(self)
        mime_data = _VideoMimeData(path, self._group_id)
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.MoveAction)

    def _on_split(self):
        """拆分：移除最后一个视频"""
        if self._video_items:
            last = self._video_items[-1]
            self._on_video_remove(last)
            # 发送信号让父组件处理（创建新组或移入缓冲区）
            self.video_dropped.emit(last, "SPLIT")

    def _on_delete_group(self):
        """删除分组：把所有视频移出"""
        for v in self._video_items[:]:
            self.video_dropped.emit(v, "DELETE_GROUP")
        self.video_dropped.emit(None, "DELETE_GROUP")

    def _update_count(self):
        self._count_label.setText(f"{len(self._video_items)} 个视频")

    def set_confidence(self, value: float):
        """更新置信度"""
        self._confidence = max(0.0, min(1.0, value))
        color = self._get_confidence_color()
        self._conf_label.setText(f"{self._confidence:.0%}")
        self._conf_label.setStyleSheet(f"""
            color: {color};
            background: {color}20;
            padding: 3px 8px;
            border-radius: 8px;
        """)
        conf_color = self._get_confidence_color()
        self.setStyleSheet(f"""
            QFrame {{
                background: {_T['bg_card']};
                border: 2px solid {conf_color};
                border-radius: 16px;
                padding: 0px;
            }}
        """)

    def get_videos(self) -> list:
        return self._video_items.copy()

    def get_label(self) -> str:
        return self._group_label

    # ── 拖拽支持 ──
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-voxplore-video"):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-voxplore-video"):
            event.acceptProposedAction()

    def dropEvent(self, event):
        mime = event.mimeData()
        if mime.hasFormat("application/x-voxplore-video"):
            data = mime.data("application/x-voxplore-video")
            import json
            try:
                info = json.loads(bytes(data).decode("utf-8"))
                video_path = info.get("path", "")
                info.get("group_id")
            except Exception:
                video_path = ""

            if video_path:
                self.video_dropped.emit(video_path, self._group_id)
            event.acceptProposedAction()


class _GroupThumbItem(QFrame):
    """分组内的视频缩略图项"""
    remove_requested = Signal(str)
    drag_started = Signal(str)

    def __init__(self, video_path: str, thumb_path: str = "", parent=None):
        super().__init__(parent)
        self._path = video_path
        self._thumb = thumb_path
        self.video_path = video_path
        self._setup_ui()
        self.setAcceptDrops(True)
        self.setFixedSize(100, 80)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def _setup_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background: {_T['bg_input']};
                border: 1px solid {_T['border']};
                border-radius: 8px;
            }}
            QFrame:hover {{
                border-color: {_T['primary']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # 缩略图
        self._thumb_label = QLabel()
        self._thumb_label.setFixedSize(92, 52)
        self._thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumb_label.setStyleSheet("border-radius: 4px; background: #000;")
        self._thumb_label.setText("🎬")
        self._thumb_label.setFont(QFont("", 20))

        if self._thumb and os.path.exists(self._thumb):
            pixmap = QPixmap(self._thumb)
            if not pixmap.isNull():
                scaled = pixmap.scaled(92, 52, Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
                self._thumb_label.setPixmap(scaled)
                self._thumb_label.setText("")

        layout.addWidget(self._thumb_label)

        # 文件名（截断）
        name = Path(self._path).name
        if len(name) > 12:
            name = name[:10] + "…"
        self._name_label = QLabel(name)
        self._name_label.setFont(QFont("", 8))
        self._name_label.setStyleSheet(f"color: {_T['text_muted']};")
        self._name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._name_label)

        # 移除按钮（悬停显示）
        self._remove_btn = QPushButton("✕")
        self._remove_btn.setFont(QFont("", 8))
        self._remove_btn.setFixedSize(16, 16)
        self._remove_btn.setStyleSheet(f"""
            QPushButton {{
                background: {_T['error']};
                color: white;
                border-radius: 8px;
                padding: 0px;
            }}
        """)
        self._remove_btn.clicked.connect(lambda: self.remove_requested.emit(self._path))
        self._remove_btn.setVisible(False)
        layout.addWidget(self._remove_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self._name_label.mousePressEvent = self._on_mouse_press

    def _on_mouse_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_started.emit(self._path)

    def enterEvent(self, event):
        self._remove_btn.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._remove_btn.setVisible(False)
        super().leaveEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.drag_started.emit(self._path)
            drag = QDrag(self)
            mime_data = _VideoMimeData(self._path, None)
            drag.setMimeData(mime_data)
            drag.exec(Qt.DropAction.MoveAction)


class _VideoMimeData(QFrame):
    """自定义拖拽数据（用于跨分组拖拽）"""
    def __init__(self, video_path: str, group_id, parent=None):
        super().__init__(parent)
        import json
        self._data = json.dumps({"path": video_path, "group_id": str(group_id)}).encode("utf-8")

    def data(self, mime_type: str) -> bytes:
        if mime_type == "application/x-voxplore-video":
            return self._data
        return b""


# ── 智能分组页面 ────────────────────────────────────────────
class StepGroup(QWidget):
    """
    智能分组结果展示页面
    展示 AI 分析后的视频分组结果，支持手动合并/拆分
    """
    group_confirmed = Signal(list)  # 确认后的分组列表
    back_requested = Signal()
    next_requested = Signal(list)  # 分组后的路径列表

    def __init__(self, video_paths: list = None, parent=None):
        super().__init__(parent)
        self._all_videos = list(video_paths) if video_paths else []
        self._groups = []  # list of (group_id, label, confidence, videos)
        self._ungrouped = []  # 尚未分组的视频
        self._group_counter = 0
        self._setup_ui()

        if self._all_videos:
            self._generate_demo_groups()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        # ── 标题栏 ──
        header = QHBoxLayout()
        back_btn = QPushButton("← 上传")
        back_btn.setObjectName("secondary_btn")
        back_btn.setFixedSize(90, 36)
        back_btn.clicked.connect(self.back_requested.emit)
        header.addWidget(back_btn)

        title = QLabel("智能分组")
        title.setFont(QFont("", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {_T['text']};")
        header.addWidget(title)
        header.addStretch()

        # 总览标签
        self._overview_label = QLabel("0 个视频，0 个分组")
        self._overview_label.setStyleSheet(f"color: {_T['text_muted']}; font-size: 12px;")
        header.addWidget(self._overview_label)
        layout.addLayout(header)

        # 副标题
        hint = QLabel("AI 已根据场景、内容和角色自动分组。您可以拖拽调整，或手动合并/拆分")
        hint.setStyleSheet(f"color: {_T['text_muted']}; font-size: 12px;")
        layout.addWidget(hint)

        # ── 分组卡片区域（可滚动）────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QScrollBar:horizontal {{
                background: {_T['bg_input']};
                border-radius: 4px;
                height: 8px;
                margin: 0 2px;
            }}
            QScrollBar::handle:horizontal {{
                background: {_T['border_h']};
                border-radius: 4px;
            }}
        """)

        # 分组卡片容器（横向滚动）
        self._groups_container = QWidget()
        self._groups_layout = QHBoxLayout(self._groups_container)
        self._groups_layout.setSpacing(16)
        self._groups_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        scroll.setWidget(self._groups_container)
        layout.addWidget(scroll, stretch=1)

        # ── 未分组视频区（若有）──────────────────────────────
        self._ungrouped_area = QFrame()
        self._ungrouped_area.setVisible(False)
        self._ungrouped_area.setStyleSheet(f"""
            QFrame {{
                background: {_T['bg_card']};
                border: 2px dashed {_T['border']};
                border-radius: 12px;
            }}
        """)
        un_layout = QVBoxLayout(self._ungrouped_area)
        un_layout.setContentsMargins(12, 12, 12, 12)
        un_label = QLabel("未分组视频（拖入上方分组）")
        un_label.setStyleSheet(f"color: {_T['text_muted']}; font-size: 11px;")
        un_layout.addWidget(un_label)

        self._un_layout = QGridLayout()
        self._un_layout.setSpacing(8)
        un_layout.addLayout(self._un_layout)
        layout.addWidget(self._ungrouped_area)

        # ── 进度条（分析进度）───────────────────────────────
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

        # ── 底部操作 ────────────────────────────────────────
        btn_layout = QHBoxLayout()

        # 新增分组按钮
        self._new_group_btn = QPushButton("+ 新建分组")
        self._new_group_btn.setObjectName("secondary_btn")
        self._new_group_btn.setFixedSize(110, 40)
        self._new_group_btn.clicked.connect(self._add_new_group)
        btn_layout.addWidget(self._new_group_btn)

        btn_layout.addStretch()

        self._next_btn = QPushButton("生成解说 →")
        self._next_btn.setObjectName("primary_btn")
        self._next_btn.setFixedSize(140, 44)
        self._next_btn.clicked.connect(self._on_next)
        btn_layout.addWidget(self._next_btn)
        layout.addLayout(btn_layout)

    def _generate_demo_groups(self):
        """生成演示分组（实际由 AI 调用产生）"""
        # 模拟三个分组
        demo_groups = [
            ("场景A", 0.92, self._all_videos[:len(self._all_videos)//2]),
            ("场景B", 0.78, self._all_videos[len(self._all_videos)//2:]),
        ]
        for label, conf, videos in demo_groups:
            self._group_counter += 1
            gid = self._group_counter
            card = self._add_group_card(gid, label, conf, videos)
            card.video_dropped.connect(self._on_video_dropped)

    def _add_group_card(self, group_id, label: str, confidence: float,
                        videos: list) -> GroupCard:
        """创建并添加一个分组卡片"""
        card = GroupCard(group_id, label, confidence)
        for v in videos:
            card.add_video(v)
        card.video_dropped.connect(self._on_video_dropped)
        self._groups_layout.addWidget(card)
        self._groups.append(card)
        self._update_overview()
        return card

    def _add_new_group(self):
        """新增一个空分组"""
        self._group_counter += 1
        card = self._add_group_card(
            self._group_counter,
            f"分组 {self._group_counter}",
            0.0,
            []
        )
        card.set_confidence(0.0)
        card.setStyleSheet(f"""
            QFrame {{
                background: {_T['bg_card']};
                border: 2px solid {_T['border']};
                border-radius: 16px;
            }}
        """)

    def _on_video_dropped(self, video_path: str, target_group_id):
        """处理视频拖拽到分组"""
        if video_path is None and target_group_id == "DELETE_GROUP":
            return

        if target_group_id == "SPLIT":
            # 从原组移除后暂存（可在_ungrouped_area显示）
            return

        # 找到目标分组
        target_card = None
        for card in self._groups:
            if card._group_id == target_group_id:
                target_card = card
                break

        if target_card and video_path:
            # 从其他分组移除（如果存在）
            for card in self._groups:
                if video_path in card.get_videos():
                    # 触发移除
                    for i in range(card._thumb_grid.count()):
                        w = card._thumb_grid.itemAt(i).widget()
                        if hasattr(w, 'video_path') and w.video_path == video_path:
                            w.setParent(None)
                            w.deleteLater()
                    if video_path in card._video_items:
                        card._video_items.remove(video_path)
                    card._rearrange_grid()
                    card._update_count()
                    break

            target_card.add_video(video_path)
            self._update_overview()

    def _update_overview(self):
        total = sum(len(c.get_videos()) for c in self._groups)
        self._overview_label.setText(f"{total} 个视频，{len(self._groups)} 个分组")

    def _on_next(self):
        # 收集所有分组视频路径
        all_paths = []
        for card in self._groups:
            all_paths.extend(card.get_videos())
        self.next_requested.emit(all_paths)

    # ── 模拟分析进度（演示用）───────────────────────────────
    def run_analysis(self, progress_callback=None):
        """模拟 AI 分组分析（实际由 AI 服务调用）"""
        self._progress_bar.setVisible(True)
        self._new_group_btn.setEnabled(False)

        def animate():
            for i in range(0, 101, 5):
                self._progress_bar.setValue(i)
                if progress_callback:
                    progress_callback(i)
                import time
                time.sleep(0.05)
            self._progress_bar.setVisible(False)
            self._new_group_btn.setEnabled(True)

        import threading
        t = threading.Thread(target=animate, daemon=True)
        t.start()
