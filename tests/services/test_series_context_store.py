#!/usr/bin/env python3
"""Phase R · SeriesContext 跨项目复用持久化测试。"""

from __future__ import annotations

from app.core.settings_store import SettingsStore
from app.models.project import SeriesContext
from app.services.series_context_store import (
    KEY_LAST_USED,
    clear_series_context,
    load_series_context,
    save_series_context,
)


def _reset_store() -> None:
    """重置 SettingsStore 单例的内部状态以避免测试间污染。"""
    inst = SettingsStore()
    # 直接清空 fallback dict(测试环境无 QSettings)
    with inst._lock:  # type: ignore[attr-defined]
        inst._fallback.clear()  # type: ignore[attr-defined]


class TestSeriesContextStore:
    def test_save_and_load_round_trip(self):
        _reset_store()
        ctx = SeriesContext(
            series_title="深夜短剧",
            episode_naming="{title}_EP{ep:02d}",
            shared_characters=["小志", "阿娇"],
            shared_plot="凌晨 3 点的便利店",
            world_setting="都市 / 雾夜",
            genre="悬疑",
            total_episodes=24,
        )
        save_series_context(ctx)
        loaded = load_series_context()
        assert loaded is not None
        assert loaded.series_title == "深夜短剧"
        assert loaded.episode_naming == "{title}_EP{ep:02d}"
        assert loaded.shared_characters == ["小志", "阿娇"]
        assert loaded.shared_plot == "凌晨 3 点的便利店"
        assert loaded.world_setting == "都市 / 雾夜"
        assert loaded.genre == "悬疑"
        assert loaded.total_episodes == 24

    def test_load_returns_none_when_empty(self):
        _reset_store()
        assert load_series_context() is None

    def test_clear_removes_value(self):
        _reset_store()
        save_series_context(SeriesContext(
            series_title="临时", total_episodes=10))
        assert load_series_context() is not None
        clear_series_context()
        assert load_series_context() is None

    def test_corrupted_payload_returns_none(self):
        """非法 JSON / 类型异常 → 安全降级 None,不抛错。"""
        _reset_store()
        # 直接往 fallback 塞坏值,模拟磁盘损坏或版本不兼容
        inst = SettingsStore()
        with inst._lock:  # type: ignore[attr-defined]
            # type: ignore[attr-defined]
            inst._fallback[KEY_LAST_USED] = "{not_json{{{"
        assert load_series_context() is None

    def test_non_string_payload_returns_none(self):
        """``QSettings`` 在某些场景下会回退类型 → 安全降级。"""
        _reset_store()
        inst = SettingsStore()
        with inst._lock:  # type: ignore[attr-defined]
            inst._fallback[KEY_LAST_USED] = 12345  # type: ignore[attr-defined]
        # 非 str → 直接返回 None(json.loads 不会触发)
        assert load_series_context() is None

    def test_load_uses_from_dict_safe_fallback(self):
        """半合法 JSON（dict 缺字段）→ from_dict 安全降级。"""
        _reset_store()
        inst = SettingsStore()
        with inst._lock:  # type: ignore[attr-defined]
            # type: ignore[attr-defined]
            inst._fallback[KEY_LAST_USED] = '{"series_title": "X"}'
        loaded = load_series_context()
        assert loaded is not None
        assert loaded.series_title == "X"
        assert loaded.total_episodes == 0
        assert loaded.shared_characters == []

    def test_key_constant_matches_documented_path(self):
        """key 字符串锁住,避免改名后影响历史数据。"""
        assert KEY_LAST_USED == "qt.series_context.last_used"
