#!/usr/bin/env python3
"""Shared page defaults for the main UI."""

from scenefab.services.ai.model_catalog import settings_model_options
from scenefab.services.export.presets import (
    DEFAULT_AUDIO_BITRATE_KBPS,
    DEFAULT_VERTICAL_RESOLUTION,
    DEFAULT_VIDEO_BITRATE_KBPS,
)

DEFAULT_PROJECT_DIR = "~/SceneFab/projects"
DEFAULT_EXPORT_DIR = "~/SceneFab/exports"
DEFAULT_FPS = 30
DEFAULT_VIDEO_CODEC_LABEL = "H.264"
DEFAULT_EXPORT_FORMAT_LABEL = "MP4"
DEFAULT_PLATFORM_LABEL = "Shorts / TikTok / Reels"

VIDEO_RESOLUTION_OPTIONS = [
    DEFAULT_VERTICAL_RESOLUTION,
    "720x1280",
    "1920x1080",
]
FPS_OPTIONS = [f"{fps} fps" for fps in (DEFAULT_FPS, 60, 24)]
CODEC_OPTIONS = [
    "MP4 / H.264",
    "MP4 / H.265",
    "MOV / ProRes",
]
LANGUAGE_OPTIONS = ["简体中文", "English"]


def default_video_bitrate() -> str:
    """Return the default video bitrate label used by export presets."""
    return f"{DEFAULT_VIDEO_BITRATE_KBPS}k"


def default_audio_bitrate() -> str:
    """Return the default audio bitrate label used by export presets."""
    return f"{DEFAULT_AUDIO_BITRATE_KBPS}k"


def default_delivery_summary() -> str:
    """Return the compact delivery summary shown on dashboard headers."""
    return (
        f"竖屏 {DEFAULT_VERTICAL_RESOLUTION} · {DEFAULT_FPS} fps · "
        f"{DEFAULT_VIDEO_CODEC_LABEL} · {default_video_bitrate()}"
    )


__all__ = [
    "CODEC_OPTIONS",
    "DEFAULT_EXPORT_DIR",
    "DEFAULT_EXPORT_FORMAT_LABEL",
    "DEFAULT_FPS",
    "DEFAULT_PLATFORM_LABEL",
    "DEFAULT_PROJECT_DIR",
    "DEFAULT_VERTICAL_RESOLUTION",
    "FPS_OPTIONS",
    "LANGUAGE_OPTIONS",
    "VIDEO_RESOLUTION_OPTIONS",
    "default_audio_bitrate",
    "default_delivery_summary",
    "default_video_bitrate",
    "settings_model_options",
]
