#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
剪映草稿导出器 (Jianying Exporter)

将 Voxplore 项目导出为剪映草稿格式，实现与剪映的完美对接。

剪映草稿结构:
    drafts/
    └── {project_name}/
        ├── draft_content.json     # 主要内容
        ├── draft_meta_info.json   # 元信息
        └── 素材文件...

使用示例:
    from app.services.export import JianyingExporter

    exporter = JianyingExporter()
    draft_path = exporter.export(project, output_dir)
    logger.info(f"草稿已导出: {draft_path}")

数据模型已拆分到 jianying_models.py，导出器保持单一职责。
"""

import logging
import json
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Tuple

from ..video_tools.ffmpeg_tool import FFmpegTool
from .jianying_models import (
    TrackType,
    MaterialType,  # noqa: F401  # intentionally re-exported for tests
    TimeRange,
    Track,
    Segment,
    VideoMaterial,
    AudioMaterial,
    TextMaterial,
    JianyingDraft,
    JianyingConfig,
    CanvasConfig,
)


logger = logging.getLogger(__name__)


class JianyingExporter:
    """
    剪映草稿导出器

    将项目导出为剪映可识别的草稿格式

    使用示例:
        exporter = JianyingExporter()

        # 创建草稿
        draft = exporter.create_draft("我的视频")

        # 添加视频轨道
        video_track = Track(type=TrackType.VIDEO)
        video_material = VideoMaterial(path="/path/to/video.mp4", duration=5000000)
        draft.add_video(video_material)

        video_segment = Segment(
            material_id=video_material.id,
            target_timerange=TimeRange.from_seconds(0, 5),
            source_timerange=TimeRange.from_seconds(0, 5),
        )
        video_track.add_segment(video_segment)
        draft.add_track(video_track)

        # 导出
        draft_path = exporter.export(draft, "/path/to/output")
    """

    def __init__(self, config: Optional[JianyingConfig] = None):
        self.config = config or JianyingConfig()

    def create_draft(self, name: str) -> JianyingDraft:
        """创建新草稿"""
        canvas_config = self._get_canvas_config(self.config.canvas_ratio)

        return JianyingDraft(
            name=name,
            canvas_config=canvas_config,
            version=self.config.version,
        )

    def _get_canvas_config(self, ratio: str) -> CanvasConfig:
        """根据比例获取画布配置"""
        configs = {
            "9:16": CanvasConfig(width=1080, height=1920, ratio="9:16"),  # 竖屏
            "16:9": CanvasConfig(width=1920, height=1080, ratio="16:9"),  # 横屏
            "1:1": CanvasConfig(width=1080, height=1080, ratio="1:1"),    # 方形
            "3:4": CanvasConfig(width=1080, height=1440, ratio="3:4"),    # 小红书
        }
        return configs.get(ratio, configs["9:16"])

    def export(
        self,
        draft: JianyingDraft,
        output_dir: str,
        progress_callback=None,
    ) -> str:
        """
        导出草稿到指定目录

        Args:
            draft: 剪映草稿对象
            output_dir: 输出目录（剪映草稿目录）
            progress_callback: 进度回调 fn(phase: str, progress: float)

        Returns:
            草稿文件夹路径
        """
        def _report(phase: str, p: float):
            if progress_callback:
                progress_callback(phase, p)

        output_path = Path(output_dir)

        # 创建草稿文件夹（使用项目名称）
        safe_name = self._safe_filename(draft.name)
        draft_folder = output_path / safe_name
        draft_folder.mkdir(parents=True, exist_ok=True)

        # 复制素材（如果启用）
        if self.config.copy_materials:
            _report("复制素材", 0.0)
            self._copy_materials(draft, draft_folder)
            _report("复制素材", 1.0)

        # 生成 draft_content.json
        _report("生成草稿配置", 0.0)
        content = draft.to_draft_content()
        content_path = draft_folder / "draft_content.json"
        self._write_json(content_path, content)
        _report("生成草稿配置", 1.0)

        # 生成 draft_meta_info.json
        _report("写入元信息", 0.0)
        meta = draft.to_draft_meta_info()
        meta["draft_root_path"] = str(draft_folder)
        meta_path = draft_folder / "draft_meta_info.json"
        self._write_json(meta_path, meta)
        _report("写入元信息", 1.0)

        return str(draft_folder)

    def _safe_filename(self, name: str) -> str:
        """生成安全的文件名"""
        # 移除或替换不安全字符
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        return name.strip()

    def _copy_materials(self, draft: JianyingDraft, draft_folder: Path) -> None:
        """复制素材到草稿目录（并行化以提升大文件性能）"""
        materials_folder = draft_folder / "materials"
        materials_folder.mkdir(exist_ok=True)

        from concurrent.futures import ThreadPoolExecutor, as_completed

        def _copy_single(src_path: str, materials_folder: Path) -> Optional[str]:
            """复制单个素材，返回新路径"""
            src = Path(src_path)
            if not src.exists():
                return None
            dst = materials_folder / src.name
            if not dst.exists():
                shutil.copy2(src, dst)
            return str(dst)

        # 收集所有待复制的素材
        tasks: List[Tuple[str, str]] = []  # [(src_path, type), ...]

        for video in draft.materials.videos:
            if video.path:
                tasks.append((video.path, "video"))

        for audio in draft.materials.audios:
            if audio.path:
                tasks.append((audio.path, "audio"))

        # 并行复制所有素材
        if tasks:
            results: Dict[str, str] = {}
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {
                    executor.submit(_copy_single, src, materials_folder): src
                    for src, _ in tasks
                }
                for future in as_completed(futures):
                    src = futures[future]
                    try:
                        new_path = future.result()
                        if new_path:
                            results[src] = new_path
                    except Exception as e:
                        logger.warning(f"素材复制失败 {src}: {e}")

            # 更新路径为相对路径
            for video in draft.materials.videos:
                if video.path and video.path in results:
                    video.path = results[video.path]

            for audio in draft.materials.audios:
                if audio.path and audio.path in results:
                    audio.path = results[audio.path]

    def _write_json(self, path: Path, data: dict) -> None:
        """写入 JSON 文件"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # =========== 便捷方法 ===========

    def add_video_segment(
        self,
        draft: JianyingDraft,
        video_path: str,
        start: float,
        duration: float,
        target_start: float = None,
    ) -> Segment:
        """
        便捷方法：添加视频片段

        Args:
            draft: 草稿对象
            video_path: 视频文件路径
            start: 源视频开始时间（秒）
            duration: 持续时间（秒）
            target_start: 目标时间轴开始位置（秒），默认为自动计算

        Returns:
            创建的片段对象
        """
        # 获取视频信息
        video_info = self._get_video_info(video_path)

        # 创建素材
        material = VideoMaterial(
            path=video_path,
            duration=video_info.get('duration', int(duration * 1_000_000)),
            width=video_info.get('width', 1920),
            height=video_info.get('height', 1080),
        )
        draft.add_video(material)

        # 计算目标开始时间
        if target_start is None:
            # 找到视频轨道的最后位置
            video_tracks = [t for t in draft.tracks if t.type == TrackType.VIDEO]
            if video_tracks:
                last_track = video_tracks[0]
                if last_track.segments:
                    last_seg = last_track.segments[-1]
                    target_start = (last_seg.target_timerange.start +
                                   last_seg.target_timerange.duration) / 1_000_000
                else:
                    target_start = 0
            else:
                # 创建新的视频轨道
                new_track = Track(type=TrackType.VIDEO, attribute=1)
                draft.add_track(new_track)
                target_start = 0

        # 创建片段
        segment = Segment(
            material_id=material.id,
            source_timerange=TimeRange.from_seconds(start, duration),
            target_timerange=TimeRange.from_seconds(target_start, duration),
        )

        # 添加到视频轨道
        video_tracks = [t for t in draft.tracks if t.type == TrackType.VIDEO]
        if video_tracks:
            video_tracks[0].add_segment(segment)

        return segment

    def add_audio_segment(
        self,
        draft: JianyingDraft,
        audio_path: str,
        start: float,
        duration: float,
        target_start: float = 0,
        volume: float = 1.0,
    ) -> Segment:
        """
        便捷方法：添加音频片段

        Args:
            draft: 草稿对象
            audio_path: 音频文件路径
            start: 源音频开始时间（秒）
            duration: 持续时间（秒）
            target_start: 目标时间轴开始位置（秒）
            volume: 音量（0.0 - 1.0）

        Returns:
            创建的片段对象
        """
        # 创建素材
        material = AudioMaterial(
            path=audio_path,
            duration=int(duration * 1_000_000),
            name=Path(audio_path).stem,
        )
        draft.add_audio(material)

        # 获取或创建音频轨道
        audio_tracks = [t for t in draft.tracks if t.type == TrackType.AUDIO]
        if not audio_tracks:
            audio_track = Track(type=TrackType.AUDIO)
            draft.add_track(audio_track)
            audio_tracks = [audio_track]

        # 创建片段
        segment = Segment(
            material_id=material.id,
            source_timerange=TimeRange.from_seconds(start, duration),
            target_timerange=TimeRange.from_seconds(target_start, duration),
            volume=volume,
        )

        audio_tracks[0].add_segment(segment)
        return segment

    def add_caption(
        self,
        draft: JianyingDraft,
        text: str,
        start: float,
        duration: float,
        font_size: float = 8.0,
        font_color: str = "#FFFFFF",
    ) -> Segment:
        """
        便捷方法：添加字幕

        Args:
            draft: 草稿对象
            text: 字幕文本
            start: 开始时间（秒）
            duration: 持续时间（秒）
            font_size: 字体大小（剪映相对尺寸，默认8.0）
            font_color: 字体颜色（十六进制）

        Returns:
            创建的片段对象
        """
        # 创建文本素材
        material = TextMaterial(
            content=text,
            font_size=font_size,
            font_color=font_color,
        )
        draft.add_text(material)

        # 获取或创建字幕轨道
        text_tracks = [t for t in draft.tracks if t.type == TrackType.TEXT]
        if not text_tracks:
            text_track = Track(type=TrackType.TEXT)
            draft.add_track(text_track)
            text_tracks = [text_track]

        # 创建片段
        segment = Segment(
            material_id=material.id,
            source_timerange=TimeRange.from_seconds(0, duration),
            target_timerange=TimeRange.from_seconds(start, duration),
            caption_info={
                "content": text,
                "font_size": font_size,
                "font_color": font_color,
            },
        )

        text_tracks[0].add_segment(segment)
        return segment

    def _get_video_info(self, video_path: str) -> dict:
        """
        获取视频信息

        使用 FFmpegTool 获取视频的时长、分辨率等信息
        """
        try:
            info = FFmpegTool.get_video_info(video_path)
            video_stream = next((s for s in info.get('streams', []) if s.get('codec_type') == 'video'), {})
            duration_str = info.get('format', {}).get('duration', '0')
            duration = float(duration_str) if duration_str else 0.0
            width = int(video_stream.get('width', 1920))
            height = int(video_stream.get('height', 1080))
            return {
                'width': width,
                'height': height,
                'duration': int(duration * 1_000_000),
            }
        except Exception as e:
            logger.error(f"获取视频信息失败: {e}")
            return {'width': 1920, 'height': 1080, 'duration': 0}


# =========== 使用示例 ===========

def demo_export():
    """导出示例"""

    exporter = JianyingExporter(JianyingConfig(
        canvas_ratio="9:16",  # 竖屏短视频
        copy_materials=True,
    ))

    # 创建草稿
    draft = exporter.create_draft("我的AI解说视频")

    # 添加视频片段
    exporter.add_video_segment(
        draft,
        video_path="/path/to/source.mp4",
        start=0,
        duration=10,
    )

    # 添加配音
    exporter.add_audio_segment(
        draft,
        audio_path="/path/to/voiceover.mp3",
        start=0,
        duration=10,
        volume=1.0,
    )

    # 添加字幕
    exporter.add_caption(
        draft,
        text="欢迎观看这个视频",
        start=0,
        duration=3,
        font_size=8.0,
        font_color="#FFFFFF",
    )

    exporter.add_caption(
        draft,
        text="这是AI自动解说生成的内容",
        start=3,
        duration=4,
    )

    # 导出到剪映草稿目录
    # macOS: ~/Movies/JianyingPro/User Data/Projects/com.lveditor.draft/drafts/
    output = exporter.export(draft, "/path/to/jianying/drafts")
    logger.info(f"草稿已导出: {output}")


if __name__ == '__main__':
    demo_export()
