#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
字幕轨道组件

显示和管理同一轨道的所有字幕块。
"""

from typing import Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel
from PySide6.QtCore import Qt, Signal

from ..subtitle_core import SubtitleTrack
from .subtitle_block import SubtitleBlockWidget


class SubtitleTrackWidget(QFrame):
    """
    字幕轨道编辑组件

    显示和管理单个字幕轨道。

    Signals:
        block_selected(str block_id): 字幕块选中信号
        block_changed(str block_id): 字幕块改变信号
        track_changed(str track_id): 轨道改变信号
    """

    block_selected = Signal(str)
    block_changed = Signal(str)
    track_changed = Signal(str)

    def __init__(
        self,
        track: SubtitleTrack,
        style,  # SubtitleStylePreset - imported but unused in this file
        scale: float = 50.0,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)

        self._track = track
        self._style = style
        self._scale = scale
        self._selected_block_id: Optional[str] = None

        self._setup_ui()
        self._setup_styles()

    def _setup_ui(self) -> None:
        """设置UI"""
        self.setObjectName("subtitleTrackWidget")
        self.setMinimumHeight(50)
        self.setMaximumHeight(80)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(60, 4, 12, 4)
        layout.setSpacing(0)

        # 轨道标签
        label = QLabel(self._track.name)
        label.setObjectName("trackLabel")
        label.setFixedWidth(56)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        # 轨道内容区（需要scroll area）
        self._blocks_container = QWidget()
        self._blocks_layout = QVBoxLayout(self._blocks_container)
        self._blocks_layout.setContentsMargins(0, 0, 0, 0)
        self._blocks_layout.setSpacing(2)

        self._update_blocks()

    def _setup_styles(self) -> None:
        """设置样式"""
        self.setStyleSheet("""
            QFrame#subtitleTrackWidget {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 6px;
            }
            QLabel#trackLabel {
                color: #94A3B8;
                font-size: 11px;
                font-weight: 600;
                background-color: #0F172A;
                border-radius: 4px;
                padding: 4px;
            }
        """)

    def set_scale(self, scale: float) -> None:
        """设置缩放比例"""
        self._scale = scale
        self._update_blocks()

    def set_selected_block(self, block_id: Optional[str]) -> None:
        """设置选中的字幕块"""
        self._selected_block_id = block_id
        self._update_blocks()

    def _update_blocks(self) -> None:
        """更新字幕块显示"""
        # 清除现有块
        while self._blocks_layout.count():
            item = self._blocks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 添加字幕块
        for block in sorted(self._track.blocks, key=lambda b: b.start_time):
            block_widget = SubtitleBlockWidget(block, self._style, self._scale)
            block_widget.set_selected(block.id == self._selected_block_id)
            block_widget.block_selected.connect(self.block_selected.emit)
            block_widget.block_changed.connect(self._on_block_changed)
            self._blocks_layout.addWidget(block_widget)

    def _on_block_changed(self, block_id: str) -> None:
        """字幕块改变处理"""
        self.block_changed.emit(block_id)
        self.track_changed.emit(self._track.id)


__all__ = ["SubtitleTrackWidget"]
