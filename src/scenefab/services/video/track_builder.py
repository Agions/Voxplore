#!/usr/bin/env python3

"""
剪映轨道构建器

将项目数据转换为剪映草稿的轨道结构。
"""

from pathlib import Path

from scenefab.services.export.jianying_adapter import (
    AudioMaterial,
    JianyingDraft,
    Segment,
    TextMaterial,
    TimeRange,
    Track,
    TrackType,
    VideoMaterial,
)

# 字幕样式配置
CAPTION_STYLES = {
    "cinematic": {
        "font_size": 6.0,
        "font_color": "#FFFFFF",
        "position": "bottom",
        "shadow": True,
        "animation": "fade",
    },
    "minimal": {
        "font_size": 5.0,
        "font_color": "#E0E0E0",
        "position": "bottom",
        "shadow": False,
        "animation": "none",
    },
    "expressive": {
        "font_size": 7.0,
        "font_color": "#FFFFFF",
        "position": "center",
        "shadow": True,
        "animation": "typewriter",
    },
}


def _build_video_track(
    draft: JianyingDraft,
    source_video: str,
    video_duration: float,
    segments: list,
) -> None:
    """构建视频轨道并按片段切片。"""
    video_track = Track(type=TrackType.VIDEO, attribute=1)
    draft.add_track(video_track)

    video_material = VideoMaterial(
        path=source_video,
        duration=TimeRange.from_seconds(0, video_duration).duration,
    )
    draft.add_video(video_material)

    current_time = 0.0
    for segment in segments:
        video_segment = Segment(
            material_id=video_material.id,
            source_timerange=TimeRange.from_seconds(
                segment.video_start,
                min(segment.audio_duration, segment.video_end - segment.video_start),
            ),
            target_timerange=TimeRange.from_seconds(
                current_time, segment.audio_duration
            ),
        )
        video_track.add_segment(video_segment)
        current_time += segment.audio_duration


def _build_audio_track(
    draft: JianyingDraft,
    segments: list,
) -> None:
    """构建独白音频轨道。"""
    audio_track = Track(type=TrackType.AUDIO)
    draft.add_track(audio_track)

    current_time = 0.0
    for segment in segments:
        if segment.audio_path:
            audio_material = AudioMaterial(
                path=segment.audio_path,
                duration=TimeRange.from_seconds(0, segment.audio_duration).duration,
                name=Path(segment.audio_path).stem,
            )
            draft.add_audio(audio_material)

            audio_segment = Segment(
                material_id=audio_material.id,
                source_timerange=TimeRange.from_seconds(0, segment.audio_duration),
                target_timerange=TimeRange.from_seconds(
                    current_time, segment.audio_duration
                ),
            )
            audio_track.add_segment(audio_segment)

        current_time += segment.audio_duration


def _build_text_track(
    draft: JianyingDraft,
    segments: list,
    caption_style: str,
) -> None:
    """构建字幕轨道并写入各片段的字幕。"""
    text_track = Track(type=TrackType.TEXT)
    draft.add_track(text_track)

    caption_cfg = CAPTION_STYLES.get(caption_style, CAPTION_STYLES["cinematic"])

    for segment in segments:
        for cap in segment.captions:
            text_material = TextMaterial(
                content=cap["text"],
                font_size=caption_cfg["font_size"],  # type: ignore[arg-type]
                font_color=caption_cfg["font_color"],  # type: ignore[arg-type]
                has_shadow=caption_cfg["shadow"],  # type: ignore[arg-type]
            )
            draft.add_text(text_material)

            text_segment = Segment(
                material_id=text_material.id,
                source_timerange=TimeRange.from_seconds(0, cap["duration"]),
                target_timerange=TimeRange.from_seconds(cap["start"], cap["duration"]),
            )
            text_track.add_segment(text_segment)


def build_monologue_tracks(
    draft: JianyingDraft,
    source_video: str,
    video_duration: float,
    segments: list,
    caption_style: str = "cinematic",
) -> None:
    """
    构建独白视频的剪映轨道

    Args:
        draft: 剪映草稿对象
        source_video: 源视频路径
        video_duration: 视频时长（秒）
        segments: 独白片段列表
        caption_style: 字幕样式名称
    """
    _build_video_track(draft, source_video, video_duration, segments)
    _build_audio_track(draft, segments)
    _build_text_track(draft, segments, caption_style)


__all__ = [
    "CAPTION_STYLES",
    "build_monologue_tracks",
]