#!/usr/bin/env python3
"""Static view models for main UI pages."""

from dataclasses import dataclass

from app.pipeline.fp_workflow import (
    FIRST_PERSON_QUALITY_GATES,
    FIRST_PERSON_SCRIPT_RULES,
    numbered_workflow,
)

from .page_defaults import (
    DEFAULT_EXPORT_DIR,
    DEFAULT_PLATFORM_LABEL,
    DEFAULT_PROJECT_DIR,
    DEFAULT_VERTICAL_RESOLUTION,
    FPS_OPTIONS,
    default_audio_bitrate,
    default_video_bitrate,
    settings_model_options,
)


@dataclass(frozen=True, slots=True)
class StatusCardView:
    """Dashboard status card content."""

    title_key: str = ""
    status_key: str = ""
    value: str = ""
    # Backwards-compat fallbacks: callers building a card from raw
    # strings (e.g. tests) can still pass ``title="…"`` and have the
    # literal text displayed verbatim when no key is set.
    title: str = ""
    status: str = ""


@dataclass(frozen=True, slots=True)
class WorkflowStepView:
    """Workflow row content."""

    number_key: str = ""
    name_key: str = ""
    detail_key: str = ""
    number: str = ""
    name: str = ""
    detail: str = ""


@dataclass(frozen=True, slots=True)
class KeyValueView:
    """Simple key/value display row."""

    label_key: str = ""
    value: str = ""
    label: str = ""


@dataclass(frozen=True, slots=True)
class SettingRowView:
    """Settings row content and control type."""

    key: str
    label: str = ""
    control: str = "label"
    description: str = ""
    value: str = ""
    options: tuple[str, ...] = ()
    checked: bool = False
    placeholder: str = ""
    # Optional i18n keys: when set, ``SettingsPage._row`` will look up
    # the localized text instead of using ``label``/``description``.
    # ``_key`` is what the row looks up in the ``settings.row.*`` and
    # ``settings.group.*`` namespaces; the row's *group* title uses
    # ``group_key`` (set on the surrounding tuple below).
    label_key: str = ""
    description_key: str = ""
    group_key: str = ""
    # Parallel ``options_keys`` list: when non-empty, ``_combo`` treats
    # ``options`` as i18n keys (in the same order) and the combo's
    # ``retranslate()`` pass refreshes each item using its key. This
    # keeps theme / language / codec / canvas / fps options in sync with
    # the active language without needing a literal→label mapping.
    options_keys: tuple[str, ...] = ()
    # When ``control == "button"``, this is the i18n key for the button
    # text. ``label_key`` keeps the row label (left column) and
    # ``description_key`` the desc (small print below).
    button_label_key: str = ""


HOME_STATUS_CARDS = (
    StatusCardView(
        title_key="home.status.media",
        status_key="home.status.media.empty",
        value="0",
    ),
    StatusCardView(
        title_key="home.status.scenes",
        status_key="home.status.scenes.empty",
        value="0",
    ),
    StatusCardView(
        title_key="home.status.script",
        status_key="home.status.script.empty",
        value="--",
    ),
    StatusCardView(
        title_key="home.status.export",
        status_key="home.status.export.empty",
        value=DEFAULT_VERTICAL_RESOLUTION,
    ),
)

HOME_WORKFLOW_STEPS = (
    WorkflowStepView(
        number_key="home.workflow.step1.number",
        name_key="home.workflow.step1.name",
        detail_key="home.workflow.step1.detail",
    ),
    WorkflowStepView(
        number_key="home.workflow.step2.number",
        name_key="home.workflow.step2.name",
        detail_key="home.workflow.step2.detail",
    ),
    WorkflowStepView(
        number_key="home.workflow.step3.number",
        name_key="home.workflow.step3.name",
        detail_key="home.workflow.step3.detail",
    ),
    WorkflowStepView(
        number_key="home.workflow.step4.number",
        name_key="home.workflow.step4.name",
        detail_key="home.workflow.step4.detail",
    ),
    WorkflowStepView(
        number_key="home.workflow.step5.number",
        name_key="home.workflow.step5.name",
        detail_key="home.workflow.step5.detail",
    ),
)

DELIVERY_PARAMETERS = (
    KeyValueView(label_key="home.delivery.resolution",
                 value=DEFAULT_VERTICAL_RESOLUTION),
    KeyValueView(label_key="home.delivery.fps", value=default_video_bitrate()),
    KeyValueView(label_key="home.delivery.bitrate",
                 value=default_audio_bitrate()),
    KeyValueView(label_key="home.delivery.codec",
                 value=DEFAULT_PLATFORM_LABEL),
)

PRODUCTION_STEPS = tuple(
    WorkflowStepView(number=number, name=stage.title, detail=stage.description)
    for number, stage in numbered_workflow()
)

SCRIPT_BRIEF_RULES = tuple(
    KeyValueView(label=rule.label, value=rule.value) for rule in FIRST_PERSON_SCRIPT_RULES
)

# Forwarded as ``_C.*``-independent plain strings for now; consumers in
# ``production_page._check_item`` may swap to i18n keys in a later pass.

EXPORT_QUALITY_CHECKS = (
    *FIRST_PERSON_QUALITY_GATES,
    f"成片默认 {DEFAULT_VERTICAL_RESOLUTION}",
)

ASSET_TABLE_COLUMNS = (
    "assets.table.column.kind",
    "assets.table.column.name",
    "assets.table.column.created",
)

ASSET_SOURCE_ITEMS = (
    ("assets.source.media_dir", "settings", "assets.source.media_dir.value_empty"),
    ("assets.source.export_dir", "settings",
     "assets.source.export_dir.value_default"),
    ("assets.source.resources", None, "assets.source.resources.value"),
)

SETTINGS_GROUPS = (
    (
        "settings.group.workspace",
        (
            SettingRowView(
                "project_dir",
                control="path",
                value=DEFAULT_PROJECT_DIR,
                label_key="settings.row.project_dir.label",
                description_key="settings.row.project_dir.desc",
            ),
            SettingRowView(
                "export_dir",
                control="path",
                value=DEFAULT_EXPORT_DIR,
                label_key="settings.row.export_dir.label",
                description_key="settings.row.export_dir.desc",
            ),
            SettingRowView(
                "language",
                control="combo",
                options=(
                    "settings.language.zh-CN",
                    "settings.language.en-US",
                ),
                options_keys=(
                    "settings.language.zh-CN",
                    "settings.language.en-US",
                ),
                label_key="settings.row.language.label",
            ),
        ),
    ),
    (
        "settings.group.ai",
        (
            SettingRowView(
                "qwen_api_key",
                control="password",
                placeholder="输入 QWEN_API_KEY",
                label_key="settings.row.qwen_api_key.label",
                description_key="settings.row.qwen_api_key.desc",
            ),
            SettingRowView(
                "deepseek_api_key",
                control="password",
                placeholder="输入 DEEPSEEK_API_KEY",
                label_key="settings.row.deepseek_api_key.label",
                description_key="settings.row.deepseek_api_key.desc",
            ),
            SettingRowView(
                "openai_api_key",
                control="password",
                placeholder="输入 OPENAI_API_KEY",
                label_key="settings.row.openai_api_key.label",
                description_key="settings.row.openai_api_key.desc",
            ),
            SettingRowView(
                "kimi_api_key",
                control="password",
                placeholder="输入 KIMI_API_KEY",
                label_key="settings.row.kimi_api_key.label",
                description_key="settings.row.kimi_api_key.desc",
            ),
            SettingRowView(
                "glm_api_key",
                control="password",
                placeholder="输入 GLM_API_KEY",
                label_key="settings.row.glm_api_key.label",
                description_key="settings.row.glm_api_key.desc",
            ),
            SettingRowView(
                "gemini_api_key",
                control="password",
                placeholder="输入 GEMINI_API_KEY",
                label_key="settings.row.gemini_api_key.label",
                description_key="settings.row.gemini_api_key.desc",
            ),
            SettingRowView(
                "api_key",
                control="password",
                placeholder="输入默认 API Key",
                label_key="settings.row.api_key.label",
                description_key="settings.row.api_key.desc",
            ),
            SettingRowView(
                "default_model",
                control="combo",
                options=tuple(settings_model_options()),
                options_keys=tuple(settings_model_options()),
                label_key="settings.row.default_model.label",
                description_key="settings.row.default_model.desc",
            ),
        ),
    ),
    (
        "settings.group.export",
        (
            SettingRowView(
                "canvas",
                control="combo",
                options=(
                    "settings.canvas.9_16",
                    "settings.canvas.16_9",
                    "settings.canvas.1_1",
                ),
                options_keys=(
                    "settings.canvas.9_16",
                    "settings.canvas.16_9",
                    "settings.canvas.1_1",
                ),
                label_key="settings.row.canvas.label",
                description_key="settings.row.canvas.desc",
            ),
            SettingRowView(
                "fps",
                control="combo",
                options=tuple(FPS_OPTIONS),
                label_key="settings.row.fps.label",
            ),
            SettingRowView(
                "codec",
                control="combo",
                options=(
                    "settings.codec.h264",
                    "settings.codec.h265",
                    "settings.codec.prores",
                ),
                options_keys=(
                    "settings.codec.h264",
                    "settings.codec.h265",
                    "settings.codec.prores",
                ),
                label_key="settings.row.codec.label",
            ),
        ),
    ),
    (
        "settings.group.behavior",
        (
            SettingRowView(
                "theme",
                control="combo",
                options=(
                    "settings.theme.system",
                    "settings.theme.light",
                    "settings.theme.dark",
                ),
                options_keys=(
                    "settings.theme.system",
                    "settings.theme.light",
                    "settings.theme.dark",
                ),
                label_key="settings.row.theme.label",
                description_key="settings.row.theme.desc",
            ),
            SettingRowView(
                "auto_save",
                control="toggle",
                checked=True,
                label_key="settings.row.auto_save.label",
                description_key="settings.row.auto_save.desc",
            ),
            SettingRowView(
                "minimize_to_tray",
                control="toggle",
                label_key="settings.row.minimize_to_tray.label",
                description_key="settings.row.minimize_to_tray.desc",
            ),
        ),
    ),
    # Phase 3 · Help & Support
    (
        "settings.group.help",
        (
            SettingRowView(
                "help.open",
                control="button",
                label_key="settings.row.help_panel.label",
                description_key="settings.row.help_panel.desc",
                button_label_key="settings.row.help_panel.label",
            ),
            SettingRowView(
                "help.reset_onboarding",
                control="button",
                label_key="settings.row.help_reset_onboarding.label",
                description_key="settings.row.help_reset_onboarding.desc",
                button_label_key="settings.row.help_reset_onboarding.label",
            ),
            SettingRowView(
                "help.copy_diagnostics",
                control="button",
                label_key="settings.row.help_diagnostics.label",
                description_key="settings.row.help_diagnostics.desc",
                button_label_key="settings.row.help_diagnostics.label",
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
