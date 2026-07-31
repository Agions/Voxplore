"""Tests for the unified SettingsStore façade (Phase 4-3).

覆盖：
  * 前缀分发：app.* / llm.* → ConfigManager；project.* → ProjectSettingsManager；
    其它 → QSettings（或 headless fallback）
  * set() 写时拒绝 app.* / llm.*（只读）
  * keys() / has() / snapshot()
  * 未注入任何依赖时降级到 in-memory dict
"""

from __future__ import annotations

import pytest

from app.core.settings_store import SettingsStore, get_settings


class _FakeProvider:
    """``LLMProvider`` 的最小替身，足以让 _get_app 走得通。"""

    def __init__(self, model: str = "fake-model", base_url: str = "https://x", enabled: bool = True):
        self.model = model
        self.base_url = base_url
        self.enabled = enabled
        self.api_key = "sk-fake"
        self.max_tokens = 8192
        self.temperature = 0.7


class _FakeConfig:
    default_llm = "kimi"
    llm_providers = {
        "kimi": _FakeProvider(model="kimi-k3"),
        "openai": _FakeProvider(model="gpt-5.2"),
    }


class _FakeConfigManager:
    """``ConfigManager`` 替身：门面通过 ``.config`` 属性取配置对象。"""

    config = _FakeConfig()


class _FakeProject:
    def __init__(self) -> None:
        self.settings = {"language": "zh", "video.bitrate": 8000}


class _FakeQSettings:
    """QSettings 替身：内存 dict 存储。"""

    def __init__(self) -> None:
        self._store: dict[str, object] = {}

    def value(self, key: str, default=None):
        return self._store.get(key, default)

    def setValue(self, key: str, value) -> None:
        self._store[key] = value

    def allKeys(self):
        return list(self._store.keys())


@pytest.fixture(autouse=True)
def _reset_store() -> None:
    SettingsStore._instance = None
    yield
    SettingsStore._instance = None


class TestAppReadOnly:
    def test_app_default_llm_reads_from_config(self):
        s = SettingsStore()
        s.bind_config(_FakeConfigManager())
        assert s.get("app.default_llm") == "kimi"

    def test_llm_provider_reads_subkey(self):
        s = SettingsStore()
        s.bind_config(_FakeConfigManager())
        info = s.get("llm.kimi")
        assert isinstance(info, dict)
        assert info["model"] == "kimi-k3"
        assert info["enabled"] is True

    def test_set_app_is_noop(self):
        s = SettingsStore()
        s.bind_config(_FakeConfigManager())
        s.set("app.default_llm", "openai")
        # ConfigManager 内的值不会改变
        assert s.get("app.default_llm") == "kimi"

    def test_set_llm_is_noop(self):
        s = SettingsStore()
        s.bind_config(_FakeConfigManager())
        s.set("llm.kimi", {"model": "tampered"})
        assert s.get("llm.kimi")["model"] == "kimi-k3"


class TestProject:
    def test_get_set_roundtrip(self):
        s = SettingsStore()
        s.bind_project(_FakeProject())
        assert s.get("project.language") == "zh"
        s.set("project.language", "en")
        assert s.get("project.language") == "en"


class TestQSettings:
    def test_get_set_roundtrip(self):
        s = SettingsStore()
        qs = _FakeQSettings()
        s.bind_qsettings(qs)
        s.set("qt.theme", "dark")
        assert s.get("qt.theme") == "dark"

    def test_fallback_key(self):
        """未识别前缀 + 无 QSettings → in-memory dict。"""
        s = SettingsStore()
        s.set("custom.flag", True)
        assert s.get("custom.flag") is True


class TestHeadless:
    def test_unbound_returns_default(self):
        s = SettingsStore()
        assert s.get("anything", default="X") == "X"

    def test_unbound_set_persists_in_fallback(self):
        s = SettingsStore()
        s.set("onboarding.done", True)
        assert s.get("onboarding.done") is True


class TestKeys:
    def test_keys_includes_all_prefixes(self):
        s = SettingsStore()
        s.bind_config(_FakeConfigManager())
        s.bind_project(_FakeProject())
        s.bind_qsettings(_FakeQSettings())
        s.set("qt.theme", "dark")
        keys = s.keys()
        assert "app.default_llm" in keys
        assert "llm.kimi" in keys
        assert "project.language" in keys
        assert "qt.theme" in keys

    def test_keys_with_prefix_filter(self):
        s = SettingsStore()
        s.bind_config(_FakeConfigManager())
        s.bind_project(_FakeProject())
        keys = s.keys(prefix="llm.")
        assert all(k.startswith("llm.") for k in keys)
        assert "llm.kimi" in keys

    def test_has(self):
        s = SettingsStore()
        s.bind_config(_FakeConfigManager())
        s.bind_project(_FakeProject())
        assert s.has("app.default_llm") is True
        assert s.has("project.language") is True
        assert s.has("nope") is False

    def test_snapshot(self):
        s = SettingsStore()
        s.bind_project(_FakeProject())
        snap = s.snapshot()
        assert isinstance(snap, dict)
        assert snap["project.language"] == "zh"


class TestSingleton:
    def test_singleton(self):
        a = get_settings()
        b = get_settings()
        assert a is b
