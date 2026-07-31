"""help_tooltip · 把 ``HelpTopic`` 注入到 ``QWidget.setToolTip``。

设计要点
========

1. **降级链** —— topic 缺失时退回到 ``widget.setToolTip(text)``；绝不抛异常。
2. **三级详细度** —— ``minimal`` / ``normal`` / ``detailed``，由用户在
   ``QSettings("SceneFab/help_level")`` 控制。
3. **帮助入口** —— tooltip 末尾追加 ``Enter → HelpPanel``，点击 widget 触发
   ``topicRequested`` 信号，面板侧消费它打开对应 topic。

使用示例
========

>>> from app.help.tooltip import set_help_tooltip
>>> set_help_tooltip(my_button, "shortcut.command-palette")

>>> # 自定义 registry
>>> set_help_tooltip(my_button, "faq.api-key", registry=my_registry, level="detailed")
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget

from .registry import HelpRegistry

__all__ = [
    "HelpTooltipBridge",
    "set_help_tooltip",
    "get_default_registry",
]


# ---------------------------------------------------------------------------
# 全局缓存
# ---------------------------------------------------------------------------

_DEFAULT_REGISTRY: HelpRegistry | None = None


def get_default_registry() -> HelpRegistry:
    """返回进程级单例 ``HelpRegistry``（首次访问时构建）。"""
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        from . import build_default_registry
        _DEFAULT_REGISTRY = build_default_registry()
    return _DEFAULT_REGISTRY


def set_default_registry(registry: HelpRegistry | None) -> None:
    """测试 / 热重载场景下替换默认 registry。传 ``None`` 清空缓存。"""
    global _DEFAULT_REGISTRY
    _DEFAULT_REGISTRY = registry


# ---------------------------------------------------------------------------
# 信号桥
# ---------------------------------------------------------------------------


class HelpTooltipBridge(QObject):
    """全局信号桥：widget 触发 help 请求时发出，HelpPanel 监听打开 topic。"""

    topicRequested = Signal(str)  # topic_id


_BRIDGE: HelpTooltipBridge | None = None


def get_bridge() -> HelpTooltipBridge:
    """返回全局 ``HelpTooltipBridge`` 单例。"""
    global _BRIDGE
    if _BRIDGE is None:
        _BRIDGE = HelpTooltipBridge()
    return _BRIDGE


# ---------------------------------------------------------------------------
# Markdown → tooltip 文本
# ---------------------------------------------------------------------------


def _strip_markdown(text: str) -> str:
    """极简 markdown 剥离：去掉 ``**`` / ``` / 链接 [text](url) → text。

    用于把 ``HelpTopic.body`` 渲染为单行 tooltip。完整 markdown 渲染
    留给 ``HelpPanel``。
    """
    # 代码块 ```...``` 直接删除
    import re
    text = re.sub(r"```[\s\S]*?```", "[code]", text)
    # 行内代码 `xxx` → xxx
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # 粗体 **xxx** → xxx
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    # 链接 [text](url) → text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # 列表前缀 - / * / 数字.  → •
    text = re.sub(r"(?m)^\s*[-*]\s+", "• ", text)
    text = re.sub(r"(?m)^\s*\d+\.\s+", "• ", text)
    # 折叠多行空白
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def _render_tooltip(topic, level: str) -> str:
    """根据 level 渲染 tooltip 文本。

    Levels:
        - minimal: 仅 title
        - normal: title + 一句 summary
        - detailed: title + summary + body 首段 + 帮助入口
    """
    parts = [topic.title]
    if level in {"normal", "detailed"} and topic.summary:
        parts.append(topic.summary)
    if level == "detailed" and topic.body:
        body = _strip_markdown(topic.body)
        first_para = body.split("\n", 1)[0]
        if first_para:
            parts.append(first_para)
    parts.append("Enter → HelpPanel")
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# 公共 API
# ---------------------------------------------------------------------------


def set_help_tooltip(
    widget: QWidget,
    topic_id: str,
    *,
    registry: HelpRegistry | None = None,
    level: str = "normal",
    fallback_text: str = "",
) -> bool:
    """把 ``HelpTopic`` 绑定到 widget 的 tooltip。

    Args:
        widget: 目标 widget。
        topic_id: ``HelpTopic.id``，例如 ``"shortcut.command-palette"``。
        registry: 自定义 registry；传 ``None`` 使用全局缓存。
        level: ``"minimal"`` / ``"normal"`` / ``"detailed"``。
        fallback_text: topic 缺失时的降级 tooltip；为空字符串则保留原 tooltip。

    Returns:
        ``True`` 表示成功绑定到 HelpTopic；``False`` 表示降级到 fallback。
    """
    reg = registry or get_default_registry()
    topic = reg.get(topic_id)
    if topic is None:
        if fallback_text:
            widget.setToolTip(fallback_text)
        return False

    widget.setToolTip(_render_tooltip(topic, level))

    # 绑定点击 → topicRequested
    bridge = get_bridge()
    # 避免重复连接：用 ``connect`` 的 lambda 捕获 topic_id。
    # PySide6 不支持 ``once``，靠属性标记防重复。
    if not getattr(widget, "_help_topic_bound", False):
        widget._help_topic_bound = True  # type: ignore[attr-defined]
        _topic_id = topic_id

        def _emit() -> None:
            bridge.topicRequested.emit(_topic_id)

        # 用 mousePress + Enter 键触发；任一即可。
        widget.installEventFilter(_HelpFilter(widget, _emit))
    return True


# ---------------------------------------------------------------------------
# 事件过滤
# ---------------------------------------------------------------------------


from PySide6.QtCore import QEvent  # noqa: E402  (放在此处避免循环)


class _HelpFilter(QObject):
    """为 widget 拦截「打开帮助」事件：

    - **F1** 键：直接 emit。
    - **鼠标中键 / 右键**：不冲突，仅 Enter 触发（更安全）。
    - **widget 已 disabled**：不响应。
    """

    def __init__(self, target: QWidget, on_request) -> None:
        super().__init__(target)
        self._target = target
        self._on_request = on_request

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # noqa: N802
        if obj is not self._target:
            return False
        et = event.type()
        if et == QEvent.Type.KeyPress:
            key = event.key()
            # F1 或 Enter（焦点在 widget 上时）
            if key in {0x1000040, 0x01000004}:  # Qt.Key_F1, Qt.Key_Return
                self._on_request()
                return True
        return False
