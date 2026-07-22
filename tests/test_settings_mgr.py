#!/usr/bin/env python3
"""测试项目设置管理器"""

import logging
from pathlib import Path

from scenefab.settings.manager import (
    ProjectSettingsManager,
    SettingDefinition,
    SettingType,
)
from scenefab.settings.types import ProjectSettingsProfile
from scenefab.utils.json_io import read_json, write_json


def _settings_manager(tmp_path: Path) -> ProjectSettingsManager:
    manager = ProjectSettingsManager.__new__(ProjectSettingsManager)
    manager.config_manager = None
    manager.logger = logging.getLogger(__name__)
    manager.settings = {}
    manager.settings_definitions = {}
    manager.profiles = {}
    manager.settings_file = str(tmp_path / "project_settings.json")
    manager.profiles_file = str(tmp_path / "profiles.json")
    manager._init_settings_definitions()
    return manager


class TestSettingType:
    """测试设置类型枚举"""

    def test_string(self):
        assert SettingType.STRING.value == "string"

    def test_integer(self):
        assert SettingType.INTEGER.value == "integer"

    def test_float(self):
        assert SettingType.FLOAT.value == "float"

    def test_boolean(self):
        assert SettingType.BOOLEAN.value == "boolean"

    def test_list(self):
        assert SettingType.LIST.value == "list"

    def test_dict(self):
        assert SettingType.DICT.value == "dict"

    def test_color(self):
        assert SettingType.COLOR.value == "color"

    def test_path(self):
        assert SettingType.PATH.value == "path"

    def test_resolution(self):
        assert SettingType.RESOLUTION.value == "resolution"


class TestSettingDefinition:
    """测试设置定义"""

    def test_creation(self):
        definition = SettingDefinition(
            key="test_key",
            name="测试设置",
            description="这是一个测试设置",
            setting_type=SettingType.STRING,
            default_value="默认值",
        )

        assert definition.key == "test_key"
        assert definition.name == "测试设置"
        assert definition.setting_type == SettingType.STRING

    def test_default_values(self):
        definition = SettingDefinition(
            key="test",
            name="测试",
            description="描述",
            setting_type=SettingType.BOOLEAN,
            default_value=False,
        )

        assert definition.category == "general"
        assert definition.subcategory == ""
        assert definition.advanced is False

    def test_with_options(self):
        definition = SettingDefinition(
            key="theme",
            name="主题",
            description="应用主题",
            setting_type=SettingType.STRING,
            default_value="dark",
            options=["light", "dark", "auto"],
        )

        assert definition.options == ["light", "dark", "auto"]

    def test_with_range(self):
        definition = SettingDefinition(
            key="opacity",
            name="不透明度",
            description="窗口不透明度",
            setting_type=SettingType.FLOAT,
            default_value=1.0,
            min_value=0.1,
            max_value=1.0,
        )

        assert definition.min_value == 0.1
        assert definition.max_value == 1.0


class TestProjectSettingsManagerIO:
    """测试设置管理器 JSON 读写路径"""

    def test_load_settings_reads_json_and_ignores_unknown_keys(self, tmp_path: Path):
        manager = _settings_manager(tmp_path)
        write_json(
            manager.settings_file,
            {
                "video.bitrate": "12000k",
                "unknown.setting": "ignored",
            },
        )

        manager._load_settings()

        assert manager.settings["video.bitrate"] == "12000k"
        assert "unknown.setting" not in manager.settings

    def test_save_profiles_writes_json(self, tmp_path: Path):
        manager = _settings_manager(tmp_path)
        manager.profiles["自定义"] = ProjectSettingsProfile(
            name="自定义",
            description="测试配置",
            settings={"video.bitrate": "12000k"},
            created_at="2026-01-01T00:00:00",
            modified_at="2026-01-01T00:00:00",
        )

        manager._save_profiles()

        profiles_data = read_json(manager.profiles_file)
        assert profiles_data["自定义"]["settings"]["video.bitrate"] == "12000k"

    def test_export_and_import_settings_roundtrip(self, tmp_path: Path):
        manager = _settings_manager(tmp_path)
        manager._load_settings()
        assert manager.set_setting("video.bitrate", "12000k") is True

        export_path = tmp_path / "settings_export.json"
        assert manager.export_settings(str(export_path)) is True

        imported_manager = _settings_manager(tmp_path / "imported")
        imported_manager._load_settings()
        assert imported_manager.import_settings(str(export_path), merge=False) is True
        assert imported_manager.settings["video.bitrate"] == "12000k"
