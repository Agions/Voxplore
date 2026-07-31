#!/usr/bin/env python3

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
        def _get_srt(sub: Any, index: int) -> str:
            if isinstance(sub, dict) and "to_srt" in sub:
                return sub["to_srt"](index)
            return sub.to_srt(index)

        content = "".join(
            f"{_get_srt(sub, index)}\n" for index, sub in enumerate(subtitles, 1)
        )
        if SubtitleExporter._write_text(output_path, content, "SRT"):
            logger.info(f"Exported SRT to: {output_path}")
            return True
        return False

    @staticmethod
    def export_vtt(subtitles: list[Any], output_path: str) -> bool:
        cues = []
        for index, sub in enumerate(subtitles, 1):
            start = SubtitleExporter._format_vtt_time(sub.start_time)
            end = SubtitleExporter._format_vtt_time(sub.end_time)
            cues.append(f"{index}\n{start} --> {end}\n{sub.text}\n")
        return SubtitleExporter._write_text(
            output_path, "WEBVTT\n\n" + "\n".join(cues), "VTT"
        )

    @staticmethod
    def export_lrc(subtitles: list[Any], output_path: str) -> bool:
        lines = []
        for sub in subtitles:
            minutes = int(sub.start_time // 60)
            seconds = int(sub.start_time % 60)
            millis = int((sub.start_time % 1) * 100)
            lines.append(f"[{minutes:02d}:{seconds:02d}.{millis:02d}]{sub.text}")
        return SubtitleExporter._write_text(output_path, "\n".join(lines) + "\n", "LRC")

    @staticmethod
    def _write_text(output_path: str, content: str, format_name: str) -> bool:
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error(f"Failed to export {format_name}: {e}")
            return False

    @staticmethod
    def _format_vtt_time(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


__all__ = ["SubtitleExporter"]
