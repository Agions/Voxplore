#!/usr/bin/env python3
"""
i18n 包（Phase A · 国际化基础框架）。

设计要点：
- :class:`Translator` 单例 + Qt 信号 ``language_changed`` 通知 UI 刷新
- 文案分层：系统级（Qt 自身） / 框架级 / 业务级
- 缺失 key fallback：显示 key 本身（避免 UI 出现空白或崩溃）
- 支持格式化占位符：``tr("step_n_of_m", n=1, m=5)`` → ``"步骤 1 / 5"``
- 支持 locale：``zh-CN`` / ``en-US`` / 后续可扩展 ``ja-JP`` 等

不在范围（v3.0+）：
- 货币 / 日期 / 数字 locale 格式
- 复数形式（Qt 本地化层处理）
- RTL 布局（业务暂不需要）

使用示例：

.. code-block:: python

    from app.ui.i18n import t, set_language

    set_language("en-US")
    btn.setText(t("common.save"))           # → "Save"
    msg = t("error.load_failed", path=p)    # → "Failed to load: /tmp/x.mp4"
"""

from __future__ import annotations

from .message_keys import ALL_MESSAGE_KEYS, MessageKey
from .translator import (
    SUPPORTED_LANGUAGES,
    Translator,
    available_languages,
    get_translator,
    set_language,
    set_translator,
    t,
)

__all__ = [
    "ALL_MESSAGE_KEYS",
    "MessageKey",
    "SUPPORTED_LANGUAGES",
    "Translator",
    "available_languages",
    "get_translator",
    "set_translator",
    "set_language",
    "t",
]
