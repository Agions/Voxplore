"""Tests for app.plugins.loader - entry_points discovery"""

from unittest.mock import MagicMock, patch

from scenefab.plugins.interfaces.base import PluginType
from scenefab.plugins.loader import PluginLoader


class TestPluginLoaderEntryPoints:
    def test_entry_point_group_name(self):
        assert PluginLoader.ENTRY_POINT_GROUP == "scenefab.plugins"

    def test_discover_via_entry_points_empty(self):
        """When no entry_points match, should return empty list"""
        loader = PluginLoader()
        # Patch at the import site inside the method
        with patch("importlib.metadata.entry_points", return_value=MagicMock(select=lambda group: [])):
            result = loader._discover_via_entry_points()
            assert result == []

    def test_discover_via_entry_points_with_plugins(self):
        """Should parse entry_point into PluginManifest"""
        loader = PluginLoader()

        # Use proper mock with string attributes matching importlib.metadata Entry object
        fake_ep = MagicMock()
        fake_ep.module = "my_plugin"        # set explicitly so it returns string
        fake_ep.attr = "MyPlugin"
        fake_ep.name = "my-plugin"
        fake_ep.value = "my_plugin:MyPlugin"
        fake_ep.group = "scenefab.plugins"

        fake_class = type("MyPlugin", (), {"__name__": "MyPlugin"})
        fake_ep.load.return_value = fake_class

        fake_eps = MagicMock()
        fake_eps.select.return_value = [fake_ep]

        with patch("importlib.metadata.entry_points", return_value=fake_eps):
            manifests = loader._discover_via_entry_points()

        assert len(manifests) == 1
        assert manifests[0].entry_point == "my_plugin:MyPlugin"
        assert manifests[0].plugin_type == PluginType.AI_GENERATOR  # default

    def test_infer_manifest_from_ep_detects_subtitle(self):
        """Should infer subtitle type from class name"""
        loader = PluginLoader()
        fake_ep = MagicMock()
        fake_ep.module = "sub_plugin"
        fake_ep.attr = "SubtitleStyle"
        fake_class = type("SubtitlePlugin", (), {"__name__": "SubtitlePlugin"})

        result = loader._infer_manifest_from_ep(fake_ep, fake_class)
        assert result.plugin_type == PluginType.SUBTITLE_STYLE
