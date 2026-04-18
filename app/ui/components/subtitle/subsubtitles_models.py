#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Subtitle Exporter and Importer

多轨道字幕系统的导入导出功能。

支持格式:
- SRT (SubRip)
- VTT (WebVTT)
- ASS (Advanced SubStation Alpha)
- JSON (内部格式)
- 剪映草稿格式
"""

import re
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from .subsubtitles import (
    SubtitleStylePreset,
    SubtitleBlock,
    SubtitleTrack,
    MultiTrackSubtitleEditor,
    DEFAULT_PRESETS,
)


# ─────────────────────────────────────────────────────────────
# 字幕导出器
# ─────────────────────────────────────────────────────────────

class SubtitleExporter:
    """
    字幕导出器
    
    将多轨道字幕编辑器导出为各种格式。
    """
    
    @staticmethod
    def to_srt(editor: MultiTrackSubtitleEditor, track_id: str = None) -> str:
        """
        导出为 SRT 格式
        
        Args:
            editor: 字幕编辑器
            track_id: 轨道ID（None表示所有轨道）
            
        Returns:
            SRT格式字符串
        """
        lines = []
        counter = 1
        
        tracks = editor.tracks
        if track_id:
            track = editor.get_track(track_id)
            if track:
                tracks = [track]
        
        for track in tracks:
            if not track.enabled:
                continue
                
            for block in sorted(track.blocks, key=lambda b: b.start_time):
                start = SubtitleExporter._format_srt_time(block.start_time)
                end = SubtitleExporter._format_srt_time(block.end_time)
                
                lines.append(f"{counter}")
                lines.append(f"{start} --> {end}")
                lines.append(block.text)
                lines.append("")
                counter += 1
        
        return "\n".join(lines)
    
    @staticmethod
    def _format_srt_time(seconds: float) -> str:
        """格式化SRT时间（HH:MM:SS,mmm）"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    @staticmethod
    def to_vtt(editor: MultiTrackSubtitleEditor, track_id: str = None) -> str:
        """
        导出为 VTT 格式
        
        Args:
            editor: 字幕编辑器
            track_id: 轨道ID
            
        Returns:
            VTT格式字符串
        """
        lines = ["WEBVTT", ""]
        
        tracks = editor.tracks
        if track_id:
            track = editor.get_track(track_id)
            if track:
                tracks = [track]
        
        for track in tracks:
            if not track.enabled:
                continue
                
            for block in sorted(track.blocks, key=lambda b: b.start_time):
                start = SubtitleExporter._format_vtt_time(block.start_time)
                end = SubtitleExporter._format_vtt_time(block.end_time)
                
                lines.append(f"{start} --> {end}")
                lines.append(block.text)
                lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def _format_vtt_time(seconds: float) -> str:
        """格式化VTT时间（HH:MM:SS.mmm）"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
    
    @staticmethod
    def to_ass(editor: MultiTrackSubtitleEditor, track_id: str = None) -> str:
        """
        导出为 ASS 格式
        
        Args:
            editor: 字幕编辑器
            track_id: 轨道ID
            
        Returns:
            ASS格式字符串
        """
        lines = [
            "[Script Info]",
            "ScriptType: v4.00+",
            "Collisions: Normal",
            "PlayDepth: 0",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
            "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
            "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            "Alignment, MarginL, MarginR, MarginV, Encoding",
        ]
        
        # 添加样式
        style = editor.presets.get("cinematic", DEFAULT_PRESETS["cinematic"])
        lines.append(f"Style: Default,{style.font_family},{int(style.font_size * 10)},"
                    f"&H00{style.font_color[1:]},&H0000FFFF,&H00{style.font_color[1:]},"
                    f"&H00000000,0,0,0,0,100,100,0,0,1,2,2,2,10,10,10,1")
        lines.append("")
        lines.append("[Events]")
        lines.append("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text")
        
        tracks = editor.tracks
        if track_id:
            track = editor.get_track(track_id)
            if track:
                tracks = [track]
        
        for track in tracks:
            if not track.enabled:
                continue
                
            for block in sorted(track.blocks, key=lambda b: b.start_time):
                start = SubtitleExporter._format_ass_time(block.start_time)
                end = SubtitleExporter._format_ass_time(block.end_time)
                text = block.text.replace("\n", "\\N")
                lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")
        
        return "\n".join(lines)
    
    @staticmethod
    def _format_ass_time(seconds: float) -> str:
        """格式化ASS时间（H:MM:SS.cc）"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}:{minutes:02d}:{secs:05.2f}"
    
    @staticmethod
    def to_json(editor: MultiTrackSubtitleEditor, indent: int = 2) -> str:
        """
        导出为 JSON 格式
        
        Args:
            editor: 字幕编辑器
            indent: 缩进
            
        Returns:
            JSON格式字符串
        """
        return json.dumps(editor.to_dict(), ensure_ascii=False, indent=indent)
    
    @staticmethod
    def to_jianying(editor: MultiTrackSubtitleEditor, track_id: str = None) -> List[Dict]:
        """
        导出为剪映字幕格式
        
        Args:
            editor: 字幕编辑器
            track_id: 轨道ID
            
        Returns:
            剪映字幕段列表
        """
        from .subsubtitles import export_to_jianying_text_track
        
        tracks = editor.tracks
        if track_id:
            track = editor.get_track(track_id)
            if track:
                tracks = [track]
        
        all_segments = []
        for track in tracks:
            if track.enabled:
                segments = export_to_jianying_text_track(editor, track)
                all_segments.extend(segments)
        
        return all_segments
    
    @staticmethod
    def export_to_file(
        editor: MultiTrackSubtitleEditor,
        output_path: str,
        format: str = "json",
        track_id: str = None,
    ) -> None:
        """
        导出到文件
        
        Args:
            editor: 字幕编辑器
            output_path: 输出文件路径
            format: 格式（srt, vtt, ass, json）
            track_id: 轨道ID
        """
        path = Path(output_path)
        
        if format.lower() == "srt":
            content = SubtitleExporter.to_srt(editor, track_id)
        elif format.lower() == "vtt":
            content = SubtitleExporter.to_vtt(editor, track_id)
        elif format.lower() == "ass":
            content = SubtitleExporter.to_ass(editor, track_id)
        else:
            content = SubtitleExporter.to_json(editor, indent=2)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)


# ─────────────────────────────────────────────────────────────
# 字幕导入器
# ─────────────────────────────────────────────────────────────

class SubtitleImporter:
    """
    字幕导入器
    
    从各种格式导入字幕到多轨道字幕编辑器。
    """
    
    @classmethod
    def from_srt(cls, content: str, track_name: str = "导入字幕") -> SubtitleTrack:
        """
        从 SRT 格式导入
        
        Args:
            content: SRT内容
            track_name: 轨道名称
            
        Returns:
            字幕轨道
        """
        track = SubtitleTrack(name=track_name, style_id="cinematic")
        
        # 解析SRT
        pattern = re.compile(
            r'(\d+)\s*\r?\n'
            r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})\s*\r?\n'
            r'([\s\S]*?)(?=\r?\n\r?\n|\Z)',
            re.MULTILINE
        )
        
        for match in pattern.finditer(content):
            text = match.group(4).strip()
            if not text:
                continue
            
            start = cls._parse_srt_time(match.group(2))
            end = cls._parse_srt_time(match.group(3))
            
            block = SubtitleBlock(
                text=text,
                start_time=start,
                end_time=end,
            )
            track.add_block(block)
        
        return track
    
    @classmethod
    def _parse_srt_time(cls, time_str: str) -> float:
        """解析SRT时间"""
        parts = time_str.replace(',', ':').split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    
    @classmethod
    def from_vtt(cls, content: str, track_name: str = "导入字幕") -> SubtitleTrack:
        """
        从 VTT 格式导入
        
        Args:
            content: VTT内容
            track_name: 轨道名称
            
        Returns:
            字幕轨道
        """
        track = SubtitleTrack(name=track_name, style_id="cinematic")
        
        # 移除WEBVTT头
        content = re.sub(r'^WEBVTT.*?\n\n', '', content, flags=re.MULTILINE)
        
        # 解析VTT
        pattern = re.compile(
            r'(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})\s*\r?\n'
            r'([\s\S]*?)(?=\r?\n\r?\n|\Z)',
            re.MULTILINE
        )
        
        for match in pattern.finditer(content):
            text = match.group(3).strip()
            if not text:
                continue
            
            start = cls._parse_vtt_time(match.group(1))
            end = cls._parse_vtt_time(match.group(2))
            
            block = SubtitleBlock(
                text=text,
                start_time=start,
                end_time=end,
            )
            track.add_block(block)
        
        return track
    
    @classmethod
    def _parse_vtt_time(cls, time_str: str) -> float:
        """解析VTT时间"""
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    
    @classmethod
    def from_ass(cls, content: str, track_name: str = "导入字幕") -> SubtitleTrack:
        """
        从 ASS 格式导入
        
        Args:
            content: ASS内容
            track_name: 轨道名称
            
        Returns:
            字幕轨道
        """
        track = SubtitleTrack(name=track_name, style_id="cinematic")
        
        # 解析Dialogue行
        pattern = re.compile(
            r'Dialogue:\s*\d+,(\d+:\d{2}:\d{2}\.\d{2}),(\d+:\d{2}:\d{2}\.\d{2}),.*?,,.*?(?:\d+,)*(\d+),(\d+),(\d+),,([\s\S]*?)(?:\r?\n|$)',
            re.MULTILINE
        )
        
        for match in pattern.finditer(content):
            text = match.group(7).strip()
            if not text:
                continue
            
            text = text.replace('\\N', '\n').replace('\\n', '\n')
            
            start = cls._parse_ass_time(match.group(1))
            end = cls._parse_ass_time(match.group(2))
            
            block = SubtitleBlock(
                text=text,
                start_time=start,
                end_time=end,
            )
            track.add_block(block)
        
        return track
    
    @classmethod
    def _parse_ass_time(cls, time_str: str) -> float:
        """解析ASS时间"""
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    
    @classmethod
    def from_json(cls, content: str) -> MultiTrackSubtitleEditor:
        """
        从 JSON 格式导入
        
        Args:
            content: JSON内容
            
        Returns:
            多轨道字幕编辑器
        """
        data = json.loads(content)
        return MultiTrackSubtitleEditor.from_dict(data)
    
    @classmethod
    def from_file(cls, file_path: str) -> MultiTrackSubtitleEditor:
        """
        从文件导入
        
        Args:
            file_path: 文件路径
            
        Returns:
            多轨道字幕编辑器或字幕轨道
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        suffix = path.suffix.lower()
        
        if suffix == '.srt':
            track = cls.from_srt(content, track_name=path.stem)
            return track
        elif suffix == '.vtt':
            track = cls.from_vtt(content, track_name=path.stem)
            return track
        elif suffix == '.ass':
            track = cls.from_ass(content, track_name=path.stem)
            return track
        elif suffix == '.json':
            return cls.from_json(content)
        else:
            # 尝试作为JSON处理
            try:
                return cls.from_json(content)
            except json.JSONDecodeError:
                raise ValueError(f"不支持的文件格式: {suffix}")
    
    @classmethod
    def import_to_editor(
        cls,
        file_path: str,
        editor: MultiTrackSubtitleEditor = None,
        track_name: str = None,
    ) -> MultiTrackSubtitleEditor:
        """
        导入到编辑器
        
        Args:
            file_path: 文件路径
            editor: 目标编辑器（None则创建新的）
            track_name: 轨道名称
            
        Returns:
            多轨道字幕编辑器
        """
        if editor is None:
            editor = MultiTrackSubtitleEditor()
        
        track = cls.from_file(file_path)
        
        if isinstance(track, SubtitleTrack):
            if track_name:
                track.name = track_name
            editor.add_track(track)
        else:
            # 合并轨道
            for t in track.tracks:
                editor.add_track(t)
        
        return editor


__all__ = [
    "SubtitleExporter",
    "SubtitleImporter",
]
