#!/usr/bin/env python3
"""Phase R · SeriesContext 跨项目复用持久化。

把用户在 :class:`SeriesContextDialog` 里填好的
:class:`app.models.project.SeriesContext` 写到统一的
:class:`app.core.settings_store.SettingsStore` 中，下次新建项目时作为
默认 ``initial`` 预填到对话框，避免每次都重新输入剧名/人物/剧情主线。

存储位置：
  - key: ``qt.series_context.last_used``
  - value: :meth:`SeriesContext.to_dict()` 返回的 dict 序列化为 JSON 字符串
  - 持久化由 ``SettingsStore`` 内部委托给 ``QSettings``（跨平台原生），
    headless / 测试环境无 ``QSettings`` 时回退到 in-memory dict。

为何要独立成 module（而不是把方法塞进 SettingsStore）:
  - SeriesContext 是 app.models.project 的领域对象，不该污染
    SettingsStore 这种通用门面
  - 序列化 / 反序列化规则集中在一处，方便加迁移逻辑（例如未来
    加 ``schema_version`` 时只改一处）
  - 可独立单测，不依赖 PySide6 / SettingsStore 实例
"""

from __future__ import annotations

import json
import logging

from app.core.settings_store import get_settings
from app.models.project import SeriesContext

logger = logging.getLogger(__name__)

# 统一的 SettingsStore key（v2.5.0 Phase R 引入）
KEY_LAST_USED = "qt.series_context.last_used"


def save_series_context(ctx: SeriesContext) -> None:
    """把 :class:`SeriesContext` 持久化到 SettingsStore。

    调用方应在用户 ``accept`` 完对话框后调用一次。无副作用失败
    （例如 headless 环境）只记录 warning,不抛错。
    """
    try:
        payload = json.dumps(ctx.to_dict(), ensure_ascii=False)
        get_settings().set(KEY_LAST_USED, payload)
        logger.debug("SeriesContext 已保存: series_title=%r", ctx.series_title)
    except (TypeError, ValueError, OSError) as exc:
        logger.warning("保存 SeriesContext 失败: %s", exc)


def load_series_context() -> SeriesContext | None:
    """读取上次保存的 SeriesContext;若无 / 解析失败 → 返回 None。

    与 :meth:`SeriesContext.from_dict` 的安全降级策略一致:任何
    异常都不抛,只回退 ``None``。
    """
    raw = get_settings().get(KEY_LAST_USED, None)
    if raw is None or raw == "":
        return None
    try:
        # ``QSettings`` 默认会把字符串读回 str;但 headless fallback 路径
        # 下我们是直接 ``set`` 字符串的,这里统一按 str 处理。
        data = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("读取 SeriesContext 失败: %s", exc)
        return None
    # 非 dict（int/None/str 等）一律视为非法数据 → 不返回默认实例,
    # 以免与"用户从未填过"的状态混淆。
    if not isinstance(data, dict):
        logger.warning(
            "SeriesContext 载荷不是 dict 类型（实际=%s），已忽略",
            type(data).__name__,
        )
        return None
    return SeriesContext.from_dict(data)


def clear_series_context() -> None:
    """清除上次保存的 SeriesContext（用于测试 / 切换账号场景）。"""
    try:
        get_settings().set(KEY_LAST_USED, "")
    except (OSError, RuntimeError) as exc:  # pragma: no cover
        logger.warning("清除 SeriesContext 失败: %s", exc)


__all__ = [
    "KEY_LAST_USED",
    "save_series_context",
    "load_series_context",
    "clear_series_context",
]
