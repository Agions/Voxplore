#!/usr/bin/env python3
"""智能分组结果展示页面

Task 2.2 UX 改善:
- 分组预览卡片：每组视频缩略图网格（2-3列）
- 手动合并/拆分：用户可拖拽视频到不同分组
- 置信度显示：每组显示AI分组置信度百分比
"""

import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

# 导入拖拽辅助组件

logger = logging.getLogger(__name__)




VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


# ── 分组卡片（可接收拖拽）───────────────────────────────────

from scenefab.ui.main.pages._group_card import GroupCard
from scenefab.ui.theme.ds_tokens import _C


class StepGroup(QWidget):
    """
    智能分组结果展示页面
    展示 AI 分析后的视频分组结果，支持手动合并/拆分
    """

    group_confirmed = Signal(list)  # 确认后的分组列表
    back_requested = Signal()
    next_requested = Signal(list)  # 分组后的路径列表

    def __init__(self, video_paths: list = None, parent=None):  # type: ignore[assignment]
        super().__init__(parent)
        self._all_videos = list(video_paths) if video_paths else []
        self._groups = []  # type: ignore[var-annotated]  # list of (group_id, label, confidence, videos)
        self._ungrouped = []  # type: ignore[var-annotated]  # 尚未分组的视频
        self._group_counter = 0
        self._setup_ui()

        if self._all_videos:
            self._generate_demo_groups()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)
        self._setup_header(layout)
        self._setup_hint(layout)
        self._setup_groups_scroll(layout)
        self._setup_ungrouped_area(layout)
        self._setup_progress_bar(layout)
        self._setup_bottom_actions(layout)

    def _setup_header(self, layout: QVBoxLayout):
        """标题栏：返回按钮、标题、总览标签"""
        header = QHBoxLayout()
        back_btn = QPushButton("← 上传")
        back_btn.setObjectName("secondary_btn")
        back_btn.setFixedSize(90, 36)
        back_btn.clicked.connect(self.back_requested.emit)
        header.addWidget(back_btn)

        title = QLabel("智能分组")
        title.setFont(QFont("", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {_C.TEXT_PRIMARY};")
        header.addWidget(title)
        header.addStretch()

        self._overview_label = QLabel("0 个视频，0 个分组")
        self._overview_label.setStyleSheet(
            f"color: {_C.TEXT_MUTED}; font-size: 12px;"
        )
        header.addWidget(self._overview_label)
        layout.addLayout(header)

    def _setup_hint(self, layout: QVBoxLayout):
        """副标题提示"""
        hint = QLabel(
            "AI 已根据场景、内容和角色自动分组。您可以拖拽调整，或手动合并/拆分"
        )
        hint.setStyleSheet(f"color: {_C.TEXT_MUTED}; font-size: 12px;")
        layout.addWidget(hint)

    def _setup_groups_scroll(self, layout: QVBoxLayout):
        """分组卡片区域（横向可滚动）"""
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
                background: {_C.BG_INPUT};
                border-radius: 4px;
                height: 8px;
                margin: 0 2px;
            }}
            QScrollBar::handle:horizontal {{
                background: {_C.BORDER_STRONG};
                border-radius: 4px;
            }}
        """)
        self._groups_container = QWidget()
        self._groups_layout = QHBoxLayout(self._groups_container)
        self._groups_layout.setSpacing(16)
        self._groups_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        scroll.setWidget(self._groups_container)
        layout.addWidget(scroll, stretch=1)

    def _setup_ungrouped_area(self, layout: QVBoxLayout):
        """未分组视频区域"""
        self._ungrouped_area = QFrame()
        self._ungrouped_area.setVisible(False)
        self._ungrouped_area.setStyleSheet(f"""
            QFrame {{
                background: {_C.BG_SURFACE};
                border: 2px dashed {_C.BORDER_DEFAULT};
                border-radius: 12px;
            }}
        """)
        un_layout = QVBoxLayout(self._ungrouped_area)
        un_layout.setContentsMargins(12, 12, 12, 12)
        un_label = QLabel("未分组视频（拖入上方分组）")
        un_label.setStyleSheet(f"color: {_C.TEXT_MUTED}; font-size: 11px;")
        un_layout.addWidget(un_label)
        self._un_layout = QGridLayout()
        self._un_layout.setSpacing(8)
        un_layout.addLayout(self._un_layout)
        layout.addWidget(self._ungrouped_area)

    def _setup_progress_bar(self, layout: QVBoxLayout):
        """分析进度条"""
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setVisible(False)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {_C.BG_INPUT};
                border: 1px solid {_C.BORDER_DEFAULT};
                border-radius: 6px;
                height: 8px;
                text-align: center;
                color: transparent;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {_C.PRIMARY}, stop:1 {_C.PRIMARY_DARKER});
                border-radius: 6px;
            }}
        """)
        layout.addWidget(self._progress_bar)

    def _setup_bottom_actions(self, layout: QVBoxLayout):
        """底部操作按钮"""
        btn_layout = QHBoxLayout()
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
            ("场景A", 0.92, self._all_videos[: len(self._all_videos) // 2]),
            ("场景B", 0.78, self._all_videos[len(self._all_videos) // 2 :]),
        ]
        for label, conf, videos in demo_groups:
            self._group_counter += 1
            gid = self._group_counter
            card = self._add_group_card(gid, label, conf, videos)
            card.video_dropped.connect(self._on_video_dropped)

    def _add_group_card(
        self, group_id, label: str, confidence: float, videos: list
    ) -> GroupCard:
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
            self._group_counter, f"分组 {self._group_counter}", 0.0, []
        )
        card.set_confidence(0.0)
        card.setStyleSheet(f"""
            QFrame {{
                background: {_C.BG_SURFACE};
                border: 2px solid {_C.BORDER_DEFAULT};
                border-radius: 16px;
            }}
        """)

    def _on_video_dropped(self, video_path: str, target_group_id):
        """处理视频拖拽到分组"""
        if video_path is None and target_group_id == "DELETE_GROUP":  # type: ignore[unreachable]
            return  # type: ignore[unreachable]

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
                        if hasattr(w, "video_path") and w.video_path == video_path:
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
