#!/usr/bin/env python3
"""统一设置门面 — Phase 4 · settings_store。

项目里同时存在三套配置入口，调用方很难知道 key 该写到哪：

  1. ``ConfigManager``（``app/config/config.py``）—— 全局应用配置，从
     ``config/llm.yaml`` 与 ``config/app_config.yaml`` 加载。提供
     ``default_llm``、``llm_providers``、``cache``、``video``、``tts`` 等。
  2. ``ProjectSettingsManager``（``app/config/manager.py``）—— 项目级
     设置，提供 ``settings_changed`` 信号、按 key 类型校验、profile 导入
     /导出能力。
  3. ``QSettings``（PySide6）—— 跨平台原生 store，主窗口、theme_manager、
     settings_page 直接用，散落在 5+ 文件里。

本门面按 **key 前缀** fan-out：

  - ``app.<name>``      → ``ConfigManager`` 静态读取（不可写，仅查询）
  - ``llm.<provider>``  → ``ConfigManager`` 的 ``llm_providers`` 子表
  - ``project.<name>``  → ``ProjectSettingsManager``（可写）
  - ``qt.<name>``       → ``QSettings``（可写）
  - ``onboarding.<n>``  → ``QSettings``（Phase 3 已用）
  - 其它未识别前缀       → ``QSettings``（fallback）

设计原则：
  - 读路径优先返回 cached value，避免每次穿透 3 套 store
  - 写路径必须通过 ``set(key, value)``；不允许在外部直接修改
  - 单例懒加载；如未安装 PySide6（headless 测试），自动降级为
    in-memory dict 实现，保证业务代码不爆
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Iterator
from typing import Any

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────
#  前缀分发表
# ────────────────────────────────────────────────────────────────

_PREFIX_APP = "app."
_PREFIX_LLM = "llm."
_PREFIX_PROJECT = "project."
_PREFIX_QT = "qt."


# 已知是只读的应用级配置（防止误写）
_APP_READONLY = frozenset(
    {
        "app.name",
        "app.version",
        "app.debug",
        "app.cache.enabled",
        "app.cache.max_size",
        "app.cache.ttl",
        "app.cache.cache_dir",
        "app.video.*",
        "app.tts.*",
    }
)


# ────────────────────────────────────────────────────────────────
#  门面
# ────────────────────────────────────────────────────────────────


class SettingsStore:
    """统一设置门面（线程安全单例）。"""

    _instance: SettingsStore | None = None
    _instance_lock = threading.Lock()

    def __new__(cls) -> SettingsStore:
        with cls._instance_lock:
            if cls._instance is None:
                inst = super().__new__(cls)
                inst._init()
                cls._instance = inst
            return cls._instance

    def _init(self) -> None:
        self._lock = threading.RLock()
        # 延迟绑定：headless / 测试时 PySide6 不一定可用
        self._config_manager = None
        self._project_manager = None
        self._qsettings = None
        self._qsettings_available = False
        self._fallback: dict[str, Any] = {}

    # ─── 依赖注入点 ────────────────────────────────────────────

    def bind_config(self, manager: Any) -> None:
        """注入 ConfigManager（应用启动时调用）。"""
        with self._lock:
            self._config_manager = manager

    def bind_project(self, manager: Any) -> None:
        """注入 ProjectSettingsManager。"""
        with self._lock:
            self._project_manager = manager

    def bind_qsettings(self, qsettings: Any) -> None:
        """注入 QSettings 实例。"""
        with self._lock:
            self._qsettings = qsettings
            self._qsettings_available = qsettings is not None

    def is_headless(self) -> bool:
        """当前是否在 headless / 降级模式（无 QSettings）。"""
        with self._lock:
            return not self._qsettings_available

    # ─── 读 ─────────────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        """按 key 读取值，未命中返回 ``default``。"""
        with self._lock:
            if key.startswith(_PREFIX_APP) or key.startswith(_PREFIX_LLM):
                return self._get_app(key, default)
            if key.startswith(_PREFIX_PROJECT):
                return self._get_project(key, default)
            # 默认 + qt.* → QSettings
            return self._get_qt(key, default)

    def _get_app(self, key: str, default: Any) -> Any:
        if self._config_manager is None:
            return default
        cfg = self._config_manager.config
        if key == "app.default_llm":
            return getattr(cfg, "default_llm", default)
        if key == "app.llm_providers":
            return {
                name: {
                    "model": p.model,
                    "base_url": p.base_url,
                    "enabled": p.enabled,
                }
                for name, p in cfg.llm_providers.items()
            }
        if key.startswith("llm."):
            provider = key[len(_PREFIX_LLM):]
            p = cfg.llm_providers.get(provider)
            if p is None:
                return default
            return {
                "model": p.model,
                "base_url": p.base_url,
                "enabled": p.enabled,
                "max_tokens": p.max_tokens,
                "temperature": p.temperature,
            }
        return default

    def _get_project(self, key: str, default: Any) -> Any:
        if self._project_manager is None:
            return self._fallback.get(key, default)
        short = key[len(_PREFIX_PROJECT):]
        return self._project_manager.settings.get(short, default)

    def _get_qt(self, key: str, default: Any) -> Any:
        if self._qsettings is None:
            return self._fallback.get(key, default)
        value = self._qsettings.value(key, None)
        return default if value is None else value

    # ─── 写 ─────────────────────────────────────────────────────

    def set(self, key: str, value: Any) -> None:
        """按 key 写入值。只允许写 ``project.*`` / ``qt.*`` / 其它。"""
        with self._lock:
            if key.startswith(_PREFIX_APP) or key.startswith(_PREFIX_LLM):
                # 应用级配置在 YAML 里定义，不允许运行时改写
                logger.debug(f"SettingsStore.set ignored readonly key={key}")
                return
            if key.startswith(_PREFIX_PROJECT):
                self._set_project(key, value)
            else:
                self._set_qt(key, value)

    def _set_project(self, key: str, value: Any) -> None:
        if self._project_manager is None:
            self._fallback[key] = value
            return
        short = key[len(_PREFIX_PROJECT):]
        self._project_manager.settings[short] = value

    def _set_qt(self, key: str, value: Any) -> None:
        if self._qsettings is None:
            self._fallback[key] = value
            return
        self._qsettings.setValue(key, value)

    # ─── 其它便利方法 ──────────────────────────────────────────

    def has(self, key: str) -> bool:
        """key 是否存在（任意一层 store 命中即返回 True）。"""
        try:
            return self.get(key, _MISSING) is not _MISSING
        except Exception:  # noqa: BLE001
            return False

    def keys(self, prefix: str | None = None) -> list[str]:
        """枚举所有 key（按前缀过滤）。"""
        keys: set[str] = set()
        if self._config_manager is not None:
            keys.add("app.default_llm")
            keys.add("app.llm_providers")
            for name in self._config_manager.config.llm_providers:
                keys.add(f"llm.{name}")
        if self._project_manager is not None:
            for k in self._project_manager.settings:
                keys.add(f"project.{k}")
        if self._qsettings is not None:
            for k in self._qsettings.allKeys():
                keys.add(k)
        else:
            keys.update(self._fallback.keys())
        if prefix:
            keys = {k for k in keys if k.startswith(prefix)}
        return sorted(keys)

    def prefix(self, prefix: str) -> Iterator[tuple[str, Any]]:
        """``(key, value)`` 迭代（lazy）。"""
        for k in self.keys(prefix=prefix):
            yield k, self.get(k)

    def snapshot(self) -> dict[str, Any]:
        """导出全部 key → value 的字典（用于诊断 / 落盘）。"""
        return {k: self.get(k) for k in self.keys()}


_MISSING = object()


# ────────────────────────────────────────────────────────────────
#  模块级便捷 API
# ────────────────────────────────────────────────────────────────


def get_settings() -> SettingsStore:
    return SettingsStore()


__all__ = ["SettingsStore", "get_settings"]
