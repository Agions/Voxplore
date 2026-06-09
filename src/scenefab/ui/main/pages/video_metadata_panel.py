#!/usr/bin/env python3
"""视频元数据面板组件

从 step_upload.py 提取 VideoMetadataPanel
"""

import json
import logging

from PySide6.QtWidgets import QFrame, QGridLayout, QLabel

from ...utils.security import get_ffmpeg_executor

_video_executor = get_ffmpeg_executor()


# ── OKLCH Design Tokens ──────────────────────────────────────
_T = {
    "bg_card": "oklch(0.16 0.01 250)",
    "border": "oklch(0.24 0.01 250)",
    "text": "oklch(0.93 0.01 250)",
    "text_muted": "oklch(0.55 0.01 250)",
}


# ── 视频元数据面板 ─────────────────────────────────────────
class VideoMetadataPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background: {_T["bg_card"]};
                border-radius: 12px;
                border: 1px solid {_T["border"]};
            }}
        """)
        layout = QGridLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setHorizontalSpacing(24)
        layout.setVerticalSpacing(8)
        self.labels = {}
        for i, (key, label_text) in enumerate(
            [
                ("duration", "时长"),
                ("resolution", "分辨率"),
                ("size", "文件大小"),
                ("format", "格式"),
            ]
        ):
            lbl_name = QLabel(label_text)
            lbl_name.setStyleSheet(f"color: {_T['text_muted']}; font-size: 12px;")
            layout.addWidget(lbl_name, i, 0)
            lbl_value = QLabel("—")
            lbl_value.setStyleSheet(
                f"color: {_T['text']}; font-size: 12px; font-weight: 600;"
            )
            layout.addWidget(lbl_value, i, 1)
            self.labels[key] = lbl_value

    def set_metadata(self, path: str):
        try:
            result = _video_executor.run(
                [
                    "ffprobe",
                    "-v",
                    "quiet",
                    "-print_format",
                    "json",
                    "-show_format",
                    "-show_streams",
                    path,
                ],
                timeout=10,
            )
            data = json.loads(result.stdout)
            fmt = data.get("format", {})
            dur = float(fmt.get("duration", 0))
            self.labels["duration"].setText(f"{int(dur // 60):02d}:{int(dur % 60):02d}")
            for s in data.get("streams", []):
                if s.get("codec_type") == "video":
                    self.labels["resolution"].setText(
                        f"{s.get('width', '?')}×{s.get('height', '?')}"
                    )
                    break
            size = int(fmt.get("size", 0))
            if size > 1024**3:
                self.labels["size"].setText(f"{size / 1024**3:.1f} GB")
            elif size > 1024**2:
                self.labels["size"].setText(f"{size / 1024**2:.0f} MB")
            else:
                self.labels["size"].setText(f"{size / 1024:.0f} KB")
            self.labels["format"].setText(fmt.get("format_name", "").split(",")[0])
        except Exception as e:
            logging.getLogger(__name__).warning(f"获取文件信息失败: {e}")
