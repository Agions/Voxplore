#!/usr/bin/env python3
"""
Translator · 翻译器单例。

实现：基于 ``dict[str, str]`` 的查找 + Python ``str.format`` 格式化。
缺失 key 时 fallback 到 ``key`` 本身（带中括号标识），便于 CI 检测。

扩展性：未来可替换为 Qt ``QTranslator``（基于 .ts/.qm 二进制），
只需修改 ``_lookup`` 实现，公共 API 保持不变。
"""

from __future__ import annotations

import logging
from threading import RLock
from typing import Any

from PySide6.QtCore import QObject, Signal

from . import messages_en_US, messages_zh_CN

logger = logging.getLogger(__name__)

__all__ = [
    "Translator",
    "SUPPORTED_LANGUAGES",
    "get_translator",
    "set_translator",
    "set_language",
    "available_languages",
    "t",
]


# 已支持的语言代码（与 ProjectSettingsManager 的 ui.language 字段对齐）
SUPPORTED_LANGUAGES: tuple[str, ...] = ("zh-CN", "en-US")

# 标签映射（供 SettingsPage UI 显示）
LANGUAGE_LABELS: dict[str, str] = {
    "zh-CN": "简体中文",
    "en-US": "English",
}


# ──────────────────────────────────────────────────────────
# 消息注册表（按语言聚合）
# ──────────────────────────────────────────────────────────


_MESSAGES: dict[str, dict[str, str]] = {
    "zh-CN": messages_zh_CN.MESSAGES,
    "en-US": messages_en_US.MESSAGES,
}


# ──────────────────────────────────────────────────────────
# Translator
# ──────────────────────────────────────────────────────────


class Translator(QObject):
    """线程安全的翻译器（Qt QObject，支持信号通知）。"""

    language_changed = Signal(str)  # 新语言代码

    DEFAULT_LANGUAGE = "zh-CN"

    def __init__(self, language: str = DEFAULT_LANGUAGE, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._language = language if language in SUPPORTED_LANGUAGES else self.DEFAULT_LANGUAGE
        self._lock = RLock()

    # ── 公共 API ──

    def language(self) -> str:
        """当前语言代码（如 ``zh-CN``）。"""
        with self._lock:
            return self._language

    def set_language(self, language: str) -> bool:
        """切换语言。返回 True 表示实际切换。"""
        if language not in SUPPORTED_LANGUAGES:
            logger.warning("不支持的语言: %r，保持 %s", language, self._language)
            return False
        with self._lock:
            if language == self._language:
                return False
            self._language = language
        # 信号在锁外发射（避免槽函数死锁）
        self.language_changed.emit(language)
        return True

    def tr(self, key: str, default: str | None = None, **kwargs: Any) -> str:
        """查找并格式化文案。

        Parameters
        ----------
        key : str
            文案 key，例如 ``"common.save"``。
        default : str, optional
            当当前语言缺少该 key 时使用的 fallback；缺省回退到 ``key`` 本身。
        **kwargs
            格式化占位符，例如 ``tr("error.x", path="/tmp")`` 中 ``{path}``。
        """
        if not key:
            return ""

        with self._lock:
            lang = self._language
            catalog = _MESSAGES.get(lang, {})

        template = catalog.get(key)
        if template is None:
            # 缺失 key：记日志 + 显示 fallback
            if default is not None:
                template = default
            else:
                logger.debug("i18n: 缺失 key '%s' for language '%s'", key, lang)
                template = f"[{key}]"

        if not kwargs:
            return template

        try:
            return template.format(**kwargs)
        except (KeyError, IndexError, ValueError) as e:
            logger.debug("i18n: 格式化失败 '%s' (%s)", key, e)
            return template

    def has_key(self, key: str) -> bool:
        """检查 key 在当前语言下是否存在。"""
        with self._lock:
            catalog = _MESSAGES.get(self._language, {})
        return key in catalog

    def missing_keys(self) -> list[str]:
        """返回当前语言下所有缺失 key（与另一种语言 diff）。仅供测试。"""
        with self._lock:
            current = _MESSAGES.get(self._language, {})
        # 合并所有语言的 key 集合
        all_keys: set[str] = set()
        for cat in _MESSAGES.values():
            all_keys.update(cat.keys())
        return sorted(all_keys - current.keys())


# ──────────────────────────────────────────────────────────
# 全局便捷 API
# ──────────────────────────────────────────────────────────


_translator: Translator | None = None
_translator_lock = RLock()


def get_translator() -> Translator:
    """获取全局 Translator 单例（懒初始化）。"""
    global _translator
    with _translator_lock:
        if _translator is None:
            _translator = Translator()
        return _translator


def set_translator(translator: Translator) -> None:
    """替换全局 Translator（主要用于测试）。"""
    global _translator
    with _translator_lock:
        _translator = translator


def set_language(language: str) -> bool:
    """设置全局语言。"""
    return get_translator().set_language(language)


def available_languages() -> list[tuple[str, str]]:
    """返回 ``[(code, label), ...]``，供 SettingsPage 下拉框使用。"""
    return [(code, LANGUAGE_LABELS.get(code, code)) for code in SUPPORTED_LANGUAGES]


def t(key: str, default: str | None = None, **kwargs: Any) -> str:
    """全局便捷翻译函数（等同 ``get_translator().tr(...)``）。"""
    return get_translator().tr(key, default=default, **kwargs)
