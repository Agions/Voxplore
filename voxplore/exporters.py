#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Voxplore 导出服务
支持剪映草稿、字幕等格式导出
"""
import os
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
from dataclasses import dataclass

# orjson 性能比标准 json 快 5-10 倍
try:
    import orjson
    _json_dumps = lambda obj: orjson.dumps(obj, option=orjson.OPT_INDENT_2).decode()
    _use_orjson = True
except ImportError:
    import json
    _json_dumps = lambda obj: json.dumps(obj, ensure_ascii=False, indent=2)
    _use_orjson = False

logger = logging.getLogger(__name__)


@dataclass
class ExportConfig:
    """导出配置"""
    resolution: str = "1920x1080"  # 1920x1080, 1080x1920, 1080x1080
    fps: int = 30
    video_codec: str = "h264"
    audio_codec: str = "aac"
    quality: int = 23  # CRF 值，越低越好


class JianyingExporter:
    """
    剪映草稿导出器
    
    剪映草稿格式说明：
    - 每个草稿是一个文件夹
    - 核心文件：draft_content.json
    - 素材放在 materials/ 目录下
    """
    
    DRAFT_TEMPLATE = {
        "draft_name": "Voxplore Export",
        "draft_id": "",
        "category": 0,
        "resolution": {
            "width": 1920,
            "height": 1080
        },
        "fps": 30,
        "duration": 0,
        "materials": {
            "videos": [],
            "images": [],
            "audios": [],
            "effects": [],
            "stickers": [],
            "texts": []
        },
        "tracks": [],
        "timeline": {}
    }
    
    def __init__(self, config: ExportConfig = None):
        self.config = config or ExportConfig()
        self._parse_resolution()
    
    def _parse_resolution(self):
        """解析分辨率"""
        if self.config.resolution == "1920x1080":
            self.width, self.height = 1920, 1080
        elif self.config.resolution == "1080x1920":  # 竖屏 9:16
            self.width, self.height = 1080, 1920
        elif self.config.resolution == "1080x1080":  # 方屏 1:1
            self.width, self.height = 1080, 1080
        else:
            self.width, self.height = 1920, 1080
    
    def export(
        self,
        project: Any,
        output_dir: str,
        draft_name: str = None
    ) -> str:
        """
        导出剪映草稿（优化版）
        
        Args:
            project: VideoProject 对象
            output_dir: 输出目录
            draft_name: 草稿名称
            
        Returns:
            草稿文件夹路径
        """
        if draft_name is None:
            draft_name = project.name or "Voxplore_Export"
        
        # 创建草稿文件夹
        draft_dir = os.path.join(output_dir, draft_name)
        os.makedirs(draft_dir, exist_ok=True)
        
        # 创建素材目录
        materials_dir = os.path.join(draft_dir, "materials")
        for subdir in ["videos", "images", "audios", "effects", "stickers", "texts"]:
            os.makedirs(os.path.join(materials_dir, subdir), exist_ok=True)
        
        # 构建草稿内容
        draft_content = self._build_draft_content(project)
        
        # 写入草稿文件
        draft_file = os.path.join(draft_dir, "draft_content.json")
        with open(draft_file, 'w', encoding='utf-8') as f:
            f.write(_json_dumps(draft_content))
        
        # 并行复制素材文件
        self._copy_materials_parallel(project, materials_dir, draft_content)
        
        logger.info(f"Exported Jianying draft to: {draft_dir}")
        
        return draft_dir
    
    def _copy_materials_parallel(self, project: Any, materials_dir: str, draft_content: Dict):
        """并行复制素材文件"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import shutil
        
        copy_tasks = []
        
        # 收集需要复制的文件
        for i, seg in enumerate(project.segments):
            if os.path.exists(seg.video_path):
                video_name = f"video_{i:03d}.mp4"
                dst = os.path.join(materials_dir, "videos", video_name)
                copy_tasks.append((seg.video_path, dst))
        
        if project.audio_track and os.path.exists(project.audio_track.audio_path):
            audio_name = os.path.basename(project.audio_track.audio_path)
            dst = os.path.join(materials_dir, "audios", audio_name)
            copy_tasks.append((project.audio_track.audio_path, dst))
        
        # 并行复制
        if copy_tasks:
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {executor.submit(shutil.copy, src, dst): (src, dst) 
                          for src, dst in copy_tasks}
                
                for future in as_completed(futures):
                    src, dst = futures[future]
                    try:
                        future.result()
                    except Exception as e:
                        logger.warning(f"Failed to copy {src}: {e}")
    
    def _build_draft_content(self, project: Any) -> Dict[str, Any]:
        """构建剪映草稿内容"""
        import uuid
        from datetime import datetime
        
        draft = self.DRAFT_TEMPLATE.copy()
        draft["draft_name"] = project.name or "Voxplore Export"
        draft["draft_id"] = str(uuid.uuid4()).upper()
        draft["resolution"] = {"width": self.width, "height": self.height}
        draft["fps"] = self.config.fps
        
        # 计算总时长
        total_duration = 0
        if project.audio_track:
            total_duration = max(total_duration, project.audio_track.duration)
        if project.narration_blocks:
            total_duration = max(total_duration, project.narration_blocks[-1].end_time)
        
        draft["duration"] = int(total_duration * 1000)  # 毫秒
        
        # 添加视频素材
        for i, seg in enumerate(project.segments):
            video_id = str(uuid.uuid4()).upper()
            video_name = f"video_{i:03d}.mp4"
            
            # 复制视频文件
            if os.path.exists(seg.video_path):
                src = seg.video_path
                dst = os.path.join(draft["draft_id"] + "_materials", "videos", video_name)
                dst_abs = os.path.join(os.path.dirname(os.path.dirname(draft.get("draft_path", ""))), dst)
                try:
                    import shutil
                    os.makedirs(os.path.dirname(dst_abs), exist_ok=True)
                    shutil.copy(src, dst_abs)
                except Exception as e:
                    logger.warning(f"Failed to copy video: {e}")
            
            draft["materials"]["videos"].append({
                "id": video_id,
                "name": video_name,
                "path": f"##_draftpath_placeholder_##/materials/videos/{video_name}",
                "duration": int((seg.end_time - seg.start_time) * 1000),
                "width": self.width,
                "height": self.height
            })
        
        # 添加音频素材
        if project.audio_track and os.path.exists(project.audio_track.audio_path):
            audio_id = str(uuid.uuid4()).upper()
            audio_name = os.path.basename(project.audio_track.audio_path)
            
            draft["materials"]["audios"].append({
                "id": audio_id,
                "name": audio_name,
                "path": f"##_draftpath_placeholder_##/materials/audios/{audio_name}",
                "duration": int(project.audio_track.duration * 1000)
            })
        
        # 构建时间线轨道
        draft["tracks"] = self._build_tracks(project)
        
        return draft
    
    def _build_tracks(self, project: Any) -> List[Dict[str, Any]]:
        """构建时间线轨道"""
        tracks = []
        
        # 视频轨道
        video_track = {
            "id": str(uuid.uuid4()).upper(),
            "type": "video",
            "name": "主视频",
            "segments": []
        }
        
        current_time = 0
        for seg in project.segments:
            duration_ms = int((seg.end_time - seg.start_time) * 1000)
            
            video_track["segments"].append({
                "id": str(uuid.uuid4()).upper(),
                "material_id": "",  # 应该在 materials 中查找
                "start_time": current_time,
                "duration": duration_ms,
                "source_start": int(seg.start_time * 1000),
                "source_end": int(seg.end_time * 1000),
                "effects": []
            })
            
            current_time += duration_ms
        
        if video_track["segments"]:
            tracks.append(video_track)
        
        # 音频轨道
        if project.audio_track:
            audio_track = {
                "id": str(uuid.uuid4()).upper(),
                "type": "audio",
                "name": "配音",
                "segments": [{
                    "id": str(uuid.uuid4()).upper(),
                    "material_id": "",
                    "start_time": 0,
                    "duration": int(project.audio_track.duration * 1000),
                    "volume": 1.0
                }]
            }
            tracks.append(audio_track)
        
        # 字幕轨道
        if project.subtitles:
            subtitle_track = {
                "id": str(uuid.uuid4()).upper(),
                "type": "text",
                "name": "字幕",
                "segments": []
            }
            
            for sub in project.subtitles:
                subtitle_track["segments"].append({
                    "id": str(uuid.uuid4()).upper(),
                    "start_time": int(sub.start_time * 1000),
                    "duration": int(sub.duration * 1000),
                    "text": sub.text,
                    "style": {
                        "font_size": 24,
                        "color": "#FFFFFF",
                        "stroke_color": "#000000",
                        "stroke_width": 1
                    }
                })
            
            tracks.append(subtitle_track)
        
        return tracks


class SubtitleExporter:
    """
    字幕导出器
    支持 SRT、VTT、LRC 等格式
    """
    
    @staticmethod
    def export_srt(
        subtitles: List[Any],
        output_path: str
    ) -> bool:
        """
        导出 SRT 格式字幕
        
        Args:
            subtitles: SubtitleItem 列表
            output_path: 输出文件路径
            
        Returns:
            是否成功
        """
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
    def export_vtt(
        subtitles: List[Any],
        output_path: str
    ) -> bool:
        """导出 VTT 格式字幕"""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("WEBVTT\n\n")
                for i, sub in enumerate(subtitles, 1):
                    start = SubtitleExporter._format_vtt_time(sub.start_time)
                    end = SubtitleExporter._format_vtt_time(sub.end_time)
                    f.write(f"{i}\n")
                    f.write(f"{start} --> {end}\n")
                    f.write(f"{sub.text}\n\n")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to export VTT: {e}")
            return False
    
    @staticmethod
    def export_lrc(
        subtitles: List[Any],
        output_path: str
    ) -> bool:
        """导出 LRC 格式歌词"""
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
        """格式化 VTT 时间"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


class VideoExporter:
    """
    视频导出器
    使用 FFmpeg 导出最终视频
    """
    
    def __init__(self, config: ExportConfig = None):
        self.config = config or ExportConfig()
    
    def export(
        self,
        project: Any,
        output_path: str,
        include_audio: bool = True,
        include_subtitles: bool = False
    ) -> bool:
        """
        导出视频
        
        Args:
            project: VideoProject 对象
            output_path: 输出文件路径
            include_audio: 是否包含配音
            include_subtitles: 是否包含字幕
            
        Returns:
            是否成功
        """
        if not project.segments:
            logger.error("No segments to export")
            return False
        
        try:
            import subprocess
            import tempfile
            
            # 创建临时文件列表
            list_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
            
            for seg in project.segments:
                if os.path.exists(seg.video_path):
                    # 计算片段在源视频中的位置
                    start = seg.start_time
                    duration = seg.end_time - seg.start_time
                    list_file.write(f"file '{seg.video_path}'\n")
                    list_file.write(f"inpoint {start}\n")
                    list_file.write(f"outpoint {seg.end_time}\n")
            
            list_file.close()
            
            # 构建 FFmpeg 命令
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", list_file.name,
                "-c:v", "libx264", "-crf", str(self.config.quality),
                "-preset", "medium",
                "-vf", f"scale={self.width}:{self.height}",
                "-r", str(self.config.fps),
                "-c:a", self.config.audio_codec,
                "-ar", "44100", "-ac", "2"
            ]
            
            # 添加配音
            if include_audio and project.audio_track and os.path.exists(project.audio_track.audio_path):
                cmd.extend(["-i", project.audio_track.audio_path])
            
            # 添加字幕
            if include_subtitles and project.subtitles:
                subtitle_file = output_path + ".srt"
                SubtitleExporter.export_srt(project.subtitles, subtitle_file)
                cmd.extend([
                    "-vf", f"subtitles={subtitle_file}"
                ])
            
            cmd.append(output_path)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            os.unlink(list_file.name)
            
            if result.returncode == 0:
                logger.info(f"Video exported to: {output_path}")
                return True
            else:
                logger.error(f"Export failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Export timed out")
            return False
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False
    
    @property
    def width(self) -> int:
        return self.config.resolution.split('x')[0]
    
    @property
    def height(self) -> int:
        return self.config.resolution.split('x')[1]


__all__ = [
    "ExportConfig",
    "JianyingExporter",
    "SubtitleExporter",
    "VideoExporter",
]
