#!/usr/bin/env python3
"""Static view models for main UI pages."""

from dataclasses import dataclass

from scenefab.pipeline.fp_workflow import (
    FIRST_PERSON_QUALITY_GATES,
    FIRST_PERSON_SCRIPT_RULES,
    numbered_workflow,
)

from .page_defaults import (
    CODEC_OPTIONS,
    DEFAULT_EXPORT_DIR,
    DEFAULT_PLATFORM_LABEL,
    DEFAULT_PROJECT_DIR,
    DEFAULT_VERTICAL_RESOLUTION,
    FPS_OPTIONS,
    LANGUAGE_OPTIONS,
    VIDEO_RESOLUTION_OPTIONS,
    default_audio_bitrate,
    default_video_bitrate,
    settings_model_options,
)


@dataclass(frozen=True, slots=True)
class StatusCardView:
    """Dashboard status card content."""

    title: str
    status: str
    value: str


@dataclass(frozen=True, slots=True)
class WorkflowStepView:
    """Workflow row content."""

    number: str
    name: str
    detail: str


@dataclass(frozen=True, slots=True)
class KeyValueView:
    """Simple key/value display row."""

    label: str
    value: str


@dataclass(frozen=True, slots=True)
class SettingRowView:
    """Settings row content and control type."""

    key: str
    label: str
    control: str
    description: str = ""
    value: str = ""
    options: tuple[str, ...] = ()
    checked: bool = False
    placeholder: str = ""


HOME_STATUS_CARDS = (
    StatusCardView("素材", "未导入", "0"),
    StatusCardView("场景", "未拆分", "0"),
    StatusCardView("脚本", "待生成", "--"),
    StatusCardView("导出", "待配置", DEFAULT_VERTICAL_RESOLUTION),
)

HOME_WORKFLOW_STEPS = (
    WorkflowStepView("01", "高能素材", "未开始"),
    WorkflowStepView("02", "冲突拆解", "未开始"),
    WorkflowStepView("03", "第一人称钩子", "未开始"),
    WorkflowStepView("04", "节奏字幕", "未开始"),
    WorkflowStepView("05", "发布复盘", "未开始"),
)

DELIVERY_PARAMETERS = (
    KeyValueView("画布", DEFAULT_VERTICAL_RESOLUTION),
    KeyValueView("视频码率", default_video_bitrate()),
    KeyValueView("音频码率", default_audio_bitrate()),
    KeyValueView("平台", DEFAULT_PLATFORM_LABEL),
)

PRODUCTION_STEPS = tuple(
    WorkflowStepView(number, stage.title, stage.description)
    for number, stage in numbered_workflow()
)

SCRIPT_BRIEF_RULES = tuple(
    KeyValueView(rule.label, rule.value) for rule in FIRST_PERSON_SCRIPT_RULES
)

EXPORT_QUALITY_CHECKS = (
    *FIRST_PERSON_QUALITY_GATES,
    f"成片默认 {DEFAULT_VERTICAL_RESOLUTION}",
)

ASSET_TABLE_COLUMNS = ("类型", "名称", "创建日期")

ASSET_SOURCE_ITEMS = (
    KeyValueView("素材目录", "未设置"),
    KeyValueView("输出目录", DEFAULT_EXPORT_DIR),
    KeyValueView("资源规范", "显式打包 resources/"),
)

SETTINGS_GROUPS = (
    (
        "工作区",
        (
            SettingRowView(
                "project_dir",
                "项目目录",
                "path",
                "默认项目保存位置",
                value=DEFAULT_PROJECT_DIR,
            ),
            SettingRowView(
                "export_dir",
                "输出目录",
                "path",
                "成片和草稿导出位置",
                value=DEFAULT_EXPORT_DIR,
            ),
            SettingRowView(
                "language",
                "界面语言",
                "combo",
                options=tuple(LANGUAGE_OPTIONS),
            ),
        ),
    ),
    (
        "AI 服务",
        (
            SettingRowView(
                "api_key",
                "API Key",
                "password",
                "用于脚本生成和画面理解",
                placeholder="输入 API Key",
            ),
            SettingRowView(
                "default_model",
                "默认模型",
                "combo",
                "影响脚本质量和响应速度",
                options=tuple(settings_model_options()),
            ),
        ),
    ),
    (
        "导出默认值",
        (
            SettingRowView(
                "canvas",
                "画布",
                "combo",
                "短视频默认使用竖屏 9:16",
                options=tuple(VIDEO_RESOLUTION_OPTIONS),
            ),
            SettingRowView("fps", "帧率", "combo", options=tuple(FPS_OPTIONS)),
            SettingRowView("codec", "编码", "combo", options=tuple(CODEC_OPTIONS)),
        ),
    ),
    (
        "应用行为",
        (
            SettingRowView(
                "theme",
                "主题",
                "combo",
                "切换浅色或深色外观",
                options=("浅色", "深色"),
            ),
            SettingRowView(
                "auto_save",
                "自动保存",
                "toggle",
                "每 5 分钟保存项目状态",
                checked=True,
            ),
            SettingRowView(
                "minimize_to_tray",
                "关闭到系统托盘",
                "toggle",
                "关闭窗口时保持后台运行",
            ),
        ),
    ),
)


__all__ = [
    "ASSET_SOURCE_ITEMS",
    "ASSET_TABLE_COLUMNS",
    "DELIVERY_PARAMETERS",
    "EXPORT_QUALITY_CHECKS",
    "HOME_STATUS_CARDS",
    "HOME_WORKFLOW_STEPS",
    "PRODUCTION_STEPS",
    "SCRIPT_BRIEF_RULES",
    "KeyValueView",
    "SETTINGS_GROUPS",
    "SettingRowView",
    "StatusCardView",
    "WorkflowStepView",
]
