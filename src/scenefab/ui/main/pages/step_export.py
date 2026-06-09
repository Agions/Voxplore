#!/usr/bin/env python3
"""
导出步骤页面
"""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from ...main.pages.step_base import ContentCard, StepPage
from ...theme.ds_tokens import _C, FontSizes, Radii


class FormatCard(QFrame):
    """格式选择卡片"""

    format_selected = Signal(str)

    FORMATS = [
        ("mp4", "MP4", "通用性强，画质好", "🎬"),
        ("mov", "MOV", "Apple 专属，高质量", "🍎"),
        ("avi", "AVI", "Windows 兼容", "🪟"),
        ("mkv", "MKV", "支持多音轨/字幕", "📦"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected = "mp4"
        self.setObjectName("format_selector")
        self._setup_style()
        self._setup_ui()

    def _setup_style(self):
        self.setStyleSheet(f"""
            #format_selector {{
                background: {_C.BG_SURFACE};
                border: 1px solid {_C.BORDER_SUBTLE};
                border-radius: {Radii.lg};
            }}
        """)

    def _setup_ui(self):
        layout = QGridLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        for i, (fmt, name, desc, icon) in enumerate(self.FORMATS):
            card = FormatOptionCard(fmt, name, desc, icon, fmt == self._selected)
            card.selected.connect(self._on_select)
            row, col = i // 2, i % 2
            layout.addWidget(card, row, col)

    def _on_select(self, fmt: str):
        self._selected = fmt
        self.format_selected.emit(fmt)


class FormatOptionCard(QFrame):
    """格式选项"""

    selected = Signal(str)

    def __init__(
        self, fmt: str, name: str, desc: str, icon: str, checked: bool, parent=None
    ):
        super().__init__(parent)
        self._fmt = fmt
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("fmt_card")
        self._checked = checked
        self._setup_style()
        self._setup_ui(icon, name, desc)

    def _setup_style(self):
        border_color = _C.PRIMARY_500 if self._checked else _C.BORDER_SUBTLE  # type: ignore[attr-defined]
        self.setStyleSheet(f"""  # type: ignore[attr-defined]
            #fmt_card {{
                background: {_C.BG_SURFACE};
                border: 2px solid {border_color};
                border-radius: {Radii.base};
            }}
            #fmt_card:hover {{
                border-color: {_C.PRIMARY_400};
            }}
        """)

    def _setup_ui(self, icon: str, name: str, desc: str):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        radio = QRadioButton()
        radio.setChecked(self._checked)
        radio.setStyleSheet("""
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        radio.toggled.connect(self._on_toggle)
        layout.addWidget(radio)

        icon_label = QLabel(icon)
        icon_label.setFont(QFont("", 20))
        layout.addWidget(icon_label)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)

        name_label = QLabel(name)
        name_label.setFont(QFont("", FontSizes.sm, QFont.Weight.Medium))
        name_label.setStyleSheet(f"color: {_C.TEXT_PRIMARY};")
        text_layout.addWidget(name_label)

        desc_label = QLabel(desc)
        desc_label.setFont(QFont("", FontSizes.xs))
        desc_label.setStyleSheet(f"color: {_C.TEXT_MUTED};")
        text_layout.addWidget(desc_label)

        layout.addLayout(text_layout, 1)

    def _on_toggle(self, checked: bool):
        if checked:
            self.selected.emit(self._fmt)


class ExportProgress(QFrame):
    """导出进度"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 0
        self.setFixedHeight(140)
        self.setObjectName("export_progress")
        self._setup_style()
        self._setup_ui()

    def _setup_style(self):
        self.setStyleSheet(f"""
            #export_progress {{
                background: {_C.BG_SURFACE};
                border: 1px solid {_C.SUCCESS};
                border-radius: {Radii.lg};
            }}
        """)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        header_layout = QHBoxLayout()
        icon = QLabel("📤")
        icon.setFont(QFont("", 20))
        header_layout.addWidget(icon)

        title = QLabel("正在导出...")
        title.setFont(QFont("", FontSizes.md, QFont.Weight.Medium))
        title.setStyleSheet(f"color: {_C.TEXT_PRIMARY};")
        header_layout.addWidget(title)

        header_layout.addStretch()

        self._percent_label = QLabel("0%")
        self._percent_label.setFont(QFont("", FontSizes.lg, QFont.Weight.Bold))
        self._percent_label.setStyleSheet(f"color: {_C.SUCCESS};")
        header_layout.addWidget(self._percent_label)

        layout.addLayout(header_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(10)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {_C.BG_ELEVATED};
                border: none;
                border-radius: 5px;
            }}
            QProgressBar::chunk {{
                background: {_C.SUCCESS};
                border-radius: 5px;
            }}
        """)
        layout.addWidget(self.progress_bar)

        self._file_label = QLabel("输出: ~/SceneFab/Exports/video_001.mp4")
        self._file_label.setFont(QFont("", FontSizes.xs))
        self._file_label.setStyleSheet(f"color: {_C.TEXT_MUTED};")
        self._file_label.setElideMode(Qt.TextElideMode.ElideMiddle)  # type: ignore[attr-defined]
        layout.addWidget(self._file_label)

    def set_progress(self, value: int):
        self._progress = value
        self.progress_bar.setValue(value)
        self._percent_label.setText(f"{value}%")


class ExportComplete(QFrame):
    """导出完成"""

    open_folder = Signal()
    export_again = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(160)
        self.setObjectName("export_complete")
        self._setup_style()
        self._setup_ui()

    def _setup_style(self):
        self.setStyleSheet(f"""
            #export_complete {{
                background: {_C.BG_SURFACE};
                border: 1px solid {_C.SUCCESS};
                border-radius: {Radii.lg};
            }}
        """)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("✅")
        icon.setFont(QFont("", 40))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

        title = QLabel("导出完成！")
        title.setFont(QFont("", FontSizes.xl, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {_C.SUCCESS};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(16)

        folder_btn = QPushButton("📂 打开文件夹")
        folder_btn.setObjectName("btn_secondary")
        folder_btn.setFixedSize(140, 40)
        folder_btn.clicked.connect(self.open_folder.emit)
        btn_layout.addWidget(folder_btn)

        again_btn = QPushButton("🔄 再次导出")
        again_btn.setObjectName("btn_primary")
        again_btn.setFixedSize(120, 40)
        again_btn.clicked.connect(self.export_again.emit)
        btn_layout.addWidget(again_btn)

        layout.addLayout(btn_layout)


class StepExportPage(StepPage):
    """导出步骤页 (step 3)"""

    def __init__(self, parent=None):
        super().__init__(3, parent)  # type: ignore[call-arg]
        self._exporting = False

    def _build_content(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(24)

        # 格式选择
        format_label = QLabel("选择导出格式")
        format_label.setFont(QFont("", FontSizes.md, QFont.Weight.Semibold))  # type: ignore[attr-defined]
        format_label.setStyleSheet(f"color: {_C.TEXT_PRIMARY};")
        layout.addWidget(format_label)

        format_card = FormatCard()
        layout.addWidget(format_card)

        # 画质设置
        quality_card = ContentCard("画质设置")
        qual_layout = quality_card.layout()

        qual_row = QHBoxLayout()
        qual_row.addWidget(QLabel("分辨率"))
        qual_row.addStretch()

        res_combo = QComboBox()
        res_combo.addItems(
            ["1080P (1920×1080)", "720P (1280×720)", "4K (3840×2160)", "原始分辨率"]
        )
        res_combo.setFixedWidth(200)
        res_combo.setStyleSheet(f"""
            QComboBox {{
                background: {_C.BG_ELEVATED};
                border: 1px solid {_C.BORDER_DEFAULT};
                border-radius: {Radii.sm};
                padding: 6px 12px;
                color: {_C.TEXT_PRIMARY};
            }}
        """)
        qual_row.addWidget(res_combo)
        qual_layout.addLayout(qual_row)  # type: ignore[union-attr]

        fps_row = QHBoxLayout()
        fps_row.addWidget(QLabel("帧率"))
        fps_row.addStretch()

        fps_combo = QComboBox()
        fps_combo.addItems(["30 fps", "60 fps", "24 fps", "原始帧率"])
        fps_combo.setFixedWidth(200)
        fps_combo.setStyleSheet(qual_layout.itemAt(0).spacerItem())  # type: ignore[arg-type, union-attr]
        fps_row.addWidget(fps_combo)
        qual_layout.addLayout(fps_row)  # type: ignore[union-attr]

        layout.addWidget(quality_card)

        # 进度区（初始隐藏）
        self.progress_widget = ExportProgress()
        self.progress_widget.setVisible(False)
        layout.addWidget(self.progress_widget)

        # 完成区（初始隐藏）
        self.complete_widget = ExportComplete()
        self.complete_widget.setVisible(False)
        self.complete_widget.open_folder.connect(self._open_folder)
        self.complete_widget.export_again.connect(self._reset)
        layout.addWidget(self.complete_widget)

        layout.addStretch()

        # 导出按钮
        self.export_btn = QPushButton("📤 开始导出")
        self.export_btn.setObjectName("btn_primary")
        self.export_btn.setFixedSize(180, 44)
        self.export_btn.setFont(QFont("", FontSizes.md, QFont.Weight.Medium))
        self.export_btn.clicked.connect(self._start_export)
        layout.addWidget(self.export_btn, alignment=Qt.AlignmentFlag.AlignHCenter)

        return container

    def _start_export(self):
        if self._exporting:
            return
        self._exporting = True
        self.export_btn.setVisible(False)
        self.progress_widget.setVisible(True)
        self._progress = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_progress)
        self._timer.start(80)

    def _update_progress(self):
        self._progress += 1
        self.progress_widget.set_progress(self._progress)
        if self._progress >= 100:
            self._timer.stop()
            self._exporting = False
            self.progress_widget.setVisible(False)
            self.complete_widget.setVisible(True)

    def _open_folder(self):
        import subprocess
        import sys
        from pathlib import Path

        export_dir = Path.home() / "SceneFab" / "Exports"
        if not export_dir.exists():
            return
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", str(export_dir)], check=False)
            else:
                subprocess.run(["xdg-open", str(export_dir)], check=False)
        except FileNotFoundError:
            pass

    def _reset(self):
        self.complete_widget.setVisible(False)
        self.export_btn.setVisible(True)
        self._progress = 0