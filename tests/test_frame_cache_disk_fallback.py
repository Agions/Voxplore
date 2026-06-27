#!/usr/bin/env python3
"""
Regression test for VideoFrameCache disk fallback.

Covers:
1) Name mangling bug (双下划线 → 单下划线) — 之前磁盘回退 100% 静默失败
2) disk_write_count / disk_read_count 真的增加 (不再静默失败)
3) 磁盘文件能正确被读回 (回环测试)
"""

from pathlib import Path

import numpy as np

from scenefab.services.video.cache.frame_cache import (
    VideoFrameCache,
    _safe_pickle_dump,
    _safe_pickle_load,
)


def _make_frame(seed: int = 0) -> np.ndarray:
    """构造一个确定性的 numpy 帧 (10x10 RGB)"""
    rng = np.random.default_rng(seed)
    return rng.integers(0, 255, size=(10, 10, 3), dtype=np.uint8)


class TestSafePickleFunctions:
    """_safe_pickle_load / _safe_pickle_dump 基本读写"""

    def test_round_trip(self, tmp_path: Path) -> None:
        """_safe_pickle_dump 后 _safe_pickle_load 能取回原值"""
        path = tmp_path / "test.pkl"
        original = {"key": [1, 2, 3], "frame": _make_frame()}

        _safe_pickle_dump(original, path)
        assert path.exists()

        loaded = _safe_pickle_load(path)
        assert loaded["key"] == [1, 2, 3]
        assert np.array_equal(loaded["frame"], original["frame"])

    def test_owners_only_permissions(self, tmp_path: Path) -> None:
        """写入文件是 owner-only 权限 (0o600)"""
        import stat

        path = tmp_path / "test.pkl"
        _safe_pickle_dump({"data": "secret"}, path)

        mode = path.stat().st_mode
        # owner read+write, 没有 group/other 权限
        assert mode & stat.S_IRUSR
        assert mode & stat.S_IWUSR
        assert not (mode & stat.S_IRGRP)
        assert not (mode & stat.S_IROTH)


class TestFrameCacheDiskFallback:
    """VideoFrameCache 磁盘回退行为 — name mangling bug 回归测试"""

    def test_disk_write_actually_happens(self, tmp_path: Path) -> None:
        """触发磁盘回退后, disk_write_count 必须增加 (不再静默失败)"""
        # 限制内存只够存 2 帧, 第 3 帧会触发淘汰 + 磁盘回退
        cache = VideoFrameCache(
            max_frames=2,
            max_memory_mb=10,  # 10MB
            disk_fallback=True,
            temp_dir=str(tmp_path),
        )

        # 写入 3 帧 → 第 3 帧触发淘汰
        for i in range(3):
            cache.set(f"key_{i}", _make_frame(seed=i))

        stats = cache.get_stats()
        assert stats["eviction_count"] == 1, (
            f"应有 1 次淘汰, 实际 {stats['eviction_count']}"
        )
        # 关键断言: 磁盘写入真的发生了 (修前永远是 0 因为 name mangling NameError)
        assert stats["disk_write_count"] == 1, (
            f"应有 1 次磁盘写入, 实际 {stats['disk_write_count']} "
            f"(name mangling bug 会让此处恒为 0)"
        )

    def test_disk_read_after_eviction(self, tmp_path: Path) -> None:
        """被淘汰的帧能从磁盘读回 (回环验证)"""
        cache = VideoFrameCache(
            max_frames=2,
            max_memory_mb=10,
            disk_fallback=True,
            temp_dir=str(tmp_path),
        )

        # 写入 3 帧 (第 1 帧被淘汰到磁盘)
        for i in range(3):
            cache.set(f"key_{i}", _make_frame(seed=i))

        # 读回 key_0 (应从磁盘命中)
        frame = cache.get("key_0")
        assert frame is not None, "key_0 应从磁盘读回, 实际 None"

        # 验证内容一致
        assert np.array_equal(frame, _make_frame(seed=0))

        stats = cache.get_stats()
        assert stats["disk_read_count"] == 1, (
            f"应有 1 次磁盘读, 实际 {stats['disk_read_count']}"
        )

    def test_disk_read_corruption_logs_warning(self, tmp_path: Path, caplog) -> None:
        """磁盘文件损坏时, logger.warning 而不是 debug 静默"""
        import logging

        cache = VideoFrameCache(
            max_frames=1,
            max_memory_mb=10,
            disk_fallback=True,
            temp_dir=str(tmp_path),
        )

        # 写入 1 帧, 触发淘汰到磁盘
        cache.set("key_0", _make_frame(seed=0))
        cache.set("key_1", _make_frame(seed=1))  # 触发淘汰

        # 找到磁盘文件, 损坏它
        disk_files = list(tmp_path.glob("*.pkl"))
        assert len(disk_files) == 1
        disk_files[0].write_bytes(b"corrupted data, not a pickle")

        # 读 → 触发 UnpicklingError → 应被 except 捕获 + logger.warning
        with caplog.at_level(logging.WARNING, logger="scenefab.services.video.cache.frame_cache"):
            frame = cache.get("key_0")

        # 损坏的 pickle → 返回 None (回退到默认)
        assert frame is None

        # 关键: 应该是 WARNING 级别 (修前是 DEBUG 看不见)
        warning_records = [
            r for r in caplog.records if r.levelno == logging.WARNING
        ]
        assert any("磁盘读取失败" in r.message for r in warning_records), (
            f"应有 warning 级别日志, 实际: {[r.message for r in caplog.records]}"
        )

    def test_module_level_pickle_helpers_exist(self) -> None:
        """防御: 防止再次有人把 _safe_pickle_load 写成 __safe_pickle_load

        双下划线在 module-level 会被 Python 名字修饰 (name mangling),
        重命名为 _frame_cache__safe_pickle_load, 但调用点写的是 _safe_pickle_load
        → AttributeError → 磁盘回退 100% 静默失败
        """
        from scenefab.services.video.cache import frame_cache

        # 必须能直接通过 _safe_pickle_load 访问
        assert hasattr(frame_cache, "_safe_pickle_load")
        assert hasattr(frame_cache, "_safe_pickle_dump")
        # 不能有双下划线版本 (那是 module mangled, 不可调用)
        assert not hasattr(frame_cache, "__safe_pickle_load")
        assert not hasattr(frame_cache, "__safe_pickle_dump")
