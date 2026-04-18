"""
视频制作器基类 (Base Video Maker)

为所有视频制作器提供公共抽象。
当前活跃实现:
- MonologueMaker: AI 第一人称独白（核心）
"""

import uuid
from pathlib import Path
from typing import Optional, List, Dict, Callable, TypeVar, Generic
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..ai.scene_analyzer import SceneAnalyzer, SceneInfo
from ..export.jianying_exporter import JianyingExporter
from ..export.jianying_models import (
    JianyingDraft, JianyingConfig,
    Track, TrackType, Segment, TimeRange,
    VideoMaterial, AudioMaterial, TextMaterial,
)


@dataclass
class BaseProject:
    """项目基类"""
    id: str = ""
    name: str = "新建项目"
    source_video: str = ""
    video_duration: float = 0.0
    output_dir: str = ""
    scenes: List[SceneInfo] = field(default_factory=list)


T = TypeVar("T", bound=BaseProject)


class ProgressMixin:
    """进度回调 Mixin"""

    def __init__(self):
        self._progress_callback: Optional[Callable[[str, float], None]] = None

    def set_progress_callback(self, callback: Callable[[str, float], None]) -> None:
        """设置进度回调"""
        self._progress_callback = callback

    def _report_progress(self, stage: str, progress: float) -> None:
        """报告进度"""
        if self._progress_callback:
            self._progress_callback(stage, progress)


class BaseVideoMaker(ABC, Generic[T], ProgressMixin):
    """
    视频制作器基类

    提供公共功能:
    - 进度报告
    - 视频分析
    - 剪映导出
    - FFmpeg 导出
    """

    def __init__(self):
        super().__init__()
        self.scene_analyzer = SceneAnalyzer()
        self.jianying_exporter = JianyingExporter()

    @abstractmethod
    def create_project(
        self,
        source_video: str,
        name: Optional[str] = None,
        output_dir: Optional[str] = None,
        **kwargs,
    ) -> T:
        """创建项目（子类实现）"""
        pass

    def _init_project(
        self,
        project: T,
        source_video: str,
        name: Optional[str] = None,
        output_dir: Optional[str] = None,
    ) -> T:
        """初始化项目公共属性"""
        source_path = Path(source_video)
        if not source_path.exists():
            raise FileNotFoundError(f"视频文件不存在: {source_video}")

        project.id = str(uuid.uuid4())[:8]
        project.name = name or source_path.stem
        project.source_video = str(source_path.absolute())
        project.output_dir = output_dir or str(source_path.parent / "output")

        # 分析场景
        project.scenes = self.scene_analyzer.analyze(source_video)
        project.video_duration = sum(s.duration for s in project.scenes) if project.scenes else 0

        return project

    def export_to_jianying(
        self,
        project: T,
        jianying_drafts_dir: str,
    ) -> str:
        """
        导出到剪映草稿（基类实现）

        子类可重写以自定义导出逻辑
        """
        self._report_progress("导出剪映", 0.0)

        exporter = JianyingExporter(JianyingConfig(
            canvas_ratio="9:16",
            copy_materials=True,
        ))

        self._report_progress("构建轨道", 0.0)
        draft = exporter.create_draft(project.name)

        # 子类可重写此方法来添加自定义轨道
        self._build_jianying_tracks(draft, project)
        self._report_progress("构建轨道", 1.0)

        def _on_exporter_progress(phase: str, phase_p: float):
            # 将导出器的子阶段映射到 0.5-1.0
            overall_p = 0.5 + phase_p * 0.5
            self._report_progress(f"导出: {phase}", overall_p)

        draft_path = exporter.export(draft, jianying_drafts_dir, progress_callback=_on_exporter_progress)
        self._report_progress("导出剪映", 1.0)

        return draft_path

    def _build_jianying_tracks(self, draft: JianyingDraft, project: T) -> None:
        """
        构建剪映轨道

        子类重写此方法实现自定义轨道
        """
        pass

    def _create_video_track(
        self,
        draft: JianyingDraft,
        source_video: str,
        duration: float,
        segments_data: Optional[List[Dict]] = None,
    ) -> Track:
        """创建视频轨道"""
        video_track = Track(type=TrackType.VIDEO, attribute=1)
        draft.add_track(video_track)

        video_material = VideoMaterial(
            path=source_video,
            duration=int(duration * 1_000_000),
        )
        draft.add_video(video_material)

        if segments_data:
            for seg in segments_data:
                segment = Segment(
                    material_id=video_material.id,
                    source_timerange=TimeRange.from_seconds(
                        seg.get("source_start", 0),
                        seg.get("duration", 0),
                    ),
                    target_timerange=TimeRange.from_seconds(
                        seg.get("target_start", 0),
                        seg.get("duration", 0),
                    ),
                )
                video_track.add_segment(segment)

        return video_track

    def _create_audio_track(
        self,
        draft: JianyingDraft,
        audio_path: str,
        duration: float,
        segments_data: Optional[List[Dict]] = None,
    ) -> Track:
        """创建音频轨道"""
        audio_track = Track(type=TrackType.AUDIO)
        draft.add_track(audio_track)

        audio_material = AudioMaterial(
            path=audio_path,
            duration=int(duration * 1_000_000),
            name=Path(audio_path).stem,
        )
        draft.add_audio(audio_material)

        if segments_data:
            for seg in segments_data:
                segment = Segment(
                    material_id=audio_material.id,
                    source_timerange=TimeRange.from_seconds(
                        seg.get("source_start", 0),
                        seg.get("duration", 0),
                    ),
                    target_timerange=TimeRange.from_seconds(
                        seg.get("target_start", 0),
                        seg.get("duration", 0),
                    ),
                )
                audio_track.add_segment(segment)

        return audio_track

    def _create_text_track(
        self,
        draft: JianyingDraft,
        captions: List[Dict],
        caption_style: Optional[Dict] = None,
    ) -> Track:
        """创建字幕轨道"""
        text_track = Track(type=TrackType.TEXT)
        draft.add_track(text_track)

        default_style = caption_style or {
            "font_size": 6.0,
            "font_color": "#FFFFFF",
            "has_shadow": True,
        }

        for cap in captions:
            text_material = TextMaterial(
                content=cap.get("text", ""),
                font_size=cap.get("font_size", default_style.get("font_size", 6.0)),
                font_color=cap.get("font_color", default_style.get("font_color", "#FFFFFF")),
                has_shadow=cap.get("has_shadow", default_style.get("has_shadow", True)),
            )
            draft.add_text(text_material)

            text_segment = Segment(
                material_id=text_material.id,
                source_timerange=TimeRange.from_seconds(0, cap.get("duration", 0)),
                target_timerange=TimeRange.from_seconds(
                    cap.get("start", 0),
                    cap.get("duration", 0),
                ),
            )
            text_track.add_segment(text_segment)

        return text_track


# =========== 便捷函数 ===========

def merge_audio_files(
    audio_paths: List[str],
    output_path: str,
) -> str:
    """合并多个音频文件"""
    import subprocess

    if not audio_paths:
        raise ValueError("没有可用的音频文件")

    # 如果只有一个文件，直接返回
    if len(audio_paths) == 1:
        return audio_paths[0]

    # 创建临时列表文件
    concat_list = Path(output_path).parent / "audio_concat.txt"
    with open(concat_list, 'w') as f:
        for audio in audio_paths:
            f.write(f"file '{audio}'\n")

    # 合并音频
    cmd = [
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
        '-i', str(concat_list),
        '-c', 'copy', output_path
    ]
    subprocess.run(cmd, capture_output=True)

    return output_path


def composite_video_with_audio(
    video_path: str,
    audio_path: str,
    output_path: str,
) -> str:
    """使用 FFmpeg 合成视频和音频"""
    import subprocess

    cmd = [
        'ffmpeg', '-y',
        '-i', video_path,
        '-i', audio_path,
        '-c:v', 'libx264', '-preset', 'medium',
        '-c:a', 'aac',
        '-map', '0:v:0', '-map', '1:a:0',
        '-shortest',
        output_path
    ]
    subprocess.run(cmd, capture_output=True)

    return output_path


__all__ = [
    "BaseProject",
    "BaseVideoMaker",
    "ProgressMixin",
    "merge_audio_files",
    "composite_video_with_audio",
]
