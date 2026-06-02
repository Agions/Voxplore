#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
字幕导出器（支持 SRT / VTT / LRC 格式）

.. note::
    历史：原位于 scenefab.exporters 兼容层，Phase 2 重构中迁移至
    scenefab.services.export.subtitle_exporter。
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class SubtitleExporter:
    """字幕导出器（支持 SRT / VTT / LRC）。"""

    @staticmethod
    def export_srt(subtitles: list[Any], output_path: str) -> bool:
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                for i, sub in enumerate(subtitles, 1):
                    f.write(sub.to_srt(i))
                    f.write('\n')
            logger.info(f"Exported SRT to: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export SRT: {e}")
            return False

    @staticmethod
    def export_vtt(subtitles: list[Any], output_path: str) -> bool:
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("WEBVTT\n\n")
                for i, sub in enumerate(subtitles, 1):
                    start = SubtitleExporter._format_vtt_time(sub.start_time)
                    end = SubtitleExporter._format_vtt_time(sub.end_time)
                    f.write(f"{i}\n{start} --> {end}\n{sub.text}\n\n")
            return True
        except Exception as e:
            logger.error(f"Failed to export VTT: {e}")
            return False

    @staticmethod
    def export_lrc(subtitles: list[Any], output_path: str) -> bool:
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                for sub in subtitles:
                    minutes = int(sub.start_time // 60)
                    seconds = int(sub.start_time % 60)
                    millis = int((sub.start_time % 1) * 100)
                    f.write(f"[{minutes:02d}:{seconds:02d}.{millis:02d}]{sub.text}\n")
            return True
        except Exception as e:
            logger.error(f"Failed to export LRC: {e}")
            return False

    @staticmethod
    def _format_vtt_time(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


__all__ = ["SubtitleExporter"]
