#!/usr/bin/env python3
"""智能分组结果展示页面

Task 2.2 UX 改善:
- 分组预览卡片：每组视频缩略图网格（2-3列）
- 手动合并/拆分：用户可拖拽视频到不同分组
- 置信度显示：每组显示AI分组置信度百分比
"""

import json
import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDrag, QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# 导入拖拽辅助组件
from .components.drag_helpers import MIME_TYPE, _GroupThumbItem, _VideoMimeData

logger = logging.getLogger(__name__)


# ── OKLCH Design Tokens ──────────────────────────────────────
_T = {
    "bg_card": "oklch(0.16 0.01 250)",
    "bg_input": "oklch(0.13 0.01 250)",
    "bg_hover": "oklch(0.14 0.01 250)",
    "bg_active": "oklch(0.17 0.01 250)",
    "border": "oklch(0.24 0.01 250)",
    "border_h": "oklch(0.30 0.02 250)",
    "text": "oklch(0.93 0.01 250)",
    "text_sub": "oklch(0.75 0.01 250)",
    "text_muted": "oklch(0.55 0.01 250)",
    "primary": "oklch(0.65 0.20 250)",
    "primary_l": "oklch(0.70 0.24 250)",
    "success": "oklch(0.65 0.22 145)",
    "warning": "oklch(0.75 0.20 85)",
    "error": "oklch(0.63 0.24 25)",
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

    def __init__(
        self, group_id: object, group_label: str, confidence: float = 0.0, parent=None
    ):
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
                background: {_T["bg_card"]};
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
                background: {_T["bg_input"]};
                border-bottom: 1px solid {_T["border"]};
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
                color: {_T["text"]};
                border: none;
                padding: 2px 4px;
            }}
            QLineEdit:focus {{
                border: 1px solid {_T["border_h"]};
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
                background: {_T["bg_input"]};
                border-radius: 4px;
                width: 6px;
                margin: 2px 0;
            }}
            QScrollBar::handle:vertical {{
                background: {_T["border_h"]};
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
                background: {_T["bg_input"]};
                border-top: 1px solid {_T["border"]};
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
                color: {_T["error"]};
                border: 1px solid {_T["error"]}60;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: {_T["error"]}20;
            }}
        """)
        self._delete_btn.setFixedSize(80, 28)
        self._delete_btn.clicked.connect(self._on_delete_group)
        footer_layout.addWidget(self._delete_btn)

        layout.addWidget(footer)

    def _get_confidence_color(self) -> str:
        if self._confidence >= 0.8:
            return _T["success"]
        elif self._confidence >= 0.6:
            return _T["warning"]
        return _T["error"]

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
            if hasattr(w, "video_path") and w.video_path == path:
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
                background: {_T["bg_card"]};
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
        if event.mimeData().hasFormat(MIME_TYPE):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(MIME_TYPE):
            event.acceptProposedAction()

    def dropEvent(self, event):
        mime = event.mimeData()
        if mime.hasFormat(MIME_TYPE):
            data = mime.data(MIME_TYPE)
            try:
                info = json.loads(bytes(data).decode("utf-8"))
                video_path = info.get("path", "")
                info.get("group_id")
            except json.JSONDecodeError as e:
                logger.debug(f"Invalid JSON in drop data: {e}")
                video_path = ""
            except Exception as e:
                logger.debug(f"Drop data parsing error: {e}")
                video_path = ""

            if video_path:
                self.video_dropped.emit(video_path, self._group_id)
            event.acceptProposedAction()


# ── 智能分组页面 ────────────────────────────────────────────
