#!/usr/bin/env python3
"""缩略图生成线程组件

从 step_upload.py 提取 ThumbnailWorker
"""

import logging
import os
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from scenefab.utils.security import SecurityError, get_ffmpeg_executor

logger = logging.getLogger(__name__)
_video_executor = get_ffmpeg_executor()


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
        thumb_dir = os.path.join(os.path.dirname(video_path), ".scenefab_thumbs")
        os.makedirs(thumb_dir, exist_ok=True)
        thumb_path = os.path.join(thumb_dir, f"{Path(video_path).stem}_thumb.jpg")

        if os.path.exists(thumb_path):
            return thumb_path

        try:
            result = _video_executor.run(
                [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    "1",
                    "-i",
                    video_path,
                    "-vframes",
                    "1",
                    "-q:v",
                    "3",
                    "-vf",
                    "scale=160:90",
                    thumb_path,
                ],
                timeout=15,
            )
            if result.returncode != 0:
                logger.warning(f"Thumbnail generation failed: {result.stderr}")
        except SecurityError as e:
            logger.debug(f"Thumbnail generation error: {e}")
        except Exception as e:
            logger.debug(f"Thumbnail generation error: {e}")

        return thumb_path if os.path.exists(thumb_path) else ""
