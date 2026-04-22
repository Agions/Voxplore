#!/usr/bin/env python3
"""测试项目设置管理器"""

from app.core.project_settings_manager import (
    SettingType,
    SettingDefinition,
)


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
            default_value="默认值"
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
            default_value=False
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
            options=["light", "dark", "auto"]
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
            max_value=1.0
        )
        
        assert definition.min_value == 0.1
        assert definition.max_value == 1.0
