#!/usr/bin/env python3

"""
设置定义数据

包含所有设置项的定义元数据，按类别组织。
供 ProjectSettingsManager 初始化使用。

类别:
- video: 视频设置
- audio: 音频设置
- auto_save: 自动保存设置
- ai: AI设置
- ui: 界面设置
- performance: 性能设置
- export: 导出设置
"""

from app.services.ai.model_catalog import DEFAULT_MODELS, settings_model_options

from .types import ConfigDefinition, SettingType


def _get_video_settings() -> dict[str, ConfigDefinition]:
    """视频设置定义"""
    return {
        "video.resolution": ConfigDefinition(
            key="video.resolution",
            name="视频分辨率",
            description="输出视频的分辨率",
            setting_type=SettingType.RESOLUTION,
            default_value="1920x1080",
            options=["3840x2160", "2560x1440", "1920x1080", "1280x720", "854x480"],
            category="video",
            subcategory="basic",
        ),
        "video.fps": ConfigDefinition(
            key="video.fps",
            name="帧率",
            description="视频的帧率（每秒帧数）",
            setting_type=SettingType.INTEGER,
            default_value=30,
            min_value=1,
            max_value=120,
            category="video",
            subcategory="basic",
        ),
        "video.bitrate": ConfigDefinition(
            key="video.bitrate",
            name="视频比特率",
            description="视频编码比特率",
            setting_type=SettingType.STRING,
            default_value="8000k",
            options=["4000k", "6000k", "8000k", "12000k", "16000k", "20000k"],
            category="video",
            subcategory="advanced",
        ),
        "video.codec": ConfigDefinition(
            key="video.codec",
            name="视频编码器",
            description="视频编码器类型",
            setting_type=SettingType.STRING,
            default_value="h264",
            options=["h264", "h265", "vp9", "av1"],
            category="video",
            subcategory="advanced",
            restart_required=True,
        ),
        "video.colorspace": ConfigDefinition(
            key="video.colorspace",
            name="色彩空间",
            description="视频色彩空间",
            setting_type=SettingType.STRING,
            default_value="bt709",
            options=["bt709", "bt2020", "smpte240m"],
            category="video",
            subcategory="advanced",
        ),
    }


def _get_audio_settings() -> dict[str, ConfigDefinition]:
    """音频设置定义"""
    return {
        "audio.sample_rate": ConfigDefinition(
            key="audio.sample_rate",
            name="采样率",
            description="音频采样率",
            setting_type=SettingType.INTEGER,
            default_value=44100,
            options=[22050, 44100, 48000, 96000],  # type: ignore[list-item]
            category="audio",
            subcategory="basic",
        ),
        "audio.bitrate": ConfigDefinition(
            key="audio.bitrate",
            name="音频比特率",
            description="音频编码比特率",
            setting_type=SettingType.STRING,
            default_value="192k",
            options=["128k", "192k", "256k", "320k"],
            category="audio",
            subcategory="basic",
        ),
        "audio.channels": ConfigDefinition(
            key="audio.channels",
            name="声道数",
            description="音频声道数",
            setting_type=SettingType.INTEGER,
            default_value=2,
            min_value=1,
            max_value=8,
            category="audio",
            subcategory="basic",
        ),
        "audio.codec": ConfigDefinition(
            key="audio.codec",
            name="音频编码器",
            description="音频编码器类型",
            setting_type=SettingType.STRING,
            default_value="aac",
            options=["aac", "mp3", "opus", "flac"],
            category="audio",
            subcategory="advanced",
        ),
    }


def _get_auto_save_settings() -> dict[str, ConfigDefinition]:
    """自动保存设置定义"""
    return {
        "auto_save.enabled": ConfigDefinition(
            key="auto_save.enabled",
            name="启用自动保存",
            description="自动保存项目更改",
            setting_type=SettingType.BOOLEAN,
            default_value=True,
            category="auto_save",
            subcategory="basic",
        ),
        "auto_save.interval": ConfigDefinition(
            key="auto_save.interval",
            name="自动保存间隔",
            description="自动保存的时间间隔（秒）",
            setting_type=SettingType.INTEGER,
            default_value=300,
            min_value=60,
            max_value=3600,
            category="auto_save",
            subcategory="basic",
        ),
        "auto_save.max_backups": ConfigDefinition(
            key="auto_save.max_backups",
            name="最大备份数",
            description="保留的最大备份文件数",
            setting_type=SettingType.INTEGER,
            default_value=10,
            min_value=1,
            max_value=50,
            category="auto_save",
            subcategory="advanced",
        ),
    }


def _get_ai_settings() -> dict[str, ConfigDefinition]:
    """AI设置定义"""
    return {
        "ai.default_model": ConfigDefinition(
            key="ai.default_model",
            name="默认AI模型",
            description="默认使用的AI模型",
            setting_type=SettingType.STRING,
            default_value=DEFAULT_MODELS["deepseek"],
            options=settings_model_options(),
            category="ai",
            subcategory="models",
        ),
        "ai.max_tokens": ConfigDefinition(
            key="ai.max_tokens",
            name="最大令牌数",
            description="AI响应的最大令牌数",
            setting_type=SettingType.INTEGER,
            default_value=2000,
            min_value=100,
            max_value=8000,
            category="ai",
            subcategory="models",
        ),
        "ai.temperature": ConfigDefinition(
            key="ai.temperature",
            name="创造性程度",
            description="AI响应的创造性程度",
            setting_type=SettingType.FLOAT,
            default_value=0.7,
            min_value=0.0,
            max_value=2.0,
            category="ai",
            subcategory="models",
        ),
        "ai.enable_cache": ConfigDefinition(
            key="ai.enable_cache",
            name="启用AI缓存",
            description="缓存AI响应以提高性能",
            setting_type=SettingType.BOOLEAN,
            default_value=True,
            category="ai",
            subcategory="performance",
        ),
    }


def _get_ui_settings() -> dict[str, ConfigDefinition]:
    """界面设置定义"""
    return {
        "ui.theme": ConfigDefinition(
            key="ui.theme",
            name="主题",
            description="应用程序主题",
            setting_type=SettingType.STRING,
            default_value="dark",
            options=["light", "dark", "auto"],
            category="ui",
            subcategory="appearance",
            restart_required=True,
        ),
        "ui.language": ConfigDefinition(
            key="ui.language",
            name="语言",
            description="界面语言",
            setting_type=SettingType.STRING,
            default_value="zh-CN",
            options=["zh-CN", "en-US", "ja-JP", "ko-KR"],
            category="ui",
            subcategory="appearance",
            restart_required=True,
        ),
        "ui.font_size": ConfigDefinition(
            key="ui.font_size",
            name="字体大小",
            description="界面字体大小",
            setting_type=SettingType.INTEGER,
            default_value=12,
            min_value=8,
            max_value=24,
            category="ui",
            subcategory="appearance",
        ),
        "ui.show_tips": ConfigDefinition(
            key="ui.show_tips",
            name="显示提示",
            description="显示操作提示和教程",
            setting_type=SettingType.BOOLEAN,
            default_value=True,
            category="ui",
            subcategory="behavior",
        ),
        "ui.minimize_to_tray": ConfigDefinition(
            key="ui.minimize_to_tray",
            name="关闭时最小化到系统托盘",
            description="点击关闭按钮时缩放到系统托盘（需系统支持托盘）。默认关闭：直接退出应用",
            setting_type=SettingType.BOOLEAN,
            default_value=False,
            category="ui",
            subcategory="behavior",
        ),
    }


def _get_performance_settings() -> dict[str, ConfigDefinition]:
    """性能设置定义"""
    return {
        "performance.enable_gpu": ConfigDefinition(
            key="performance.enable_gpu",
            name="启用GPU加速",
            description="使用GPU进行视频处理",
            setting_type=SettingType.BOOLEAN,
            default_value=True,
            category="performance",
            subcategory="hardware",
        ),
        "performance.memory_limit": ConfigDefinition(
            key="performance.memory_limit",
            name="内存限制",
            description="最大内存使用量（MB）",
            setting_type=SettingType.INTEGER,
            default_value=4096,
            min_value=1024,
            max_value=16384,
            category="performance",
            subcategory="hardware",
        ),
        "performance.thread_count": ConfigDefinition(
            key="performance.thread_count",
            name="线程数",
            description="并行处理的线程数",
            setting_type=SettingType.INTEGER,
            default_value=4,
            min_value=1,
            max_value=16,
            category="performance",
            subcategory="processing",
        ),
    }


def _get_export_settings() -> dict[str, ConfigDefinition]:
    """导出设置定义"""
    return {
        "export.default_format": ConfigDefinition(
            key="export.default_format",
            name="默认导出格式",
            description="默认的导出文件格式",
            setting_type=SettingType.STRING,
            default_value="mp4",
            options=["mp4", "mov", "avi", "mkv", "webm"],
            category="export",
            subcategory="format",
        ),
        "export.quality": ConfigDefinition(
            key="export.quality",
            name="导出质量",
            description="导出视频的质量级别",
            setting_type=SettingType.STRING,
            default_value="high",
            options=["low", "medium", "high", "ultra"],
            category="export",
            subcategory="quality",
        ),
        "export.metadata.enabled": ConfigDefinition(
            key="export.metadata.enabled",
            name="包含元数据",
            description="导出时包含项目元数据",
            setting_type=SettingType.BOOLEAN,
            default_value=True,
            category="export",
            subcategory="metadata",
        ),
    }


def get_all_config_definitions() -> dict[str, ConfigDefinition]:
    """获取所有设置定义"""
    all_defs: dict[str, ConfigDefinition] = {}
    all_defs.update(_get_video_settings())
    all_defs.update(_get_audio_settings())
    all_defs.update(_get_auto_save_settings())
    all_defs.update(_get_ai_settings())
    all_defs.update(_get_ui_settings())
    all_defs.update(_get_performance_settings())
    all_defs.update(_get_export_settings())
    return all_defs


__all__ = [
    "get_all_config_definitions",
]
